"""`khimeras_shared.tickets` — un trabajo largo detrás de requests cortas.

Positiva: un trabajo que tarda más que un poll sigue vivo entre polls y entrega
su resultado al que pregunta después. Resistencia: la excepción del trabajo
llega tal cual al que pregunta (no se traga ni se disfraza), un id desconocido
es None, y un trabajo recogido se puede borrar sin tumbar a los demás.

Con ledger (2026-09-23): la fila es el handoff entre procesos. Un registro nuevo
sobre el mismo ledger sirve un resultado ya escrito sin correr nada, reanuda una
fila huérfana bajo el mismo id (una sola vez), deja en paz una fila cuyo dueño
sigue latiendo, y con el ledger caído se comporta exactamente como sólo-RAM.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from khimeras_shared import tickets
from khimeras_shared.tickets import LedgerRow, TicketRegistry


async def _slow(value: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return value


async def _boom() -> str:
    await asyncio.sleep(0)
    raise RuntimeError("el turno tronó")


async def _settle() -> None:
    for _ in range(4):
        await asyncio.sleep(0)


class FakeLedger:
    """Modela en RAM la semántica de las filas: CAS al reclamar, cierre
    condicionado al dueño, `stale` como el heartbeat vencido."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}
        self.fail = False

    def _row(self, ticket_id: str, me: str | None) -> LedgerRow:
        r = self.rows[ticket_id]
        return LedgerRow(
            ticket_id=ticket_id,
            status=r["status"],
            attempts=r["attempts"],
            payload=r["payload"],
            result=r["result"],
            error=r["error"],
            stale=r["stale"],
            owned=(me is not None and r["claimed_by"] == me),
            extra={"label": r["label"]},
        )

    def age(self, ticket_id: str) -> None:
        self.rows[ticket_id]["stale"] = True

    async def open(self, ticket_id, *, label, payload, deadline_s, claimed_by):
        if self.fail:
            return None
        if ticket_id not in self.rows:
            self.rows[ticket_id] = {
                "status": "running",
                "attempts": 1,
                "payload": payload,
                "result": None,
                "error": None,
                "stale": False,
                "claimed_by": claimed_by,
                "label": label,
            }
        return self._row(ticket_id, claimed_by)

    async def get(self, ticket_id):
        if self.fail or ticket_id not in self.rows:
            return None
        return self._row(ticket_id, None)

    async def claim(self, ticket_id, *, claimed_by, stale_s, max_attempts):
        if self.fail:
            return None
        r = self.rows.get(ticket_id)
        if (
            r is None
            or r["status"] not in ("running", "queued")
            or r["claimed_by"] == claimed_by
            or not r["stale"]
            or r["attempts"] >= max_attempts
        ):
            return None
        r.update(status="running", claimed_by=claimed_by, attempts=r["attempts"] + 1, stale=False)
        return self._row(ticket_id, claimed_by)

    async def heartbeat(self, ticket_ids, *, claimed_by):
        if self.fail:
            return None
        return {
            t
            for t in ticket_ids
            if t in self.rows and self.rows[t]["claimed_by"] == claimed_by and self.rows[t]["status"] == "running"
        }

    async def finish(self, ticket_id, *, claimed_by, status, result, error):
        if self.fail:
            return None
        r = self.rows.get(ticket_id)
        if r is None:
            return False
        if claimed_by is not None and (r["claimed_by"] != claimed_by or r["status"] != "running"):
            return False
        r.update(status=status, result=result, error=error)
        return True

    async def release(self, *, claimed_by):
        if self.fail:
            return None
        n = 0
        for r in self.rows.values():
            if r["claimed_by"] == claimed_by and r["status"] == "running":
                r.update(status="queued", claimed_by=None, stale=True)
                n += 1
        return n

    async def reap(self, *, result_ttl_s):
        return 0


