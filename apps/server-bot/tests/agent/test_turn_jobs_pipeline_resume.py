"""La reanudación de un job `pipeline="runner"` (og118, F3) entra por la tubería.

Dos ejes que la fase B separa y que no se pueden confundir:

- `resumed` = qué vio AIRE (`crossed_to_aire`): decide la nota de reintento y
  si la historia se pliega.
- `ask_stored` = qué ya está en `messages`: la tubería guarda la pregunta ANTES
  del cerebro, así que un job que murió armando el contexto (embeddings, guía)
  ya la tiene guardada aunque nunca haya cruzado a AIRE.

Positiva: un job reanudado, cruzado o no, guarda sólo la respuesta — la pregunta
una sola vez en total — y al cerebro le llega `resumed` igual a lo que dice la
fila. Resistencia: el arranque reanuda por `serve_turn`, nunca directo contra
AIRE, que se saltaba el contexto, la guía y el guardado de la respuesta.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from persona_runner.api import judge as judge_api
from persona_runner.api import turn_pipeline
from persona_runner.core.schemas import TurnResponse
from persona_runner.engine import aire_route, turn_jobs
from tests.shared.fake_ledger import FakeLedger

BERNARD = "907264175246569543"


@pytest.fixture
def ledger(monkeypatch):
    fake = FakeLedger()
    monkeypatch.setattr(turn_jobs.JOBS, "ledger", fake)
    monkeypatch.setattr(turn_jobs, "LEDGER", fake)
    turn_jobs.JOBS.clear()
    turn_pipeline.reset_memory()
    judge_api.reset_judge_semaphore()
    yield fake
    turn_jobs.JOBS.clear()
    turn_pipeline.reset_memory()


def _memory() -> MagicMock:
    memory = MagicMock()
    memory.get_recent = AsyncMock(return_value=[])
    memory.store = AsyncMock()
    memory.search = AsyncMock(return_value=[])
    memory.search_facts_semantic = AsyncMock(return_value=[])
    memory.list_pending_reminders = AsyncMock(return_value=[])
    memory.build_context = MagicMock(return_value=[])
    return memory


def _orphan(ledger: FakeLedger, *, aire_sent: bool) -> None:
    ledger.rows["og1"] = {
        "status": "queued",
        "attempts": 1,
        "payload": {
            "channel_id": "conv-1",
            "user_id": BERNARD,
            "user_name": "Bernard",
            "user_text": "¿qué sabes de mí?",
            "persona_id": "insult",
            "pipeline": "runner",
            "surface": "og118",
            "job_id": "og1",
            "has_attachments": False,
        },
        "result": None,
        "error": None,
        "stale": True,
        "claimed_by": None,
        "label": "insult:conv-1",
        "aire_sent": aire_sent,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("aire_sent", [True, False], ids=["crossed", "died_before_aire"])
async def test_a_resumed_og118_job_stores_only_the_reply(ledger, monkeypatch, aire_sent):
    _orphan(ledger, aire_sent=aire_sent)
    seen = []

    async def brain(req):
        seen.append(req)
        return TurnResponse(text="Vives en GDL.", model="m", output_tokens=4, stop_reason="end_turn")

    memory = _memory()
    monkeypatch.setattr(aire_route, "turn_via_aire", brain)
    monkeypatch.setattr(turn_pipeline, "get_memory", AsyncMock(return_value=memory))
    with (
        patch("persona_core.turn.context.guidance_for_turn", new=AsyncMock(return_value="GUIA")),
        patch("persona_core.turn.context.other_people_block_for_turn", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.context.build_persona_corpus_block", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.pipeline.FactExtractor"),
    ):
        assert await turn_jobs.resume_stale_at_boot(turn_pipeline.serve_turn) == 1
        for _ in range(50):
            if ledger.rows["og1"]["status"] == "done":
                break
            await asyncio.sleep(0.02)

    assert ledger.rows["og1"]["status"] == "done"
    (sent,) = seen
    assert sent.resumed is aire_sent, "the brain hears 'retry' only when AIRE already saw the ask"
    assert sent.behavioral_guidance == "GUIA", "a resumed og118 turn is framed by the pipeline, not sent bare"
    roles = [c.args[3] for c in memory.store.await_args_list]
    assert roles == ["assistant"], "the first attempt already stored the ask; storing it again duplicates it"


@pytest.mark.asyncio
async def test_a_live_job_still_stores_the_ask_even_if_the_client_says_ask_stored(ledger, monkeypatch):
    """Resistencia: `ask_stored` lo pone sólo el runner al reanudar; el alta en
    vivo lo apaga, así que un cliente no puede saltarse el guardado."""
    memory = _memory()
    monkeypatch.setattr(
        aire_route, "turn_via_aire", AsyncMock(return_value=TurnResponse(text="ok", model="m", output_tokens=1))
    )
    monkeypatch.setattr(turn_pipeline, "get_memory", AsyncMock(return_value=memory))
    from persona_runner.core.schemas import TurnRequest

    req = TurnRequest(
        channel_id="conv-1",
        user_id=BERNARD,
        user_name="Bernard",
        user_text="hola",
        persona_id="insult",
        pipeline="runner",
        surface="og118",
        job_id="og2",
        ask_stored=True,
    )
    with (
        patch("persona_core.turn.context.guidance_for_turn", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.context.other_people_block_for_turn", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.context.build_persona_corpus_block", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.pipeline.FactExtractor"),
    ):
        job = await turn_jobs.submit(req, runner=turn_pipeline.serve_turn)
        await job.task
    assert [c.args[3] for c in memory.store.await_args_list] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_boot_resumes_orphans_through_serve_turn_not_straight_to_aire(monkeypatch):
    from persona_runner import runner

    used = []

    async def fake_resume(runner_fn):
        used.append(runner_fn)
        return 0

    monkeypatch.setattr(aire_route, "verify_aire_route", lambda: None)
    monkeypatch.setattr(turn_jobs, "resume_stale_at_boot", fake_resume)
    monkeypatch.setattr(turn_jobs, "drain_for_shutdown", AsyncMock(return_value=0))
    monkeypatch.setattr(turn_jobs.JOBS, "start_heartbeat", lambda: None)
    monkeypatch.setattr(turn_jobs.JOBS, "stop_heartbeat", AsyncMock())
    monkeypatch.setattr(turn_pipeline, "warm_at_boot", AsyncMock())
    monkeypatch.setattr(turn_pipeline, "close_memory", AsyncMock())
    monkeypatch.setattr(aire_route, "close_backends", AsyncMock())

    async with runner._lifespan(FastAPI()):
        await asyncio.sleep(0)
    assert used == [turn_pipeline.serve_turn]
