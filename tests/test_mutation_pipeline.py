"""Tests for the post-LLM Intercepting Filter pipeline.

Two layers of coverage:

1. **Unit** — the runner itself: each on_violation policy fires the
   correct outcome, sync and async stages compose, the built-in
   invariant helpers behave as advertised.
2. **Regression** — the literal 2026-05-06 bug. ``deduplicate_opener``
   nuked 51% of an empathic response to a vulnerable user because its
   matcher fired on the demonstrative *"Eso"*. With the pipeline
   guards (``preserve_react_markers`` + ``max_shrink_pct=0.30``), the
   mutation gets rejected and the original opener survives.

If the regression test ever turns red, the guards have either been
loosened, removed, or the matcher was tightened in a way that re-
introduced the same false-positive class.
"""

from __future__ import annotations

import pytest

from insult.core.character import (
    MutationStage,
    PipelineViolationError,
    deduplicate_opener,
    preserve_min_length,
    preserve_question_marks,
    preserve_react_markers,
    run_pipeline,
)

# ---------------------------------------------------------------------------
# Invariant helpers — pure-fn unit tests
# ---------------------------------------------------------------------------


def test_preserve_react_markers_passes_when_count_unchanged():
    assert preserve_react_markers("hi [REACT:👀]", "hello [REACT:👀]") is True


def test_preserve_react_markers_fails_when_marker_dropped():
    """Exact failure mode of the Alex bug."""
    before = "Eso fue muy pesado. [REACT:🌊💙🪷🫂🌿✨]\n\nY tú lo recibiste con cuidado."
    after = "Y tú lo recibiste con cuidado."
    assert preserve_react_markers(before, after) is False


def test_preserve_react_markers_passes_when_no_markers_originally():
    assert preserve_react_markers("plain text", "plain text edited") is True


def test_preserve_question_marks_blocks_dropping_a_question():
    assert preserve_question_marks("¿cómo estás?", "muy bien") is False


def test_preserve_question_marks_passes_when_neither_has_one():
    assert preserve_question_marks("hola", "qué tal") is True


def test_preserve_min_length_blocks_collapse_below_floor():
    check = preserve_min_length(50)
    long_input = "x" * 100
    short_output = "x" * 30
    assert check(long_input, short_output) is False
    assert check(long_input, "y" * 60) is True


def test_preserve_min_length_passes_when_input_already_short():
    """The floor only applies if the input was above it."""
    check = preserve_min_length(50)
    assert check("x" * 10, "y" * 5) is True


# ---------------------------------------------------------------------------
# Runner — on_violation policies
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skip_stage_rejects_mutation_continues_pipeline():
    """skip_stage rejects the bad stage's output AND keeps the next stage running."""
    stage_bad = MutationStage(
        name="too_aggressive",
        apply=lambda t, _ctx: "x",  # nukes 99% of input
        max_shrink_pct=0.30,
        on_violation="skip_stage",
    )
    stage_after = MutationStage(
        name="appender",
        apply=lambda t, _ctx: t + "!",
        max_shrink_pct=0.30,
        on_violation="skip_stage",
    )
    out = await run_pipeline([stage_bad, stage_after], "long input that should survive")
    # Bad stage rejected → second stage operates on original input
    assert out == "long input that should survive!"


@pytest.mark.asyncio
async def test_abort_pipeline_returns_pre_mutation_text():
    """abort_pipeline halts further stages and returns the text before this stage."""
    aggressive = MutationStage(
        name="nuke",
        apply=lambda t, _ctx: "",
        max_shrink_pct=0.30,
        on_violation="abort_pipeline",
    )
    never_runs = MutationStage(
        name="should_not_run",
        apply=lambda t, _ctx: "RAN",
    )
    out = await run_pipeline([aggressive, never_runs], "important content here")
    assert out == "important content here"


@pytest.mark.asyncio
async def test_raise_policy_lifts_exception():
    raiser = MutationStage(
        name="boom",
        apply=lambda t, _ctx: "",
        max_shrink_pct=0.30,
        on_violation="raise",
    )
    with pytest.raises(PipelineViolationError) as exc:
        await run_pipeline([raiser], "hello world this is a long input")
    assert exc.value.stage == "boom"
    assert "max_shrink_pct" in exc.value.failed[0]


@pytest.mark.asyncio
async def test_log_only_accepts_violation_but_warns():
    """Shadow-mode rollout — accept the mutation, just log it."""
    bad = MutationStage(
        name="loud_but_silent",
        apply=lambda t, _ctx: "x",
        max_shrink_pct=0.10,
        on_violation="log_only",
    )
    out = await run_pipeline([bad], "long enough input")
    assert out == "x"  # mutation accepted despite violation