# ── sólo RAM (contrato original) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_job_longer_than_one_poll_survives_between_polls():
    registry: TicketRegistry[str] = TicketRegistry("t")
    ticket = registry.submit(_slow("respuesta", 0.15), label="c1")

    done, result = await registry.wait(ticket, wait_s=0.02)
    assert (done, result) == (False, None)
    assert registry.get(ticket.ticket_id) is ticket  # sigue ahí, sigue corriendo

    done, result = await registry.wait(ticket, wait_s=1.0)
    assert (done, result) == (True, "respuesta")


@pytest.mark.asyncio
async def test_the_jobs_exception_reaches_the_poller_unchanged():
    registry: TicketRegistry[str] = TicketRegistry("t")
    ticket = registry.submit(_boom(), label="c1")
    with pytest.raises(RuntimeError, match="tronó"):
        await registry.wait(ticket, wait_s=1.0)


@pytest.mark.asyncio
async def test_unknown_and_dropped_ids_are_none():
    registry: TicketRegistry[str] = TicketRegistry("t")
    assert registry.get("nope") is None
    ticket = registry.submit(_slow("x", 0), label="c1")
    await registry.wait(ticket, wait_s=1.0)
    registry.drop(ticket.ticket_id)
    assert registry.get(ticket.ticket_id) is None
    assert registry.open() == 0


@pytest.mark.asyncio
async def test_a_finished_job_nobody_collected_is_reaped_after_the_ttl(monkeypatch):
    registry: TicketRegistry[str] = TicketRegistry("t")
    ticket = registry.submit(_slow("x", 0), label="c1")
    await registry.wait(ticket, wait_s=1.0)
    assert registry.open() == 1
    monkeypatch.setattr(tickets, "DONE_TTL_S", 0.0)
    await asyncio.sleep(0.01)
    assert registry.open() == 0


@pytest.mark.asyncio
async def test_the_same_client_ticket_id_submitted_twice_is_one_job():
    """2026-09-23: el ingress retuvo el alta durante un arranque en frío y la
    entregó después de que el cliente la repitió — dos turnos para un mensaje."""
    registry: TicketRegistry[str] = TicketRegistry("t")
    runs: list[str] = []

    async def _turn(tag: str) -> str:
        runs.append(tag)
        await asyncio.sleep(0.05)
        return tag

    first = registry.submit(_turn("uno"), label="c1", ticket_id="job-abc")
    again = registry.submit(_turn("dos"), label="c1", ticket_id="job-abc")
    assert again is first
    assert registry.open() == 1
    done, result = await registry.wait(first, wait_s=1.0)
    assert (done, result) == (True, "uno")
    assert runs == ["uno"]  # la segunda corrutina se cerró sin correr

    other = registry.submit(_turn("tres"), label="c1", ticket_id="job-xyz")
    assert other is not first
    await registry.wait(other, wait_s=1.0)


@pytest.mark.asyncio
async def test_a_single_poll_never_waits_longer_than_the_cap():
    registry: TicketRegistry[str] = TicketRegistry("t")
    ticket = registry.submit(_slow("x", 5.0), label="c1")
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    done, _ = await registry.wait(ticket, wait_s=0.05)
    assert done is False
    assert loop.time() - t0 < 1.0
    ticket.task.cancel()


# ── con ledger (el handoff entre procesos) ────────────────────────────────


def _registry(ledger: FakeLedger | None) -> TicketRegistry[dict]:
    return TicketRegistry("t", ledger=ledger)


async def _run(payload: dict) -> dict:
    await asyncio.sleep(payload.get("delay", 0))
    return {"text": f"respuesta a {payload['ask']}"}


@pytest.mark.asyncio
async def test_open_writes_the_row_and_finish_records_the_result():
    ledger = FakeLedger()
    a = _registry(ledger)
    ticket = await a.open_durable({"ask": "hola"}, _run, ticket_id="j1", label="c1", deadline_s=600)
    assert ledger.rows["j1"]["status"] == "running" and ledger.rows["j1"]["claimed_by"] == a.claimed_by
    done, result = await a.wait(ticket, wait_s=1.0)  # type: ignore[arg-type]
    await _settle()
    assert (done, result) == (True, {"text": "respuesta a hola"})
    assert ledger.rows["j1"]["status"] == "done" and ledger.rows["j1"]["result"] == {"text": "respuesta a hola"}


