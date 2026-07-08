"""Per-session model routing for the agent runner.

Wraps `insult.core.routing.select_model` for use inside the FastAPI runner.
The legacy LLM path (insult/core/llm.py, pre-F3) ran preset classification
+ flow analysis + routing inline; the runner-extracted architecture lost
that step when the runner was first wired with a hardcoded
AGENT_RUNNER_MODEL (claude-sonnet-4-6). Bernard's explicit 2026-05-13 call
was the 3-tier router (memory: reference_llm_model_choice_2026_05_13).
This module ports that decision back into the runner.

Scope tradeoffs (v3.9.71, v1):

- **Per-session stickiness, not per-turn.** The router runs ONCE when a
  channel opens a new ClaudeSDKClient. Subsequent turns on the same
  session reuse that model. Why: per-turn rerouting would force the
  runner to close+reopen the SDK client (the model is set at
  ClaudeAgentOptions construction time), which invalidates the prompt
  cache — defeating the whole reason F3 introduced long-lived clients.
  Concrete cost: an Opus turn forced mid-Haiku session would pay ~25k
  tokens of cache miss for one routing decision. Not worth it.
  Net behavior: if a user enters crisis mid-conversation, their CURRENT
  session stays on whatever was first picked, but the NEXT session
  (post-reaper, post-DELETE, post-restart) picks up the new tier.

- **Preset classifier runs on current_message only.** The classifier
  signature accepts last-5-messages context but populating it requires
  a synchronous DB read in the runner's hot path. v1 trades that
  fidelity for latency; the classifier's reasoning logs the partial
  context so we can measure miss rate before adding the fetch.

- **Flow analysis stubbed to neutral.** select_model only consults
  flow on the crisis branch (`flow.pressure.detected_state ==
  VULNERABLE and flow.pressure.pressure_level >= 4`). Stubbing to
  NORMAL/pressure=0 means crisis is driven by preset
  (RESPECTFUL_SERIOUS) OR disclosure_severity >= 3 — the two
  signals that survive without the full pipeline. Vulnerable users
  with the disclosure overlay are still routed to Opus correctly.

- **disclosure_severity derived from disclosure_log table.** A
  single asyncpg query (`SELECT COALESCE(MAX(severity), 0)`) per
  new session. ~5ms; negligible vs SDK init cost.

- **Opus budget is in-memory, per-process.** Module-singleton
  `_BUDGET`. Loses state on container restart — same constraint as
  the legacy LLM path's OpusBudget. Acceptable: a restart during a
  crisis already disrupts continuity, persisting the cap across
  restarts would make the "I'm getting Opus" experience feel
  random after infra blips.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import asyncpg
import structlog

from persona_runner.model_routing import ModelChoice, OpusBudget, select_model
from personas.insult.core.flows.types import (
    AwarenessAnalysis,
    ConversationPattern,
    EpistemicAnalysis,
    EpistemicMove,
    ExpressionAnalysis,
    FlowAnalysis,
    PressureAnalysis,
    ResponseShape,
    StyleFlavor,
    UserState,
)
from personas.insult.core.presets import classify_preset

log = structlog.get_logger()

# Env-overridable model IDs per tier. Defaults match the family Bernard
# named in memory (Opus 4.7 / Sonnet 4.6 / Haiku 4.5). Override per env
# to A/B a new family without code changes.
CASUAL_MODEL = os.environ.get("ROUTER_CASUAL_MODEL", "claude-haiku-4-5-20251001")
DEPTH_MODEL = os.environ.get("ROUTER_DEPTH_MODEL", "claude-sonnet-4-6")
CRISIS_MODEL = os.environ.get("ROUTER_CRISIS_MODEL", "claude-opus-4-7")
OPUS_24H_CAP = int(os.environ.get("ROUTER_OPUS_24H_CAP", "20"))

# Allow ops to disable routing wholesale and pin one model. Useful for
# A/B comparisons and for instant rollback if the router misroutes in
# prod. When set, ALL turns use this model regardless of signals.
FORCED_MODEL = os.environ.get("AGENT_RUNNER_FORCED_MODEL", "").strip()

_BUDGET = OpusBudget(cap=OPUS_24H_CAP)


@dataclass(frozen=True)
class RoutingDecision:
    """What route_for_session decided + enough info to log it."""

    model: str
    tier: str
    reason: str
    preset_mode: str
    preset_modifiers: list[str]
    disclosure_severity: int
    forced: bool


def _neutral_flow() -> FlowAnalysis:
    """Default FlowAnalysis: no crisis, no pressure, no patterns detected.

    The router only consults flow on the vulnerable+hard-pressure crisis
    branch. With UserState.NEUTRAL + pressure_level=0, that branch
    correctly falls through to the preset/disclosure-based decision.
    """
    return FlowAnalysis(
        epistemic=EpistemicAnalysis(
            assertion_density=0.0,
            hedging_score=0.0,
            fluff_score=0.0,
            contradiction_detected=False,
            vague_claim_count=0,
            recommended_move=EpistemicMove.NONE,
            move_reason="router_runtime_stub",
        ),
        pressure=PressureAnalysis(
            detected_state=UserState.NEUTRAL,
            state_confidence=0.5,
            pressure_level=0,
            pressure_reason="router_runtime_stub",
            clamped_by_preset=False,
        ),
        expression=ExpressionAnalysis(
            selected_shape=ResponseShape.LAYERED,
            selected_flavor=StyleFlavor.DRY,
            shape_reason="router_runtime_stub",
            flavor_reason="router_runtime_stub",
        ),
        awareness=AwarenessAnalysis(
            detected_pattern=ConversationPattern.NONE,
            pattern_confidence=0.0,
            meta_commentary=None,
            delayed_question=None,
            turns_in_pattern=0,
        ),
        agreement_streak=0,
    )


async def _disclosure_severity(conn: asyncpg.Connection, user_id: str) -> int:
    """Max severity (1-3 typically) from disclosure_log for this user.

    Returns 0 if no rows. The disclosure_log table populates from the
    fact-extraction pipeline + manual overlays; severity=3 means
    'named diagnosis / active hospitalization / self-harm history'.
    The router uses severity >= 3 as a crisis trigger to escalate to
    Opus regardless of the current message's preset.
    """
    row = await conn.fetchrow(
        "SELECT COALESCE(MAX(severity), 0)::int AS s FROM disclosure_log WHERE user_id = $1",
        user_id,
    )
    return int(row["s"]) if row else 0


async def route_for_session(
    *, channel_id: str, user_id: str, user_text: str, pg_conn: asyncpg.Connection | None
) -> RoutingDecision:
    """Pick a model for a NEW session. Fail-open to DEPTH_MODEL on any error.

    Failure modes considered:
    - asyncpg conn unavailable → disclosure=0, classifier runs on text only
    - classifier raises (defensive: shouldn't, but new patterns could fail)
      → log + use DEPTH_MODEL
    - disclosure_log table missing (fresh deploy?) → severity=0
    """
    # 1) Operator override beats everything.
    if FORCED_MODEL:
        return RoutingDecision(
            model=FORCED_MODEL,
            tier="forced",
            reason="env_AGENT_RUNNER_FORCED_MODEL",
            preset_mode="",
            preset_modifiers=[],
            disclosure_severity=0,
            forced=True,
        )

    # 2) Disclosure severity (best-effort).
    severity = 0
    if pg_conn is not None:
        try:
            severity = await _disclosure_severity(pg_conn, user_id)
        except Exception:
            log.exception("router_disclosure_query_failed", user_id=user_id)
            severity = 0

    # 3) Preset classification on current_message only.
    try:
        preset = classify_preset(user_text)
    except Exception:
        log.exception("router_preset_classify_failed", channel_id=channel_id)
        return RoutingDecision(
            model=DEPTH_MODEL,
            tier="depth",
            reason="classifier_exception",
            preset_mode="",
            preset_modifiers=[],
            disclosure_severity=severity,
            forced=False,
        )

    # 4) Route.
    choice: ModelChoice = select_model(
        preset=preset,
        flow=_neutral_flow(),
        disclosure_severity=severity,
        casual_model=CASUAL_MODEL,
        depth_model=DEPTH_MODEL,
        crisis_model=CRISIS_MODEL,
        opus_24h_count=_BUDGET.count(user_id),
        opus_24h_cap=OPUS_24H_CAP,
    )

    # 5) Record Opus usage post-decision so the cap takes effect on the next
    #    call. Only count actual crisis-tier picks (not "depth chosen because
    #    crisis cap reached" — that's not an Opus call).
    if choice.tier == "crisis" and choice.primary == CRISIS_MODEL:
        _BUDGET.record(user_id)

    return RoutingDecision(
        model=choice.primary,
        tier=str(choice.tier),
        reason=choice.reason,
        preset_mode=str(preset.mode),
        preset_modifiers=[str(m) for m in preset.modifiers],
        disclosure_severity=severity,
        forced=False,
    )


def get_opus_count(user_id: str) -> int:
    """Expose the in-memory Opus budget for diagnostics / debug endpoint."""
    return _BUDGET.count(user_id)


def _reset_budget_for_tests() -> Any:
    """Tests can swap out the singleton; production code never calls this."""
    global _BUDGET
    old = _BUDGET
    _BUDGET = OpusBudget(cap=OPUS_24H_CAP)
    return old
