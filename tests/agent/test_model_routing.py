"""Unit coverage for the runner-side 3-tier model router."""

from __future__ import annotations

from types import SimpleNamespace

from khimeras_shared.behavior.contracts.flows import (
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
from khimeras_shared.behavior.contracts.presets import PresetMode, PresetSelection
from persona_runner.routing.model_routing import ModelTier, OpusBudget, select_model

CASUAL = "haiku"
DEPTH = "sonnet"
CRISIS = "opus"


def _preset(mode: PresetMode) -> PresetSelection:
    return PresetSelection(mode=mode, confidence=0.9, reason="test")


def _flow(
    *,
    state: UserState = UserState.NEUTRAL,
    pressure_level: int = 0,
) -> FlowAnalysis:
    return FlowAnalysis(
        epistemic=EpistemicAnalysis(
            assertion_density=0.0,
            hedging_score=0.0,
            fluff_score=0.0,
            contradiction_detected=False,
            vague_claim_count=0,
            recommended_move=EpistemicMove.NONE,
            move_reason="test",
        ),
        pressure=PressureAnalysis(
            detected_state=state,
            state_confidence=0.8,
            pressure_level=pressure_level,
            pressure_reason="test",
            clamped_by_preset=False,
        ),
        expression=ExpressionAnalysis(
            selected_shape=ResponseShape.LAYERED,
            selected_flavor=StyleFlavor.DRY,
            shape_reason="test",
            flavor_reason="test",
        ),
        awareness=AwarenessAnalysis(
            detected_pattern=ConversationPattern.NONE,
            pattern_confidence=0.0,
            meta_commentary=None,
            delayed_question=None,
            turns_in_pattern=0,
        ),
    )


def _select(
    *,
    preset: PresetSelection | SimpleNamespace,
    flow: FlowAnalysis | None = None,
    disclosure_severity: int = 0,
    opus_24h_count: int = 0,
    opus_24h_cap: int = 20,
):
    return select_model(
        preset=preset,
        flow=flow or _flow(),
        disclosure_severity=disclosure_severity,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
        opus_24h_count=opus_24h_count,
        opus_24h_cap=opus_24h_cap,
    )


def test_select_model_crisis_branch_for_respectful_serious_preset():
    """RESPECTFUL_SERIOUS always escalates to the crisis tier."""
    choice = _select(preset=_preset(PresetMode.RESPECTFUL_SERIOUS))

    assert choice.primary == CRISIS
    assert choice.fallback == DEPTH
    assert choice.tier == ModelTier.CRISIS
    assert choice.reason == "crisis_trigger"


def test_select_model_crisis_branch_for_severe_disclosure():
    """Disclosure severity 3 or higher escalates to the crisis tier."""
    choice = _select(
        preset=_preset(PresetMode.DEFAULT_ABRASIVE),
        disclosure_severity=3,
    )

    assert choice.primary == CRISIS
    assert choice.fallback == DEPTH
    assert choice.tier == ModelTier.CRISIS
    assert choice.reason == "crisis_trigger"


def test_select_model_crisis_branch_for_vulnerable_hard_pressure():
    """Vulnerable users at pressure level 4 or higher escalate to crisis."""
    choice = _select(
        preset=_preset(PresetMode.PLAYFUL_ROAST),
        flow=_flow(state=UserState.VULNERABLE, pressure_level=4),
    )

    assert choice.primary == CRISIS
    assert choice.fallback == DEPTH
    assert choice.tier == ModelTier.CRISIS
    assert choice.reason == "crisis_trigger"


def test_select_model_depth_branch_when_opus_cap_reached():
    """A crisis trigger falls back to depth when the Opus cap is reached."""
    choice = _select(
        preset=_preset(PresetMode.RESPECTFUL_SERIOUS),
        opus_24h_count=20,
        opus_24h_cap=20,
    )

    assert choice.primary == DEPTH
    assert choice.fallback == DEPTH
    assert choice.tier == ModelTier.DEPTH
    assert choice.reason == "opus_cap_reached"


def test_select_model_depth_branch_for_depth_preset():
    """Depth presets route to the depth tier without crisis escalation."""
    choice = _select(preset=_preset(PresetMode.INTELLECTUAL_PRESSURE))

    assert choice.primary == DEPTH
    assert choice.fallback == DEPTH
    assert choice.tier == ModelTier.DEPTH
    assert choice.reason == "depth_preset"


def test_select_model_casual_branch_for_casual_preset():
    """Casual presets route to the casual tier with depth fallback."""
    choice = _select(preset=_preset(PresetMode.DEFAULT_ABRASIVE))

    assert choice.primary == CASUAL
    assert choice.fallback == DEPTH
    assert choice.tier == ModelTier.CASUAL
    assert choice.reason == "casual_preset"


def test_select_model_depth_branch_for_unknown_future_preset():
    """Unknown future presets default to depth instead of casual."""
    choice = _select(preset=SimpleNamespace(mode="future_mode"))

    assert choice.primary == DEPTH
    assert choice.fallback == DEPTH
    assert choice.tier == ModelTier.DEPTH
    assert choice.reason == "unknown_preset_default_to_depth"


def test_select_model_resists_escalation_below_disclosure_threshold():
    """Resistance: disclosure severity 2 does not escalate to crisis."""
    choice = _select(
        preset=_preset(PresetMode.DEFAULT_ABRASIVE),
        disclosure_severity=2,
    )

    assert choice.primary == CASUAL
    assert choice.tier == ModelTier.CASUAL
    assert choice.reason == "casual_preset"


def test_select_model_resists_escalation_below_vulnerable_pressure_threshold():
    """Resistance: vulnerable pressure level 3 does not escalate to crisis."""
    choice = _select(
        preset=_preset(PresetMode.PLAYFUL_ROAST),
        flow=_flow(state=UserState.VULNERABLE, pressure_level=3),
    )

    assert choice.primary == CASUAL
    assert choice.tier == ModelTier.CASUAL
    assert choice.reason == "casual_preset"


def test_select_model_resists_escalation_for_hard_pressure_without_vulnerability():
    """Resistance: pressure level 4 alone does not escalate to crisis."""
    choice = _select(
        preset=_preset(PresetMode.META_DEFLECTION),
        flow=_flow(state=UserState.SINCERE, pressure_level=4),
    )

    assert choice.primary == CASUAL
    assert choice.tier == ModelTier.CASUAL
    assert choice.reason == "casual_preset"


def test_opus_budget_allows_below_cap():
    """A user below cap has remaining budget in the injected time window."""
    budget = OpusBudget(cap=3, window_seconds=10)

    assert budget.record("u1", now=100.0) == 1
    assert budget.count("u1", now=101.0) == 1
    assert budget.count("u1", now=101.0) < budget.cap


def test_opus_budget_blocks_at_cap():
    """A user at cap has no remaining budget in the injected time window."""
    budget = OpusBudget(cap=2, window_seconds=10)

    assert budget.record("u1", now=100.0) == 1
    assert budget.record("u1", now=101.0) == 2
    assert budget.count("u1", now=102.0) == budget.cap


def test_opus_budget_evicts_events_outside_window_and_frees_capacity():
    """Resistance: expired events are evicted and release budget capacity."""
    budget = OpusBudget(cap=2, window_seconds=10)

    budget.record("u1", now=100.0)
    budget.record("u1", now=105.0)

    assert budget.count("u1", now=110.0) == 2
    assert budget.count("u1", now=110.1) == 1
    assert budget.record("u1", now=110.1) == 2


def test_opus_budget_counts_are_per_user():
    """Resistance: different user IDs do not share Opus budget events."""
    budget = OpusBudget(cap=2, window_seconds=10)

    budget.record("u1", now=100.0)
    budget.record("u1", now=101.0)
    budget.record("u2", now=102.0)

    assert budget.count("u1", now=103.0) == 2
    assert budget.count("u2", now=103.0) == 1
    assert budget.count("u2", now=103.0) < budget.cap