@pytest.mark.asyncio
async def test_after_a_restart_a_finished_row_is_served_without_running_again():
    """Restart = registro nuevo sobre el mismo ledger. El resultado sale de la
    fila; nadie vuelve a pagar el turno."""
    ledger = FakeLedger()
    runs: list[str] = []

    async def counted(payload: dict) -> dict:
        runs.append(payload["ask"])
        return {"text": "una vez"}

    a = _registry(ledger)
    ticket = await a.open_durable({"ask": "hola"}, counted, ticket_id="j1", label="c1", deadline_s=600)
    await a.wait(ticket, wait_s=1.0)  # type: ignore[arg-type]
    await _settle()

    b = _registry(ledger)
    row = await b.lookup("j1", resume=lambda r: counted(r.payload))
    assert isinstance(row, LedgerRow) and row.status == "done" and row.result == {"text": "una vez"}
    again = await b.open_durable({"ask": "hola"}, counted, ticket_id="j1", label="c1", deadline_s=600)
    assert isinstance(again, LedgerRow) and again.status == "done"
    assert runs == ["hola"]


@pytest.mark.asyncio
async def test_an_orphaned_running_row_is_claimed_and_resumed_once_under_the_same_id():
    ledger = FakeLedger()
    resumed: list[LedgerRow] = []

    async def resume(row: LedgerRow) -> dict:
        resumed.append(row)
        return {"text": "reanudado"}

    a = _registry(ledger)
    ticket = await a.open_durable(
        {"ask": "hola"}, lambda p: _slow("nunca", 60), ticket_id="j1", label="c1", deadline_s=600
    )  # type: ignore[arg-type]
    ticket.task.cancel()  # el proceso A murió a media generación
    ledger.age("j1")

    b = _registry(ledger)
    got = await b.lookup("j1", resume=resume)
    assert not isinstance(got, LedgerRow) and got.ticket_id == "j1" and got.attempt == 2
    done, result = await b.wait(got, wait_s=1.0)
    await _settle()
    assert (done, result) == (True, {"text": "reanudado"})
    assert resumed[0].payload == {"ask": "hola"} and resumed[0].attempts == 2
    assert ledger.rows["j1"]["status"] == "done"
    assert ledger.rows["j1"]["claimed_by"] == b.claimed_by


@pytest.mark.asyncio
async def test_a_row_whose_owner_still_beats_is_not_resumed():
    ledger = FakeLedger()
    calls = {"n": 0}

    async def resume(row: LedgerRow) -> dict:
        calls["n"] += 1
        return {}

    a = _registry(ledger)
    ticket = await a.open_durable(
        {"ask": "hola"}, lambda p: _slow("x", 0.2), ticket_id="j1", label="c1", deadline_s=600
    )  # type: ignore[arg-type]
    b = _registry(ledger)
    got = await b.lookup("j1", resume=resume)
    assert isinstance(got, LedgerRow) and got.status == "running" and calls["n"] == 0
    await a.wait(ticket, wait_s=1.0)  # type: ignore[arg-type]
    await _settle()
    row = await b.wait_row("j1", wait_s=1.0)
    assert row is not None and row.status == "done"


@pytest.mark.asyncio
async def test_a_second_resume_is_refused_as_attempts_exhausted():
    ledger = FakeLedger()
    ledger.rows["j1"] = {
        "status": "running",
        "attempts": 2,
        "payload": {"ask": "hola"},
        "result": None,
        "error": None,
        "stale": True,
        "claimed_by": "muerto",
        "label": "c1",
    }
    calls = {"n": 0}

    async def resume(row: LedgerRow) -> dict:
        calls["n"] += 1
        return {}

    got = await _registry(ledger).lookup("j1", resume=resume)
    assert isinstance(got, LedgerRow) and got.status == "failed" and got.error == "attempts_exhausted"
    assert ledger.rows["j1"]["status"] == "failed" and calls["n"] == 0


