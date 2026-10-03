"""Trabajo con boleto: una corrutina larga detrás de requests cortas.

El ingress de Azure Container Apps cierra cualquier request HTTP a los 240 s y
no se configura. Un turno de Opus con caché frío puede tardar más (2026-09-19:
326.9 s, entregado por AIRE y tirado porque ya nadie escuchaba). Este módulo
separa "cuánto dura el trabajo" de "cuánto dura una request": el trabajo corre
en una task del proceso y el cliente pregunta por él en requests acotadas.

Lo usan las dos costuras que cruzan el ingress — el runner (`/v1/turn/jobs`) y
el gateway (`/invite` con boleto) — con la misma semántica:

- `submit` arranca la task y devuelve el id. Con un `ticket_id` del cliente el
  alta es idempotente: el mismo id dos veces es UN trabajo (2026-09-23: el
  ingress retuvo el alta durante un arranque en frío de 169 s, el cliente la
  dio por perdida a los 60 s, y el runner corrió dos turnos que nadie leyó).
- `wait` espera hasta `wait_s` (tope `MAX_WAIT_S`, muy por debajo del ingress) y
  devuelve `None` si sigue corriendo; si terminó, devuelve el resultado o
  re-lanza la excepción tal cual, para que la capa HTTP la mapee igual que en el
  camino síncrono.
- Un trabajo terminado sobrevive `DONE_TTL_S` en RAM sin que lo recojan.

RAM es la dueña del boleto; la fila del ledger es el HANDOFF entre procesos.
Con un `TicketLedger` cableado, `open`/`lookup` consultan la fila sólo cuando
RAM no tiene el boleto: un proceso que murió deja una fila `running` con el
heartbeat viejo, y la réplica que la encuentra la RECLAMA (compare-and-swap:
exactamente un ganador) y reanuda bajo el mismo id, en vez de contestar 404 y
provocar un reintento ciego río arriba. Un resultado ya escrito se sirve de la
fila sin volver a correr nada. Todo toque al ledger es best-effort: si Postgres
no está, el registro se comporta exactamente como antes (sólo RAM).
"""

from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Protocol

import structlog

log = structlog.get_logger()

DONE_TTL_S = 300.0
MAX_WAIT_S = 50.0

# Lease: un latido cada HEARTBEAT_S; sin latido en STALE_S el dueño está muerto.
HEARTBEAT_S = 10.0
STALE_S = 60.0
# Original + UNA reanudación: una segunda no cabe en el presupuesto del turno.
MAX_ATTEMPTS = 2
RESULT_ROW_TTL_S = 3600.0
ROW_POLL_S = 2.0

TERMINAL = frozenset({"done", "failed", "abandoned"})


@dataclass
class LedgerRow:
    ticket_id: str
    status: str
    attempts: int
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    stale: bool = False
    owned: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL


