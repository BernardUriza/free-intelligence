"""Tests for fi_runner.guards — deterministic safety nets backed by fi-core.

The headline contract: a runner gets fi-core grounding (triage, anti-drift)
WITHOUT importing fi-core — it declares a guard, fi_runner imports fi-core.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pytest

from fi_runner import RetryPolicy, Runner, TurnResult
from fi_runner.guards import (
    AntiDriftGuard,
    GuardOutcome,
    TriageGuard,
    antidrift_guard,
    triage_guard,
)


# ---------------------------------------------------------------------------
# GuardOutcome
# ---------------------------------------------------------------------------


def test_guard_outcome_clean_by_default():
    o = GuardOutcome()
    assert o.clean is True
    assert o.metadata == {}


def test_guard_outcome_not_clean_when_retry_or_override():
    assert GuardOutcome(retry=True).clean is False
    assert GuardOutcome(text_override="x").clean is False


# ---------------------------------------------------------------------------
# triage_guard (observational, fi_core.cognitive PSYCHIATRY)
# ---------------------------------------------------------------------------


def test_triage_guard_builds_for_known_domain():
    g = triage_guard("psychiatry")
    assert isinstance(g, TriageGuard)
    assert g.name == "triage"


def test_triage_guard_unknown_domain_raises():
    with pytest.raises(KeyError, match="unknown clinical domain"):
        triage_guard("astrology")


def test_triage_guard_escalates_suicide_plan_to_critical():
    g = triage_guard("psychiatry")
    out = g.inspect(response_text="el paciente refiere plan suicida")
    assert out.clean is True  # observational — never edits/retries
    assert out.metadata["level"] == "CRITICAL"
    assert out.metadata["critical"] is True
    assert out.text_override is None


def test_triage_guard_considers_context_user_words():
    g = triage_guard("psychiatry")
    # The crisis marker is in the patient's words (context), not the LLM text.
    out = g.inspect(response_text="resumen neutro", context=("ya no quiero seguir viviendo",))
    assert out.metadata["level"] == "CRITICAL"


def test_triage_guard_calm_text_is_low_urgency():
    g = triage_guard("psychiatry")
    out = g.inspect(response_text="el paciente reporta ánimo estable y buen sueño")
    assert out.metadata["level"] != "CRITICAL"


# ---------------------------------------------------------------------------
# antidrift_guard (transformational, fi_core.persona)
# ---------------------------------------------------------------------------


def _break_pat():
    return [re.compile(r"(?i)\bas an AI\b")]


def test_antidrift_guard_builds():
    g = antidrift_guard(break_patterns=_break_pat(), reinforcement="STAY IN CHARACTER")
    assert isinstance(g, AntiDriftGuard)
    assert g.name == "antidrift"


def test_antidrift_guard_break_requests_retry_with_reinforcement():
    g = antidrift_guard(break_patterns=_break_pat(), reinforcement="STAY IN CHARACTER")
    out = g.inspect(response_text="As an AI, I cannot do that.")
    assert out.retry is True
    assert out.reinforcement == "STAY IN CHARACTER"
    assert out.metadata["severity"] == "break"
    assert out.clean is False


def test_antidrift_guard_clean_text_passes():
    g = antidrift_guard(break_patterns=_break_pat())
    out = g.inspect(response_text="Órale, claro que sí güey.")
    assert out.clean is True
    assert out.metadata == {}


def test_antidrift_guard_clarification_dump_retries_with_context_cue():
    g = antidrift_guard(
        break_patterns=_break_pat(),
        clarification_patterns=[re.compile(r"(?i)dime qué busc")],
        context_reinforcement="USE THE CONTEXT",
    )
    out = g.inspect(response_text="Dime qué buscas exactamente.")
    assert out.retry is True
    assert out.reinforcement == "USE THE CONTEXT"
    assert out.metadata["severity"] == "clarification_dump"


def test_antidrift_guard_soft_drift_logs_no_retry():
    g = antidrift_guard(
        break_patterns=_break_pat(),
        soft_patterns=[re.compile(r"(?i)great question")],
    )
    out = g.inspect(response_text="Great question! Let me help.")
    assert out.retry is False  # soft drift never retries
    assert out.metadata["severity"] == "soft_drift"


def test_antidrift_guard_break_precedes_clarification():
    g = antidrift_guard(
        break_patterns=_break_pat(),
        clarification_patterns=[re.compile(r"(?i)dime qué busc")],
        reinforcement="BREAK",
        context_reinforcement="CLAR",
    )
    out = g.inspect(response_text="As an AI, dime qué buscas.")
    assert out.metadata["severity"] == "break"  # break wins priority
    assert out.reinforcement == "BREAK"


def test_antidrift_guard_sanitize_drops_break_sentence():
    g = antidrift_guard(break_patterns=_break_pat())
    cleaned = g.sanitize("Hola amigo. As an AI, I cannot. Pero está bien.")
    assert "As an AI" not in cleaned
    assert "Hola amigo" in cleaned


# ---------------------------------------------------------------------------
# Runner integration — guards run in-process post-turn
# ---------------------------------------------------------------------------


@dataclass
class _FakeBackend:
    """Minimal AgentBackend that returns a fixed text (no SDK, no network)."""

    text: str

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        return TurnResult(text=self.text)


@dataclass
class _UppercaseGuard:
    """A transformational guard that rewrites the text (tests text_override)."""

    name: str = "upper"

    def inspect(
        self, *, response_text: str, context: tuple[str, ...] = (), final: bool = False
    ) -> GuardOutcome:
        return GuardOutcome(text_override=response_text.upper())


@pytest.mark.asyncio
async def test_runner_with_no_guards_passes_through():
    runner = Runner(backend=_FakeBackend("hola"), persona="p")
    result = await runner.run("x")
    assert result.text == "hola"
    assert result.guard_outcomes == {}


@pytest.mark.asyncio
async def test_runner_runs_triage_guard_and_collects_outcome():
    runner = Runner(
        backend=_FakeBackend("el paciente menciona plan suicida"),
        persona="clinical",
        guards=[triage_guard("psychiatry")],
    )
    result = await runner.run("hola doc")
    assert "triage" in result.guard_outcomes
    assert result.guard_outcomes["triage"].metadata["level"] == "CRITICAL"
    assert result.text == "el paciente menciona plan suicida"  # observational: unchanged


@pytest.mark.asyncio
async def test_runner_applies_guard_text_override():
    runner = Runner(backend=_FakeBackend("hola"), persona="p", guards=[_UppercaseGuard()])
    result = await runner.run("x")
    assert result.text == "HOLA"
    assert "upper" in result.guard_outcomes


# ---------------------------------------------------------------------------
# RetryPolicy — retry-on-guard pipeline in Runner.run
# ---------------------------------------------------------------------------


@dataclass
class _ScriptedBackend:
    """Returns a scripted text per attempt; records the prompt/model each call."""

    texts: list[str]
    calls: list[dict] = field(default_factory=list)

    async def run_turn(self, *, system_prompt, user_message, model=None, **kwargs):  # noqa: ANN001,ANN003
        i = len(self.calls)
        self.calls.append({"system_prompt": system_prompt, "model": model})
        return TurnResult(text=self.texts[min(i, len(self.texts) - 1)])


def _antidrift():
    return antidrift_guard(break_patterns=_break_pat(), reinforcement="STAY IN CHARACTER")


@pytest.mark.asyncio
async def test_default_policy_no_retry_sanitizes_on_single_attempt():
    # max_attempts=1 (default): the single attempt is final → break is sanitized,
    # not retried.
    be = _ScriptedBackend(texts=["As an AI, I cannot. Hola amigo."])
    runner = Runner(backend=be, persona="p", guards=[_antidrift()])
    result = await runner.run("x")
    assert len(be.calls) == 1  # no retry
    assert "As an AI" not in result.text
    assert "Hola amigo" in result.text


@pytest.mark.asyncio
async def test_retry_on_break_then_clean():
    be = _ScriptedBackend(texts=["As an AI, I cannot.", "Órale, claro güey."])
    runner = Runner(
        backend=be, persona="P", guards=[_antidrift()], retry_policy=RetryPolicy(max_attempts=2)
    )
    result = await runner.run("x")
    assert len(be.calls) == 2  # retried once
    assert result.text == "Órale, claro güey."
    assert "STAY IN CHARACTER" in be.calls[1]["system_prompt"]  # reinforcement appended
    assert "STAY IN CHARACTER" not in be.calls[0]["system_prompt"]  # not on first


@pytest.mark.asyncio
async def test_retry_exhausted_sanitizes_on_final():
    be = _ScriptedBackend(texts=["As an AI, no. Hola.", "As an AI, still broken. Adiós."])
    runner = Runner(
        backend=be, persona="P", guards=[_antidrift()], retry_policy=RetryPolicy(max_attempts=2)
    )
    result = await runner.run("x")
    assert len(be.calls) == 2
    assert "As an AI" not in result.text  # final attempt → sanitized
    assert "Adiós" in result.text
    assert result.guard_outcomes["antidrift"].metadata.get("sanitized") is True


@pytest.mark.asyncio
async def test_retry_escalates_to_fallback_model():
    be = _ScriptedBackend(texts=["As an AI.", "limpio güey"])
    runner = Runner(
        backend=be,
        persona="P",
        model="primary",
        guards=[_antidrift()],
        retry_policy=RetryPolicy(max_attempts=2, fallback_model="fallback"),
    )
    await runner.run("x")
    assert be.calls[0]["model"] == "primary"
    assert be.calls[1]["model"] == "fallback"


@pytest.mark.asyncio
async def test_no_retry_when_first_attempt_clean():
    be = _ScriptedBackend(texts=["Órale güey, todo bien."])
    runner = Runner(
        backend=be, persona="P", guards=[_antidrift()], retry_policy=RetryPolicy(max_attempts=3)
    )
    result = await runner.run("x")
    assert len(be.calls) == 1  # clean → no retry even with attempts available
    assert result.guard_outcomes["antidrift"].clean is True


# ---------------------------------------------------------------------------
# Post-processors — run once after guards/retry settle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runner_runs_post_processors():
    from fi_runner import MutationStage

    runner = Runner(
        backend=_FakeBackend("  hola mundo  "),
        persona="p",
        post_processors=[MutationStage(name="strip", apply=lambda t, ctx: t.strip(), max_shrink_pct=None)],
    )
    result = await runner.run("x")
    assert result.text == "hola mundo"


@pytest.mark.asyncio
async def test_post_processor_invariant_rejects_oversized_deletion():
    from fi_runner import MutationStage

    text = "this is a long substantive reply to the user"
    runner = Runner(
        backend=_FakeBackend(text),
        persona="p",
        post_processors=[MutationStage(name="nuke", apply=lambda t, ctx: t[:2], max_shrink_pct=0.40)],
    )
    result = await runner.run("x")
    assert result.text == text  # mutation rejected by the invariant


@pytest.mark.asyncio
async def test_post_processors_run_after_guard_sanitize():
    from fi_runner import MutationStage

    runner = Runner(
        backend=_FakeBackend("As an AI. Hola mundo."),
        persona="p",
        guards=[_antidrift()],  # sanitizes the "As an AI" sentence on final attempt
        post_processors=[MutationStage(name="up", apply=lambda t, ctx: t.upper(), max_shrink_pct=None)],
    )
    result = await runner.run("x")
    assert "AS AN AI" not in result.text  # guard sanitized first
    assert "HOLA MUNDO" in result.text  # then post-processor uppercased
