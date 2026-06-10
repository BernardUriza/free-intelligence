"""Tests for the turn pipeline orchestrator (PR 2).

Covers ``run_pipeline`` behavior independently of the concrete stages:

- ``StageStop`` short-circuits with the stop's outcome, no failure log.
- ``StageFailure`` in a BUSINESS stage aborts with ``failed:<stage>``.
- ``StageFailure`` in a COSMETIC stage is logged and the pipeline continues.
- Unexpected ``Exception`` in BUSINESS becomes ``FailureClass.UNEXPECTED``.
- Unexpected ``Exception`` in COSMETIC is swallowed.
- BACKGROUND stages are spawned via ``ctx.spawn_task`` and never block
  the pipeline; failures inside them are isolated by the spawner.

These tests use a minimal ``TurnCtx`` populated with mock fields — the
orchestrator does not care about the semantic content of ``TurnCtx``,
only that stages can read/write it.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from insult.cogs.chat._failure import Criticality, FailureClass, StageFailure, StageStop
from insult.cogs.chat.pipeline import Stage, TurnCtx, TurnRuntimeDeps, run_pipeline
from insult.cogs.chat.stages import _stage_ensure_payload


def _mk_ctx(spawn_task: Any = None) -> TurnCtx:
    """Build a TurnCtx with mock fields. The orchestrator never touches
    these — they exist so the dataclass can be constructed."""
    return TurnCtx(
        message=MagicMock(),
        text="hi",
        turn_start=time.monotonic(),
        deps=TurnRuntimeDeps(
            memory=MagicMock(),
            settings=MagicMock(),
            bot=MagicMock(),
            expression_history=MagicMock(),
            opus_budget=MagicMock(),
            spawn_task=spawn_task or (lambda *a, **kw: None),
            all_tools=[],
            facts=MagicMock(),
            stance=MagicMock(),
            arc=MagicMock(),
        ),
    )


@pytest.mark.asyncio
async def test_all_stages_succeed_returns_ok():
    calls: list[str] = []

    async def s1(ctx: TurnCtx) -> None:
        calls.append("s1")

    async def s2(ctx: TurnCtx) -> None:
        calls.append("s2")

    ctx = _mk_ctx()
    result = await run_pipeline(
        ctx,
        [
            Stage("s1", Criticality.BUSINESS, s1),
            Stage("s2", Criticality.BUSINESS, s2),
        ],
    )

    assert result.outcome == "ok"
    assert result.failure_stage is None
    assert result.failure_class is None
    assert calls == ["s1", "s2"]
    assert "s1" in result.stage_timings
    assert "s2" in result.stage_timings


@pytest.mark.asyncio
async def test_stage_stop_short_circuits_with_outcome():
    """StageStop is treated as success — no failure log, outcome
    propagates as-is. Used for the triviality gate."""
    calls: list[str] = []

    async def s1(ctx: TurnCtx) -> None:
        calls.append("s1")
        raise StageStop("trivial_skipped")

    async def s2(ctx: TurnCtx) -> None:
        calls.append("s2")  # must NOT run

    result = await run_pipeline(
        _mk_ctx(),
        [
            Stage("s1", Criticality.BUSINESS, s1),
            Stage("s2", Criticality.BUSINESS, s2),
        ],
    )

    assert result.outcome == "trivial_skipped"
    assert result.failure_stage is None
    assert calls == ["s1"]


@pytest.mark.asyncio
async def test_business_stage_failure_aborts_with_typed_outcome():
    """BUSINESS StageFailure aborts and produces failed:<stage>."""
    calls: list[str] = []

    async def s1(ctx: TurnCtx) -> None:
        calls.append("s1")
        raise StageFailure(
            stage="s1",
            failure_class=FailureClass.LLM_FAILED,
            error_type="DummyError",
            error_msg="boom",
            elapsed_ms=42,
        )

    async def s2(ctx: TurnCtx) -> None:
        calls.append("s2")  # must NOT run

    result = await run_pipeline(
        _mk_ctx(),
        [
            Stage("s1", Criticality.BUSINESS, s1),
            Stage("s2", Criticality.BUSINESS, s2),
        ],
    )

    assert result.outcome == "failed:s1"
    assert result.failure_stage == "s1"
    assert result.failure_class == "llm_failed"
    assert calls == ["s1"]


@pytest.mark.asyncio
async def test_cosmetic_stage_failure_is_logged_and_swallowed():
    """COSMETIC StageFailure logs a warning and the pipeline continues
    to the next stage. Used for telemetry stages."""
    calls: list[str] = []

    async def cosmetic(ctx: TurnCtx) -> None:
        calls.append("cosmetic")
        raise StageFailure(
            stage="cosmetic",
            failure_class=FailureClass.UNEXPECTED,
            error_type="DummyError",
            error_msg="telemetry blip",
            elapsed_ms=5,
        )

    async def after(ctx: TurnCtx) -> None:
        calls.append("after")

    result = await run_pipeline(
        _mk_ctx(),
        [
            Stage("cosmetic", Criticality.COSMETIC, cosmetic),
            Stage("after", Criticality.BUSINESS, after),
        ],
    )

    assert result.outcome == "ok"
    assert result.failure_stage is None
    assert calls == ["cosmetic", "after"]


@pytest.mark.asyncio
async def test_unexpected_exception_in_business_becomes_unexpected_failure():
    """A non-StageFailure exception in BUSINESS is wrapped as
    FailureClass.UNEXPECTED — no exception escapes the orchestrator."""

    async def s1(ctx: TurnCtx) -> None:
        raise ValueError("surprise")

    result = await run_pipeline(
        _mk_ctx(),
        [Stage("s1", Criticality.BUSINESS, s1)],
    )

    assert result.outcome == "failed:s1"
    assert result.failure_stage == "s1"
    assert result.failure_class == "unexpected"


@pytest.mark.asyncio
async def test_unexpected_exception_in_cosmetic_is_swallowed():
    async def cosmetic(ctx: TurnCtx) -> None:
        raise ValueError("surprise")

    async def after(ctx: TurnCtx) -> None:
        return None

    result = await run_pipeline(
        _mk_ctx(),
        [
            Stage("cosmetic", Criticality.COSMETIC, cosmetic),
            Stage("after", Criticality.BUSINESS, after),
        ],
    )

    assert result.outcome == "ok"


@pytest.mark.asyncio
async def test_background_stage_spawned_via_ctx_spawn_task():
    """BACKGROUND stages are scheduled via ctx.spawn_task; the
    pipeline does NOT await them. Failures inside are isolated."""
    spawned: list[tuple[str, Any]] = []

    def fake_spawn(coro, name: str = "") -> None:
        spawned.append((name, coro))
        # close the coroutine so the warning about unawaited coroutine
        # does not pollute the test output
        coro.close()

    calls: list[str] = []

    async def s1(ctx: TurnCtx) -> None:
        calls.append("s1")

    async def bg(ctx: TurnCtx) -> None:
        # Should NOT be called inline — only when the spawned coroutine
        # is awaited (we close it instead).
        calls.append("bg")  # pragma: no cover

    async def s2(ctx: TurnCtx) -> None:
        calls.append("s2")

    ctx = _mk_ctx(spawn_task=fake_spawn)
    result = await run_pipeline(
        ctx,
        [
            Stage("s1", Criticality.BUSINESS, s1),
            Stage("bg", Criticality.BACKGROUND, bg),
            Stage("s2", Criticality.BUSINESS, s2),
        ],
    )

    assert result.outcome == "ok"
    assert calls == ["s1", "s2"]  # bg NOT in this list — it was spawned
    assert len(spawned) == 1
    assert spawned[0][0] == "bg"


@pytest.mark.asyncio
async def test_background_stage_spawn_failure_does_not_block_pipeline():
    """If ctx.spawn_task itself raises (e.g. event loop shutting down),
    we log and continue the pipeline rather than crash."""
    calls: list[str] = []

    def crashing_spawn(coro, name: str = "") -> None:
        coro.close()
        raise RuntimeError("event loop closed")

    async def bg(ctx: TurnCtx) -> None:
        pass  # pragma: no cover

    async def after(ctx: TurnCtx) -> None:
        calls.append("after")

    ctx = _mk_ctx(spawn_task=crashing_spawn)
    result = await run_pipeline(
        ctx,
        [
            Stage("bg", Criticality.BACKGROUND, bg),
            Stage("after", Criticality.BUSINESS, after),
        ],
    )

    assert result.outcome == "ok"
    assert calls == ["after"]


@pytest.mark.asyncio
async def test_stage_timings_recorded_per_stage():
    """Each stage that runs — including the one that fails — must
    appear in ``stage_timings`` so KQL alerts can break down latency
    per stage. The timing values themselves are non-negative ints; we
    don't assert specific durations here because other tests in the
    suite ``monkeypatch.setattr`` ``asyncio.sleep`` which can leak
    timing assumptions across modules. Per-stage latency assertions
    belong in dedicated benchmark tests, not the orchestrator contract."""

    async def first(ctx: TurnCtx) -> None:
        # No sleep — relying on asyncio.sleep would make this test
        # fragile to the monkeypatched-sleep tests in test_llm_retry.
        pass

    async def failing(ctx: TurnCtx) -> None:
        raise StageFailure(
            stage="failing",
            failure_class=FailureClass.LLM_FAILED,
            error_type="E",
            error_msg="x",
            elapsed_ms=1,
        )

    result = await run_pipeline(
        _mk_ctx(),
        [
            Stage("first", Criticality.BUSINESS, first),
            Stage("failing", Criticality.BUSINESS, failing),
        ],
    )

    assert result.outcome == "failed:failing"
    assert set(result.stage_timings.keys()) == {"first", "failing"}
    # Timings must be ints; non-negative is the only invariant the
    # orchestrator contract promises.
    assert all(isinstance(v, int) and v >= 0 for v in result.stage_timings.values())


# ---------------------------------------------------------------------------
# _stage_ensure_payload — silent-tool-call recovery (v3.8.0 RM-1)
# ---------------------------------------------------------------------------
#
# Bug this guards: when the LLM fires `create_reminder` or `cancel_reminder`
# without any user-facing text, the delivery stage used to skip entirely
# (has_side_effects=True + empty body → `delivery_skipped`). The user saw
# silence in the channel where they asked. v3.7.x logs reproduced this as
# "se volvió a morir por pedir un recordatorio". The recovery in
# `_stage_ensure_payload` injects a short in-character confirmation so the
# action is visible without disturbing the path where the LLM did write text.


def _mk_tool_call(name: str):
    tc = MagicMock()
    tc.name = name
    return tc


def _mk_payload_ctx(*, response_text: str, tool_calls: list, reactions=None) -> TurnCtx:
    ctx = _mk_ctx()
    ctx.response_text = response_text
    ctx.raw_response_text = response_text
    ctx.reactions = reactions or []
    ctx.llm_response = MagicMock()
    ctx.llm_response.tool_calls = tool_calls
    return ctx


@pytest.mark.asyncio
async def test_ensure_payload_recovers_silent_create_reminder():
    """Empty text + create_reminder → confirmation gets injected."""
    ctx = _mk_payload_ctx(response_text="", tool_calls=[_mk_tool_call("create_reminder")])
    await _stage_ensure_payload(ctx)
    assert ctx.response_text == "Ya. Te aviso."


@pytest.mark.asyncio
async def test_ensure_payload_recovers_silent_cancel_reminder():
    ctx = _mk_payload_ctx(response_text="", tool_calls=[_mk_tool_call("cancel_reminder")])
    await _stage_ensure_payload(ctx)
    assert ctx.response_text == "Cancelado."


@pytest.mark.asyncio
async def test_ensure_payload_does_not_override_existing_text():
    """When the LLM wrote text alongside the tool call, leave it alone."""
    ctx = _mk_payload_ctx(
        response_text="Ya te lo apunté pa' las nueve.",
        tool_calls=[_mk_tool_call("create_reminder")],
    )
    await _stage_ensure_payload(ctx)
    assert ctx.response_text == "Ya te lo apunté pa' las nueve."


@pytest.mark.asyncio
async def test_ensure_payload_leaves_list_reminders_alone():
    """list_reminders posts its own message via tools.py — no injection needed."""
    ctx = _mk_payload_ctx(response_text="", tool_calls=[_mk_tool_call("list_reminders")])
    await _stage_ensure_payload(ctx)
    # No silent-tool injection for list_reminders; falls through with empty text.
    # `_stage_deliver` then short-circuits via `has_side_effects=True`.
    assert ctx.response_text == ""


@pytest.mark.asyncio
async def test_ensure_payload_empty_no_side_effects_uses_error_fallback():
    """No tool calls + no reactions + no text → generic in-character error."""
    ctx = _mk_payload_ctx(response_text="", tool_calls=[])
    await _stage_ensure_payload(ctx)
    assert ctx.response_text  # something non-empty got injected
    # The exact text comes from `get_error_response(ErrorType.GENERIC)` and
    # is randomized; we only assert it's not the silent-tool recovery line.
    assert ctx.response_text not in {"Ya. Te aviso.", "Cancelado."}
