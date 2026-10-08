"""El shutdown del runner espera sus jobs y, al vencer, suelta las filas.

Positiva: un job que termina dentro de la espera se drena y ninguna fila se
suelta. Resistencia: un job que no cabe en la espera se ABANDONA soltando su
fila (`queued`, sin dueño) para que la réplica sucesora lo reanude sin esperar
STALE_S — el grace period de ACA no puede cubrir un turno de cinco minutos, y
la fila suelta es la red real.
"""

from __future__ import annotations

import asyncio

import pytest

from persona_runner.core.schemas import TurnRequest, TurnResponse
from persona_runner.engine import turn_jobs
from tests.shared.fake_ledger import FakeLedger

REQ = TurnRequest(channel_id="1", user_id="2", user_text="hola", job_id="j1")


@pytest.fixture
def ledger(monkeypatch):
    fake = FakeLedger()
    monkeypatch.setattr(turn_jobs.JOBS, "ledger", fake)
    monkeypatch.setattr(turn_jobs, "LEDGER", fake)
    turn_jobs.JOBS.clear()
    yield fake
    turn_jobs.JOBS.clear()


@pytest.mark.asyncio
async def test_a_job_that_finishes_in_time_is_drained_and_nothing_is_released(ledger):
    async def quick(_req: TurnRequest) -> TurnResponse:
        await asyncio.sleep(0.05)
        return TurnResponse(text="ok", output_tokens=1, model="m", stop_reason="end_turn")

    await turn_jobs.submit(REQ, runner=quick)
    assert await turn_jobs.drain_for_shutdown(timeout_s=2.0) == 0
    await asyncio.sleep(0)
    assert ledger.rows["j1"]["status"] == "done"


@pytest.mark.asyncio
async def test_a_job_that_outlives_the_wait_is_released_for_the_successor(ledger):
    async def slow(_req: TurnRequest) -> TurnResponse:
        await asyncio.sleep(60)
        raise AssertionError("unreachable")

    ticket = await turn_jobs.submit(REQ, runner=slow)
    assert await turn_jobs.drain_for_shutdown(timeout_s=0.01) == 1
    assert ledger.rows["j1"]["status"] == "queued" and ledger.rows["j1"]["claimed_by"] is None
    ticket.task.cancel()


@pytest.mark.asyncio
async def test_boot_resumes_the_orphans_the_previous_replica_left(ledger):
    ledger.rows["j9"] = {
        "status": "queued",
        "attempts": 1,
        "payload": {"channel_id": "1", "user_id": "2", "user_text": "pendiente", "has_attachments": False},
        "result": None,
        "error": None,
        "stale": True,
        "claimed_by": None,
        "label": "insult:1",
    }
    seen: list[TurnRequest] = []

    async def turn(req: TurnRequest) -> TurnResponse:
        seen.append(req)
        return TurnResponse(text="reanudado", output_tokens=1, model="m", stop_reason="end_turn")

    assert await turn_jobs.resume_stale_at_boot(turn) == 1
    await asyncio.sleep(0.05)
    assert seen and seen[0].resumed and seen[0].user_text == "pendiente"
    assert ledger.rows["j9"]["status"] == "done" and ledger.rows["j9"]["attempts"] == 2
