"""Tests for fi_runner.pipeline — post-turn mutation stages with invariants.

The point of the invariants: a cosmetic stage with a catch-all matcher must NOT
silently nuke good content. A violated invariant rejects the mutation (per the
stage's on_violation policy), logged, not silent.
"""

from __future__ import annotations

import pytest

from fi_runner.pipeline import (
    MutationStage,
    PipelineViolationError,
    preserve_min_length,
    preserve_question_marks,
    run_pipeline,
    run_pipeline_sync,
)


def _stage(name, fn, **kw):
    return MutationStage(name=name, apply=lambda t, ctx: fn(t), **kw)


# ---------------------------------------------------------------------------
# Basic application + ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stages_apply_in_order():
    stages = [
        _stage("strip", lambda t: t.strip(), max_shrink_pct=None),  # whitespace removal is legit
        _stage("upper", lambda t: t.upper(), max_shrink_pct=None),
    ]
    out = await run_pipeline(stages, "  hola  ")
    assert out == "HOLA"


@pytest.mark.asyncio
async def test_no_change_is_a_noop():
    out = await run_pipeline([_stage("id", lambda t: t)], "same")
    assert out == "same"


@pytest.mark.asyncio
async def test_async_stage_is_awaited():
    async def amut(t, ctx):  # noqa: ANN001
        return t + "!"

    out = await run_pipeline([MutationStage(name="bang", apply=amut, max_shrink_pct=None)], "hi")
    assert out == "hi!"


@pytest.mark.asyncio
async def test_ctx_is_passed_to_stage():
    def mut(t, ctx):  # noqa: ANN001
        return t + ctx.get("suffix", "")

    out = await run_pipeline([MutationStage(name="sfx", apply=mut, max_shrink_pct=None)], "x", {"suffix": "Y"})
    assert out == "xY"


# ---------------------------------------------------------------------------
# max_shrink_pct invariant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_shrink_pct_rejects_oversized_deletion():
    # A stage that deletes 90% of the text violates the default 0.40 floor → skip.
    stages = [_stage("nuke", lambda t: t[:1], max_shrink_pct=0.40)]
    out = await run_pipeline(stages, "this is a long substantive reply")
    assert out == "this is a long substantive reply"  # mutation rejected


@pytest.mark.asyncio
async def test_max_shrink_pct_none_allows_full_removal():
    stages = [_stage("clear", lambda t: "", max_shrink_pct=None)]
    out = await run_pipeline(stages, "removable")
    assert out == ""


# ---------------------------------------------------------------------------
# must_preserve invariants
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preserve_question_marks_blocks_question_loss():
    stages = [
        _stage(
            "drop_q",
            lambda t: t.replace("?", ""),
            max_shrink_pct=None,
            must_preserve=[preserve_question_marks],
        )
    ]
    out = await run_pipeline(stages, "¿estás bien?")
    assert out == "¿estás bien?"  # rejected — would lose the question


@pytest.mark.asyncio
async def test_preserve_min_length_blocks_undershoot():
    stages = [
        _stage(
            "trunc",
            lambda t: t[:3],
            max_shrink_pct=None,
            must_preserve=[preserve_min_length(10)],
        )
    ]
    out = await run_pipeline(stages, "a fairly long reply")
    assert out == "a fairly long reply"  # rejected — below floor


# ---------------------------------------------------------------------------
# on_violation policies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_abort_pipeline_stops_further_stages():
    stages = [
        _stage("nuke", lambda t: "x", max_shrink_pct=0.40, on_violation="abort_pipeline"),
        _stage("never", lambda t: t + " SHOULD NOT RUN", max_shrink_pct=None),
    ]
    out = await run_pipeline(stages, "long original text here")
    assert out == "long original text here"
    assert "SHOULD NOT RUN" not in out


@pytest.mark.asyncio
async def test_raise_policy_raises():
    stages = [_stage("nuke", lambda t: "x", max_shrink_pct=0.40, on_violation="raise")]
    with pytest.raises(PipelineViolationError):
        await run_pipeline(stages, "long original text here")


@pytest.mark.asyncio
async def test_log_only_accepts_mutation():
    stages = [_stage("nuke", lambda t: "x", max_shrink_pct=0.40, on_violation="log_only")]
    out = await run_pipeline(stages, "long original text here")
    assert out == "x"  # accepted despite violation


@pytest.mark.asyncio
async def test_raising_stage_keeps_pre_mutation_text():
    def boom(t, ctx):  # noqa: ANN001
        raise ValueError("stage exploded")

    out = await run_pipeline([MutationStage(name="boom", apply=boom)], "intact")
    assert out == "intact"


# ---------------------------------------------------------------------------
# on_event sink
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_event_sink_receives_events():
    events: list[tuple[str, dict]] = []
    stages = [
        _stage("ok", lambda t: t + "!", max_shrink_pct=None),
        _stage("nuke", lambda t: "x", max_shrink_pct=0.40),  # violation → skip
    ]
    await run_pipeline(stages, "hello", on_event=lambda e, f: events.append((e, f)))
    names = [e for e, _ in events]
    assert "mutation_applied" in names
    assert "pipeline_violation" in names


def test_run_pipeline_sync_facade():
    out = run_pipeline_sync([_stage("up", lambda t: t.upper(), max_shrink_pct=None)], "hi")
    assert out == "HI"
