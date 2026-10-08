"""The mutation pipeline's whole reason to exist: a stage that breaks its own
invariants does NOT get to ship its mutation. The founding incident — a dedup
stage that deleted 51% of a substantive reply to a vulnerable user, logged and
sent anyway — is the first test here on purpose. These pin the four violation
policies, the shrink guard, the must_preserve checks, and the rule that a stage
which raises never takes the turn down with it."""

import asyncio

import pytest

from aire.engine.invariants import preserve_min_length, preserve_question_marks, shrink_pct
from aire.engine.pipeline import MutationStage, PipelineViolationError, run_pipeline

REPLY = "A substantive reply to someone who needed it. " * 4


def run(stages, text, **kw):
    events: list[tuple] = []
    kw.setdefault("on_event", lambda e, f: events.append((e, f.get("stage"))))
    return asyncio.run(run_pipeline(stages, text, **kw)), events


def stage(name, fn, **kw):
    return MutationStage(name=name, apply=fn, **kw)


def test_a_stage_that_eats_half_the_reply_is_refused():
    out, events = run([stage("dedup", lambda t, c: t[: len(t) // 2])], REPLY)
    assert out == REPLY
    assert ("pipeline_violation", "dedup") in events


def test_a_legal_mutation_is_applied_and_announced():
    out, events = run([stage("upper", lambda t, c: t.upper())], "hola")
    assert out == "HOLA"
    assert ("mutation_applied", "upper") in events


def test_a_stage_that_swallows_the_questions_is_refused():
    strip = stage("strip", lambda t, c: t.replace("?", ""),
                  max_shrink_pct=None, must_preserve=[preserve_question_marks])
    out, _ = run([strip], "¿vienes? ¿o no?")
    assert out == "¿vienes? ¿o no?"


def test_min_length_is_enforced_by_name_in_the_violation():
    short = stage("short", lambda t, c: "hi", max_shrink_pct=None,
                  must_preserve=[preserve_min_length(20)])
    events: list[dict] = []
    out = asyncio.run(run_pipeline([short], "a long enough original text",
                                   on_event=lambda e, f: events.append(f)))
    assert out == "a long enough original text"
    assert "preserve_min_length(20)" in events[0]["failed_invariants"]


def test_a_raising_stage_never_takes_the_turn_down():
    out, events = run([stage("boom", lambda t, c: 1 / 0)], "intacto")
    assert out == "intacto"
    assert ("pipeline_stage_raised", "boom") in events


def test_a_check_that_raises_counts_as_a_violation():
    def explodes(before, after):
        raise RuntimeError("bad check")

    bad = stage("bad", lambda t, c: t + "!", max_shrink_pct=None, must_preserve=[explodes])
    events: list[dict] = []
    out = asyncio.run(run_pipeline([bad], "x", on_event=lambda e, f: events.append(f)))
    assert out == "x"
    assert events[0]["failed_invariants"] == ["explodes:raised"]


def test_policy_raise_really_raises():
    with pytest.raises(PipelineViolationError) as exc:
        run([stage("hard", lambda t, c: "", on_violation="raise")], "x" * 100)
    assert exc.value.stage == "hard"


def test_abort_pipeline_stops_the_chain_at_the_offender():
    stages = [stage("nuke", lambda t, c: "", on_violation="abort_pipeline"),
              stage("later", lambda t, c: t + " REACHED")]
    out, _ = run(stages, "original text long enough")
    assert out == "original text long enough"


def test_log_only_accepts_the_mutation_anyway():
    out, events = run([stage("loud", lambda t, c: "", on_violation="log_only")], "x" * 100)
    assert out == ""
    assert ("pipeline_violation", "loud") in events


def test_an_async_stage_is_awaited():
    async def slow(t, c):
        await asyncio.sleep(0)
        return t + "!"

    out, _ = run([stage("slow", slow)], "ok")
    assert out == "ok!"


def test_a_stage_that_changes_nothing_is_silent():
    out, events = run([stage("noop", lambda t, c: t)], "same")
    assert out == "same" and events == []


def test_shrink_pct_never_goes_negative_when_the_text_grew():
    assert shrink_pct("ab", "abcd") == 0.0
    assert shrink_pct("", "anything") == 0.0