class TicketLedger(Protocol):
    """Adaptador de la fila. Cada método devuelve `None` cuando la base falla:
    el registro degrada a RAM y lo loggea; nunca mata el trabajo."""

    async def open(
        self, ticket_id: str, *, label: str, payload: dict[str, Any], deadline_s: float, claimed_by: str
    ) -> LedgerRow | None: ...

    async def get(self, ticket_id: str) -> LedgerRow | None: ...

    async def claim(
        self, ticket_id: str, *, claimed_by: str, stale_s: float, max_attempts: int
    ) -> LedgerRow | None: ...

    async def heartbeat(self, ticket_ids: list[str], *, claimed_by: str) -> set[str] | None: ...

    async def finish(
        self,
        ticket_id: str,
        *,
        claimed_by: str | None,
        status: str,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> bool | None:
        """`claimed_by=None` escribe sin condición de dueño (agotar/abandonar);
        con dueño, sólo si la fila sigue `running` bajo ese dueño."""
        ...

    async def release(self, *, claimed_by: str) -> int | None: ...

    async def reap(self, *, result_ttl_s: float) -> int | None: ...


@dataclass
class Ticket[T]:
    ticket_id: str
    label: str
    task: asyncio.Task[T]
    created_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None
    attempt: int = 1

    @property
    def done(self) -> bool:
        return self.task.done()


class TicketRegistry[T]:
    def __init__(
        self,
        name: str,
        *,
        ledger: TicketLedger | None = None,
        encode: Callable[[T], dict[str, Any]] | None = None,
        decode: Callable[[dict[str, Any]], T] | None = None,
    ) -> None:
        self.name = name
        self.ledger = ledger
        self.claimed_by = uuid.uuid4().hex
        self._encode = encode
        self._decode = decode
        self._tickets: dict[str, Ticket[T]] = {}
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._finish_tasks: set[asyncio.Future[None]] = set()
        self._last_reap = 0.0
        self._ledger_warned_at = 0.0

    # ── RAM ──────────────────────────────────────────────────────────────

    def _reap(self) -> None:
        now = time.monotonic()
        for ticket_id, ticket in list(self._tickets.items()):
            if ticket.finished_at is not None and now - ticket.finished_at > DONE_TTL_S:
                del self._tickets[ticket_id]

    def submit(self, coro: Coroutine[Any, Any, T], *, label: str, ticket_id: str | None = None) -> Ticket[T]:
        self._reap()
        if ticket_id is not None and (existing := self._tickets.get(ticket_id)) is not None:
            coro.close()
            log.info("ticket_reused", registry=self.name, ticket_id=ticket_id, label=label, done=existing.done)
            return existing
        return self._start(coro, ticket_id=ticket_id or uuid.uuid4().hex, label=label, attempt=1)

    def _start(self, coro: Coroutine[Any, Any, T], *, ticket_id: str, label: str, attempt: int) -> Ticket[T]:
        task: asyncio.Task[T] = asyncio.create_task(coro, name=f"{self.name}:{ticket_id}")
        ticket: Ticket[T] = Ticket(ticket_id=ticket_id, label=label, task=task, attempt=attempt)

        def _mark_finished(done: asyncio.Task[T]) -> None:
            ticket.finished_at = time.monotonic()
            if self.ledger is not None and not done.cancelled():
                recorder = asyncio.ensure_future(self._record_finish(ticket, done))
                self._finish_tasks.add(recorder)
                recorder.add_done_callback(self._finish_tasks.discard)

        task.add_done_callback(_mark_finished)
        self._tickets[ticket_id] = ticket
        log.info(
            "ticket_submitted",
            registry=self.name,
            ticket_id=ticket_id,
            label=label,
            attempt=attempt,
            open=len(self._tickets),
        )
        return ticket

    def get(self, ticket_id: str) -> Ticket[T] | None:
        self._reap()
        return self._tickets.get(ticket_id)

    async def wait(self, ticket: Ticket[T], wait_s: float) -> tuple[bool, T | None]:
        """(terminó, resultado). Si terminó con excepción, la re-lanza."""
        budget = max(0.0, min(wait_s, MAX_WAIT_S))
        try:
            result = await asyncio.wait_for(asyncio.shield(ticket.task), timeout=budget)
        except TimeoutError:
            return False, None
        return True, result

    def drop(self, ticket_id: str) -> None:
        self._tickets.pop(ticket_id, None)

    def open_count(self) -> int:
        self._reap()
        return len(self._tickets)

    def open(self) -> int:
        return self.open_count()

    def running_ids(self) -> list[str]:
        return [ticket_id for ticket_id, ticket in self._tickets.items() if not ticket.done]

    def clear(self) -> None:
        self._tickets.clear()

    # ── Ledger ───────────────────────────────────────────────────────────

    def decode_result(self, row: LedgerRow) -> T | None:
        if row.result is None:
            return None
        return self._decode(row.result) if self._decode else row.result  # type: ignore[return-value]

    def _ledger_unavailable(self, op: str) -> None:
        now = time.monotonic()
        if now - self._ledger_warned_at > 60.0:
            self._ledger_warned_at = now
            log.warning("ticket_ledger_unavailable", registry=self.name, op=op)

    async def open_durable(
        self,
        payload: dict[str, Any],
        run: Callable[[dict[str, Any]], Coroutine[Any, Any, T]],
        *,
        ticket_id: str,
        label: str,
        deadline_s: float,
        resume: Callable[[LedgerRow], Coroutine[Any, Any, T]] | None = None,
    ) -> Ticket[T] | LedgerRow:
        """Alta idempotente con fila. Devuelve el boleto en RAM si este proceso
        lo corre, o la fila cuando otro proceso ya lo terminó o lo sigue corriendo."""
        self._reap()
        if (existing := self._tickets.get(ticket_id)) is not None:
            log.info("ticket_reused", registry=self.name, ticket_id=ticket_id, label=label, done=existing.done)
            return existing
        if self.ledger is None:
            return self._start(run(payload), ticket_id=ticket_id, label=label, attempt=1)
        await self._maybe_reap_rows()
        row = await self.ledger.open(
            ticket_id, label=label, payload=payload, deadline_s=deadline_s, claimed_by=self.claimed_by
        )
        if row is None:
            self._ledger_unavailable("open")
            return self._start(run(payload), ticket_id=ticket_id, label=label, attempt=1)
        if row.owned:
            log.info("ticket_ledger_opened", registry=self.name, ticket_id=ticket_id, label=label)
            return self._start(run(payload), ticket_id=ticket_id, label=label, attempt=1)
        return await self._adopt(row, label=label, resume=resume or (lambda r: run(r.payload)))

    async def lookup(
        self,
        ticket_id: str,
        *,
        resume: Callable[[LedgerRow], Coroutine[Any, Any, T]] | None = None,
    ) -> Ticket[T] | LedgerRow | None:
        """El poll. RAM primero; después la fila: terminada → su resultado;
        viva en otro proceso → `running`; huérfana → se reclama y se reanuda aquí."""
        if (ticket := self.get(ticket_id)) is not None:
            return ticket
        if self.ledger is None:
            return None
        row = await self.ledger.get(ticket_id)
        if row is None:
            return None
        return await self._adopt(row, label=row.extra.get("label", ticket_id), resume=resume)

    async def _adopt(
        self,
        row: LedgerRow,
        *,
        label: str,
        resume: Callable[[LedgerRow], Coroutine[Any, Any, T]] | None,
    ) -> Ticket[T] | LedgerRow:
        if row.terminal:
            log.info(
                "ticket_recovered_from_ledger",
                registry=self.name,
                ticket_id=row.ticket_id,
                status=row.status,
                attempts=row.attempts,
            )
            return row
        if not row.stale:
            log.info("ticket_owned_elsewhere", registry=self.name, ticket_id=row.ticket_id, attempts=row.attempts)
            return row
        if resume is None:
            return row
        if row.attempts >= MAX_ATTEMPTS:
            return await self._exhaust(row)
        claimed = await self.ledger.claim(  # type: ignore[union-attr]
            row.ticket_id, claimed_by=self.claimed_by, stale_s=STALE_S, max_attempts=MAX_ATTEMPTS
        )
        if claimed is None:
            fresh = await self.ledger.get(row.ticket_id)  # type: ignore[union-attr]
            if fresh is None:
                return row
            if not fresh.terminal and fresh.stale and fresh.attempts >= MAX_ATTEMPTS:
                return await self._exhaust(fresh)
            return fresh
        log.warning(
            "ticket_resumed",
            registry=self.name,
            ticket_id=row.ticket_id,
            label=label,
            attempts=claimed.attempts,
        )
        return self._start(resume(claimed), ticket_id=row.ticket_id, label=label, attempt=claimed.attempts)

    async def _exhaust(self, row: LedgerRow) -> LedgerRow:
        log.error("ticket_attempts_exhausted", registry=self.name, ticket_id=row.ticket_id, attempts=row.attempts)
        await self.ledger.finish(  # type: ignore[union-attr]
            row.ticket_id, claimed_by=None, status="failed", result=None, error="attempts_exhausted"
        )
        row.status = "failed"
        row.error = "attempts_exhausted"
        return row

    async def wait_row(self, ticket_id: str, wait_s: float) -> LedgerRow | None:
        """Espera acotada sobre la fila de un boleto que corre en OTRO proceso."""
        if self.ledger is None:
            return None
        deadline = time.monotonic() + max(0.0, min(wait_s, MAX_WAIT_S))
        row = await self.ledger.get(ticket_id)
        while row is not None and not row.terminal and time.monotonic() < deadline:
            await asyncio.sleep(ROW_POLL_S)
            row = await self.ledger.get(ticket_id)
        return row

    async def _record_finish(self, ticket: Ticket[T], done: asyncio.Task[T]) -> None:
        assert self.ledger is not None
        exc = done.exception()
        if exc is None:
            result = done.result()
            payload = (
                self._encode(result) if self._encode else (result if isinstance(result, dict) else {"value": result})
            )
            status, error = "done", None
        else:
            payload, status, error = None, "failed", f"{type(exc).__name__}: {exc}"[:500]
        try:
            written = await self.ledger.finish(
                ticket.ticket_id, claimed_by=self.claimed_by, status=status, result=payload, error=error
            )
        except Exception:
            written = None
        if written is None:
            self._ledger_unavailable("finish")
            log.warning("ticket_finished_unrecorded", registry=self.name, ticket_id=ticket.ticket_id, status=status)
        elif written is False:
            log.warning("ticket_finish_rejected", registry=self.name, ticket_id=ticket.ticket_id, status=status)

    # ── Heartbeat ────────────────────────────────────────────────────────

    def start_heartbeat(self) -> None:
        if self.ledger is None or self._heartbeat_task is not None:
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name=f"{self.name}:heartbeat")

    async def stop_heartbeat(self) -> None:
        if self._heartbeat_task is None:
            return
        self._heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await self._heartbeat_task
        self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_S)
            await self.heartbeat_once()

    async def heartbeat_once(self) -> None:
        if self.ledger is None:
            return
        ids = self.running_ids()
        if not ids:
            return
        try:
            owned = await self.ledger.heartbeat(ids, claimed_by=self.claimed_by)
        except Exception:
            owned = None
        if owned is None:
            log.warning("ticket_heartbeat_failed", registry=self.name, open=len(ids))
            return
        for ticket_id in ids:
            if ticket_id in owned:
                continue
            ticket = self._tickets.get(ticket_id)
            if ticket is None or ticket.done:
                continue
            log.error("ticket_lease_lost", registry=self.name, ticket_id=ticket_id, attempt=ticket.attempt)
            ticket.task.cancel()

    async def release_open(self) -> int:
        """Al vencer la espera de shutdown: suelta las filas que este proceso
        sigue corriendo para que la sucesora las reanude sin esperar STALE_S."""
        if self.ledger is None:
            return 0
        try:
            released = await self.ledger.release(claimed_by=self.claimed_by)
        except Exception:
            released = None
        if released is None:
            self._ledger_unavailable("release")
            return 0
        if released:
            log.warning("ticket_released", registry=self.name, released=released, open=len(self.running_ids()))
        return released

    async def _maybe_reap_rows(self) -> None:
        now = time.monotonic()
        if now - self._last_reap < RESULT_ROW_TTL_S / 6:
            return
        self._last_reap = now
        try:
            await self.ledger.reap(result_ttl_s=RESULT_ROW_TTL_S)  # type: ignore[union-attr]
        except Exception:
            self._ledger_unavailable("reap")