@pytest.mark.asyncio
async def test_passing_stage_emits_mutation_applied_event(caplog):
    """Healthy mutation: no violation, runner records it as a normal event."""
    import logging

    caplog.set_level(logging.INFO)
    ok = MutationStage(
        name="trim",
        apply=lambda t, _ctx: t.strip(),
        max_shrink_pct=0.50,
    )
    out = await run_pipeline([ok], "  hello world  ")
    assert out == "hello world"
    # No "pipeline_violation" record should have fired.
    assert not any("pipeline_violation" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_async_stage_is_awaited():
    async def _async_apply(t: str, _ctx: dict) -> str:
        return t + " (async)"

    stage = MutationStage(name="async_op", apply=_async_apply, max_shrink_pct=None)
    out = await run_pipeline([stage], "hello")
    assert out == "hello (async)"


@pytest.mark.asyncio
async def test_raising_stage_is_treated_as_no_op():
    """A stage that throws does NOT mutate — the runner logs and skips it."""

    def _bad(t, _ctx):
        raise RuntimeError("upstream broke")

    stage = MutationStage(name="explody", apply=_bad)
    out = await run_pipeline([stage], "intact")
    assert out == "intact"


@pytest.mark.asyncio
async def test_must_preserve_failure_skips_stage():
    """A custom invariant failing fires the on_violation policy."""
    stage = MutationStage(
        name="strip_questions",
        apply=lambda t, _ctx: t.replace("?", ""),
        max_shrink_pct=None,
        must_preserve=[preserve_question_marks],
        on_violation="skip_stage",
    )
    out = await run_pipeline([stage], "really? are you sure?")
    assert out == "really? are you sure?"  # rejected — '?' was nuked


@pytest.mark.asyncio
async def test_no_op_stages_do_not_log_mutation_applied(caplog):
    """A stage that returns the same string is silent (no spam)."""
    import logging

    caplog.set_level(logging.INFO)
    ident = MutationStage(name="identity", apply=lambda t, _ctx: t)
    await run_pipeline([ident], "anything")
    assert not any("mutation_applied" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# REGRESSION — the actual 2026-05-06 bug
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alex_2026_05_06_opener_with_eso_is_preserved():
    """The literal turn from KQL (request_id=f3bf696d).

    The LLM produced 235 chars opening with *"Eso que describes de
    ella..."* and embedding ``[REACT:🌊💙🪷🫂🌿✨]``. ``deduplicate_opener``
    matched "eso" against a previous opener in ``recent_openers`` that
    also began with "Eso suena a...", treated them as a name collision,
    and stripped the entire first line — losing both the empathic
    acknowledgment AND the reaction markers, leaving only a procedural
    follow-up question.

    With the new guards (preserve_react_markers + max_shrink_pct=0.30
    + skip_stage policy) this mutation fails BOTH invariants and gets
    rejected — the original opener is what reaches Discord.
    """
    raw_response = (
        "Eso que describes de ella... no es un dato menor. "
        "Es una carga muy pesada la que cargó con decirte eso. "
        "[REACT:🌊💙🪷🫂🌿✨]\n\n"
        "Y me parece que tú lo recibiste con más cuidado del que la situación obligaba. "
        "¿Cómo te sentiste cuando te lo dijo?"
    )
    recent_openers = [
        "Eso suena a que encontraste algo que funciona para ti.",
        "Tiene mucho sentido.",
    ]
    stage = MutationStage(
        name="deduplicate_opener",
        apply=lambda t, _ctx, _o=recent_openers: deduplicate_opener(t, _o),
        max_shrink_pct=0.30,
        must_preserve=[preserve_react_markers],
        on_violation="skip_stage",
    )
    out = await run_pipeline([stage], raw_response)
    # The pre-fix bug shipped the response without the opener — assert
    # the opener (and its REACT block) survived.
    assert "Eso que describes de ella" in out
    assert "[REACT:🌊💙🪷🫂🌿✨]" in out
    # Length recovered — the silent 51% shrink does not happen anymore.
    assert len(out) >= int(len(raw_response) * 0.95)


@pytest.mark.asyncio
async def test_legitimate_dedup_still_fires_on_real_name_collision():
    """The guards shouldn't make the dedup useless. When the opener
    really IS a repeated personal name, the mutation should pass
    invariants and apply normally."""
    response = "¡BERNARD!\n\nEso que dices es interesante."
    recent_openers = [
        "¡BERNARD! Mira nada más.",
        "¡BERNARD! Otra vez con eso.",
    ]
    stage = MutationStage(
        name="deduplicate_opener",
        apply=lambda t, _ctx, _o=recent_openers: deduplicate_opener(t, _o),
        # Use the same caps as production so this is a realistic test
        max_shrink_pct=0.50,
        must_preserve=[preserve_react_markers],
        on_violation="skip_stage",
    )
    out = await run_pipeline([stage], response)
    assert "¡BERNARD!" not in out
    assert "Eso que dices es interesante." in out