@pytest.mark.asyncio
async def test_a_dead_ledger_degrades_to_ram_only():
    ledger = FakeLedger()
    ledger.fail = True
    a = _registry(ledger)
    ticket = await a.open_durable({"ask": "hola"}, _run, ticket_id="j1", label="c1", deadline_s=600)
    assert not isinstance(ticket, LedgerRow)
    done, result = await a.wait(ticket, wait_s=1.0)
    await _settle()
    assert (done, result) == (True, {"text": "respuesta a hola"})
    assert await a.lookup("j1") is ticket
    assert await a.lookup("desconocido") is None
    assert await a.release_open() == 0


@pytest.mark.asyncio
async def test_release_open_hands_running_rows_to_the_successor():
    ledger = FakeLedger()
    a = _registry(ledger)
    t1 = await a.open_durable({"ask": "1"}, lambda p: _slow("x", 60), ticket_id="j1", label="c1", deadline_s=600)  # type: ignore[arg-type]
    t2 = await a.open_durable({"ask": "2"}, lambda p: _slow("x", 60), ticket_id="j2", label="c1", deadline_s=600)  # type: ignore[arg-type]
    assert await a.release_open() == 2
    assert all(ledger.rows[j]["status"] == "queued" and ledger.rows[j]["claimed_by"] is None for j in ("j1", "j2"))
    for t in (t1, t2):
        t.task.cancel()  # type: ignore[union-attr]

    b = _registry(ledger)
    got = await b.lookup("j1", resume=lambda r: _run(r.payload))
    assert isinstance(got, tickets.Ticket) and got.attempt == 2
    done, result = await b.wait(got, wait_s=1.0)
    await _settle()
    assert (done, result) == (True, {"text": "respuesta a 1"})
    assert ledger.rows["j1"]["status"] == "done" and ledger.rows["j1"]["claimed_by"] == b.claimed_by


@pytest.mark.asyncio
async def test_a_lost_lease_cancels_the_local_task_and_its_result_is_never_written():
    ledger = FakeLedger()
    a = _registry(ledger)
    ticket = await a.open_durable({"ask": "hola", "delay": 0.2}, _run, ticket_id="j1", label="c1", deadline_s=600)
    ledger.rows["j1"]["claimed_by"] = "otro"  # alguien más reclamó la fila
    await a.heartbeat_once()
    await _settle()
    assert ticket.task.cancelled()  # type: ignore[union-attr]
    assert ledger.rows["j1"]["status"] == "running" and ledger.rows["j1"]["result"] is None


@pytest.mark.asyncio
async def test_a_late_result_from_a_replica_that_lost_the_lease_is_rejected():
    ledger = FakeLedger()
    a = _registry(ledger)
    ticket = await a.open_durable({"ask": "hola", "delay": 0.05}, _run, ticket_id="j1", label="c1", deadline_s=600)
    ledger.rows["j1"]["claimed_by"] = "otro"
    await a.wait(ticket, wait_s=1.0)  # type: ignore[arg-type]
    await _settle()
    assert ledger.rows["j1"]["result"] is None  # el cierre condicionado al dueño no escribió


@pytest.mark.asyncio
async def test_a_failed_job_is_recorded_as_failed_with_its_error():
    ledger = FakeLedger()
    a = _registry(ledger)

    async def bad(payload: dict) -> dict:
        await asyncio.sleep(0)
        raise RuntimeError("AIRE dijo que no")

    ticket = await a.open_durable({"ask": "hola"}, bad, ticket_id="j1", label="c1", deadline_s=600)
    with pytest.raises(RuntimeError):
        await a.wait(ticket, wait_s=1.0)  # type: ignore[arg-type]
    await _settle()
    assert ledger.rows["j1"]["status"] == "failed" and "AIRE dijo que no" in ledger.rows["j1"]["error"]
