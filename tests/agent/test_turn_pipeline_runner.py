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
    assert out.text == "Vives en GDL.", "the text the surface shows is marker-free"
    assert out.reactions == ["👀"] and out.empty_reason == "", "the reaction rides the wire (F5), not a log line"
    assert out.model == "claude-opus-4-7" and out.output_tokens == 12, "the brain's receipt survives"
    assert [c.args[3] for c in memory.store.await_args_list] == ["user", "assistant"]
    assert memory.store.await_args_list[0].args[2] == "Bernard"
    judge = extractor.return_value.spawn.call_args.args[0]
    assert isinstance(judge, turn_pipeline.InProcessJudge) and judge.persona_id == "insult"


def _pipeline_memory() -> MagicMock:
    memory = MagicMock()
    memory.get_recent = AsyncMock(return_value=[])
    memory.store = AsyncMock()
    memory.search = AsyncMock(return_value=[])
    memory.search_facts_semantic = AsyncMock(return_value=[])
    memory.list_pending_reminders = AsyncMock(return_value=[])
    memory.build_context = MagicMock(return_value=[])
    return memory


async def _serve_runner_turn(monkeypatch, brain_text: str, **patches) -> TurnResponse:
    """A runner-owned turn against a stubbed brain and memory (F5 receipts)."""

    async def brain(req):
        return TurnResponse(text=brain_text, model="m", output_tokens=3)

    monkeypatch.setattr(aire_route, "turn_via_aire", brain)
    monkeypatch.setattr(turn_pipeline, "get_memory", AsyncMock(return_value=_pipeline_memory()))
    with (
        patch("persona_core.turn.context.guidance_for_turn", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.context.other_people_block_for_turn", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.context.build_persona_corpus_block", new=AsyncMock(return_value=None)),
        patch("persona_core.turn.pipeline.FactExtractor"),
        patch("persona_core.turn.pipeline.resolve_gifs", new=patches.get("resolve_gifs", lambda *_: [])),
    ):
        return await turn_pipeline.serve_turn(_req(pipeline="runner", surface="og118", user_name="Bernard"))


@pytest.mark.asyncio
async def test_a_reaction_only_turn_returns_empty_text_with_its_reason(monkeypatch):
    """Before F5 og118 read this as 'external engine returned an empty answer':
    the reaction was logged as not delivered and the text came back blank with
    no explanation."""
    out = await _serve_runner_turn(monkeypatch, "[REACT:👀,🔥]")

    assert out.text == ""
    assert out.reactions == ["👀", "🔥"]
    assert out.empty_reason == "reactions_only"


@pytest.mark.asyncio
async def test_the_gif_urls_the_persona_resolved_ride_the_wire(monkeypatch):
    url = "https://tenor.com/view/facepalm-1"
    out = await _serve_runner_turn(monkeypatch, "Ajá. [GIF: facepalm]", resolve_gifs=lambda *_: [url])

    assert out.text == "Ajá."
    assert out.gif_urls == [url]
    assert out.empty_reason == ""


def test_a_response_written_before_f5_still_decodes():
    """A ledger row from a pre-F5 replica has no sidecar fields; the poll of that
    job must still decode (rolling update, or a job resumed across the deploy)."""
    old = TurnResponse.model_validate({"text": "hola", "model": "m", "stop_reason": "end_turn"})
    assert (old.reactions, old.gif_urls, old.empty_reason) == ([], [], "")


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
async def test_a_caller_with_no_principal_never_runs_the_pipeline(monkeypatch):
    brain = AsyncMock(return_value=TurnResponse(text="hola", model="m"))
    monkeypatch.setattr(aire_route, "turn_via_aire", brain)
    get_memory = AsyncMock()
    monkeypatch.setattr(turn_pipeline, "get_memory", get_memory)

    out = await turn_pipeline.serve_turn(_req(pipeline="runner", user_id="0"))

    assert out.text == "hola"
    get_memory.assert_not_awaited()


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
async def test_the_real_store_is_built_with_a_small_pool(monkeypatch):
    """2026-09-28: the fake store above accepted any kwargs, so a constructor
    the REAL `MemoryStore` rejects shipped and 500'd og118's first F3 turn.
    Only `connect` is faked here — the constructor is the real one."""
    from persona_core.memory.connection import ConnectionManager

    monkeypatch.setenv("POSTGRES_URL", "postgresql://x")
    monkeypatch.setattr(ConnectionManager, "connect", AsyncMock())

    store = await turn_pipeline.get_memory()

    assert isinstance(store, turn_pipeline.MemoryStore)
    assert (store._manager._min_size, store._manager._max_size) == (
        turn_pipeline._MEMORY_POOL_MIN,
        turn_pipeline._MEMORY_POOL_MAX,
    )


@pytest.mark.asyncio
async def test_a_store_that_cannot_be_built_degrades_to_a_bare_turn(monkeypatch):
    monkeypatch.setenv("POSTGRES_URL", "postgresql://x")

    def _boom(*a, **k):
        raise TypeError("unexpected keyword argument")

    monkeypatch.setattr(turn_pipeline, "MemoryStore", _boom)
    assert await turn_pipeline.get_memory() is None, "a constructor fault must never become a 500"


@pytest.mark.asyncio
async def test_warm_at_boot_builds_the_store_and_waits_for_the_embedder(monkeypatch):
    """The first turn of a cold replica paid ~25 s of model load inside its own
    budget (2026-09-28). Boot now builds the store and awaits the warmup
    `connect()` starts, so traffic finds the model resident."""
    store = MagicMock()
    store.wait_embeddings_prewarmed = AsyncMock(return_value=True)
    get_memory = AsyncMock(return_value=store)
    monkeypatch.setattr(turn_pipeline, "get_memory", get_memory)

    await turn_pipeline.warm_at_boot()

    get_memory.assert_awaited_once()
    store.wait_embeddings_prewarmed.assert_awaited_once()


@pytest.mark.asyncio
async def test_warm_at_boot_is_a_noop_without_postgres(monkeypatch):
    monkeypatch.setattr(turn_pipeline, "get_memory", AsyncMock(return_value=None))
    await turn_pipeline.warm_at_boot()  # no raise, nothing to warm


@pytest.mark.asyncio
async def test_warm_at_boot_never_takes_the_runner_down(monkeypatch):
    monkeypatch.setattr(turn_pipeline, "get_memory", AsyncMock(side_effect=RuntimeError("hf down")))
    await turn_pipeline.warm_at_boot()  # logged, swallowed


@pytest.mark.asyncio
async def test_close_memory_releases_the_pool_once(monkeypatch):
    store = MagicMock()
    store.close = AsyncMock()
    monkeypatch.setattr(turn_pipeline, "_memory", store)

    await turn_pipeline.close_memory()
    await turn_pipeline.close_memory()

    store.close.assert_awaited_once()
    assert turn_pipeline._memory is None


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
