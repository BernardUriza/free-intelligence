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
- Un trabajo terminado sobrevive `DONE_TTL_S` sin que lo recojan; un proceso que
  muere se lleva sus trabajos, y el cliente recibe "no existe" — la misma señal
  de reinicio que ya sabe leer. Persistirlos sería prometer una durabilidad que
  el motor de abajo tampoco da.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Coroutine
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger()

DONE_TTL_S = 300.0
MAX_WAIT_S = 50.0


@dataclass
class Ticket[T]:
    ticket_id: str
    label: str
    task: asyncio.Task[T]
    created_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None

    @property
    def done(self) -> bool:
        return self.task.done()


class TicketRegistry[T]:
    def __init__(self, name: str) -> None:
        self.name = name
        self._tickets: dict[str, Ticket[T]] = {}

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
        ticket_id = ticket_id or uuid.uuid4().hex
        task: asyncio.Task[T] = asyncio.create_task(coro, name=f"{self.name}:{ticket_id}")
        ticket: Ticket[T] = Ticket(ticket_id=ticket_id, label=label, task=task)

        def _mark_finished(_: asyncio.Task[T]) -> None:
            ticket.finished_at = time.monotonic()

        task.add_done_callback(_mark_finished)
        self._tickets[ticket_id] = ticket
        log.info("ticket_submitted", registry=self.name, ticket_id=ticket_id, label=label, open=len(self._tickets))
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

    def open(self) -> int:
        self._reap()
        return len(self._tickets)

    def clear(self) -> None:
        self._tickets.clear()
