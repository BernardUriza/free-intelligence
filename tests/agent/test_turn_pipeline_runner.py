"""The runner as a pipeline host (F3) — `serve_turn` and its in-process judge.

`pipeline="caller"` (the gateway) must reach the brain byte-identical: the
gateway already ran the pipeline, and running it twice would store every turn
twice. `pipeline="runner"` (og118) must run `run_turn` around the same brain
call. Without Postgres the runner-owned turn degrades to the bare pre-F3 turn,
never to a failed one.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from persona_runner.api import judge as judge_api
from persona_runner.api import turn_pipeline
from persona_runner.core.schemas import JudgeResponse, TurnRequest, TurnResponse
from persona_runner.engine import aire_route

BERNARD = "907264175246569543"


def _req(**overrides) -> TurnRequest:
    fields = {"channel_id": "conv-1", "user_id": BERNARD, "user_text": "¿qué sabes de mí?", "persona_id": "insult"}
    fields.update(overrides)
    return TurnRequest(**fields)


@pytest.fixture(autouse=True)
def _fresh_process_state():
    turn_pipeline.reset_memory()
    judge_api.reset_judge_semaphore()
    yield
    turn_pipeline.reset_memory()


@pytest.mark.asyncio
async def test_a_caller_owned_turn_reaches_the_brain_untouched(monkeypatch):
    seen: list[TurnRequest] = []

    async def brain(req):
        seen.append(req)
        return TurnResponse(text="ok", model="m")

    monkeypatch.setattr(aire_route, "turn_via_aire", brain)
    run_turn = AsyncMock()
    monkeypatch.setattr(turn_pipeline, "run_turn", run_turn)
    req = _req(behavioral_guidance="GUIA-DEL-GATEWAY")

    out = await turn_pipeline.serve_turn(req)

    assert out.text == "ok"
    assert seen == [req], "the gateway's framed request must reach the brain as sent"
    run_turn.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_runner_owned_turn_runs_the_pipeline_around_the_brain(monkeypatch):
    seen: list[TurnRequest] = []

    async def brain(req):
        seen.append(req)
        return TurnResponse(text="Vives en GDL. [REACT:👀]", model="claude-opus-4-7", output_tokens=12)

    monkeypatch.setattr(aire_route, "turn_via_aire", brain)
    memory = MagicMock()
    memory.get_recent = AsyncMock(return_value=[])
    memory.store = AsyncMock()
    memory.search = AsyncMock(return_value=[])
    memory.search_facts_semantic = AsyncMock(return_value=[])
    memory.list_pending_reminders = AsyncMock(return_value=[])
    memory.build_context = MagicMock(return_value=[])
    monkeypatch.setattr(turn_pipeline, "get_memory", AsyncMock(return_value=memory))

    with (
        patch("persona_core.turn.context.guidance_for_turn", new=AsyncMock(return_value="GUIA")),
        patch("persona_core.turn.context.other_people_block_for_turn", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.context.build_persona_corpus_block", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.pipeline.FactExtractor") as extractor,
    ):
        out = await turn_pipeline.serve_turn(_req(pipeline="runner", surface="og118", user_name="Bernard"))

    (sent,) = seen
    assert sent.behavioral_guidance == "GUIA"
    assert "<current_time>" in sent.user_text and sent.user_text.endswith("¿qué sabes de mí?")
    assert out.text == "Vives en GDL.", "markers and reactions never reach the surface"
    assert out.model == "claude-opus-4-7" and out.output_tokens == 12, "the brain's receipt survives"
    assert [c.args[3] for c in memory.store.await_args_list] == ["user", "assistant"]
    assert memory.store.await_args_list[0].args[2] == "Bernard"
    judge = extractor.return_value.spawn.call_args.args[0]
    assert isinstance(judge, turn_pipeline.InProcessJudge) and judge.persona_id == "insult"


@pytest.mark.asyncio
async def test_a_nameless_surface_takes_the_name_the_principal_already_uses():
    memory = MagicMock()
    memory.get_latest_username = AsyncMock(return_value="bernard2389")
    assert await turn_pipeline._known_name(memory, BERNARD) == "bernard2389"
    memory.get_latest_username.assert_awaited_once_with(BERNARD)


@pytest.mark.asyncio
async def test_a_failed_name_lookup_falls_back_to_the_id():
    memory = MagicMock()
    memory.get_latest_username = AsyncMock(side_effect=ConnectionError("pg blip"))
    assert await turn_pipeline._known_name(memory, BERNARD) == BERNARD
    memory.get_latest_username = AsyncMock(return_value=None)
    assert await turn_pipeline._known_name(memory, "nuevo") == "nuevo"


@pytest.mark.asyncio
async def test_without_postgres_the_runner_turn_runs_bare(monkeypatch):
    brain = AsyncMock(return_value=TurnResponse(text="sin memoria", model="m"))
    monkeypatch.setattr(aire_route, "turn_via_aire", brain)
    monkeypatch.setattr(turn_pipeline, "get_memory", AsyncMock(return_value=None))
    run_turn = AsyncMock()
    monkeypatch.setattr(turn_pipeline, "run_turn", run_turn)

    out = await turn_pipeline.serve_turn(_req(pipeline="runner"))

    assert out.text == "sin memoria"
    run_turn.assert_not_awaited()
    assert brain.await_args.args[0].user_text == "¿qué sabes de mí?"


@pytest.mark.asyncio
async def test_no_postgres_url_means_no_store(monkeypatch):
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    assert await turn_pipeline.get_memory() is None


@pytest.mark.asyncio
async def test_a_failed_connect_is_retried_on_the_next_turn(monkeypatch):
    monkeypatch.setenv("POSTGRES_URL", "postgresql://x")
    attempts: list[int] = []

    class _Store:
        def __init__(self, *a, **k):
            pass

        async def connect(self):
            attempts.append(1)
            if len(attempts) == 1:
                raise ConnectionError("pg down")

    monkeypatch.setattr(turn_pipeline, "MemoryStore", _Store)
    assert await turn_pipeline.get_memory() is None
    assert isinstance(await turn_pipeline.get_memory(), _Store), "a blip must heal without a restart"
    assert await turn_pipeline.get_memory() is await turn_pipeline.get_memory(), "one store per process"


@pytest.mark.asyncio
async def test_the_in_process_judge_queues_behind_the_judge_gate(monkeypatch):
    seen = []

    async def judge(req):
        seen.append((req, judge_api.get_judge_semaphore().locked()))
        return JudgeResponse(text="[]", model="haiku")

    monkeypatch.setattr(aire_route, "judge_via_aire", judge)
    monkeypatch.setattr(judge_api.config, "JUDGE_MAX_CONCURRENCY", 1)
    judge_api.reset_judge_semaphore()

    out = await turn_pipeline.InProcessJudge("vultur").utility_call(
        "extrae facts", [{"role": "user", "content": "me gusta el cine"}], model="claude-haiku-4-5"
    )

    assert out.text == "[]"
    ((req, gate_held),) = seen
    assert gate_held, "the call must run INSIDE the shared judge semaphore"
    assert (req.persona_id, req.user_text, req.model) == ("vultur", "me gusta el cine", "claude-haiku-4-5")


@pytest.mark.asyncio
async def test_the_in_process_judge_refuses_an_empty_prompt():
    with pytest.raises(ValueError, match="empty user_text"):
        await turn_pipeline.InProcessJudge("insult").utility_call("s", [{"role": "assistant", "content": "x"}])
