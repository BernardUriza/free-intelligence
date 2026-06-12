"""Tests for the 3-tier model router (insult.core.routing)."""

from __future__ import annotations

from personas.insult.core.flows import (
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
from personas.insult.core.presets import PresetMode, PresetSelection
from personas.insult.core.routing import ModelTier, OpusBudget, select_model

CASUAL = "haiku-test"
DEPTH = "sonnet-test"
CRISIS = "opus-test"


def _flow(
    state: UserState = UserState.NEUTRAL,
    pressure_level: int = 2,
) -> FlowAnalysis:
    return FlowAnalysis(
        epistemic=EpistemicAnalysis(
            assertion_density=0.0,
            hedging_score=0.0,
            fluff_score=0.0,
            contradiction_detected=False,
            vague_claim_count=0,
            recommended_move=EpistemicMove.NONE,
            move_reason="none",
        ),
        pressure=PressureAnalysis(
            detected_state=state,
            state_confidence=0.5,
            pressure_level=pressure_level,
            pressure_reason="test",
            clamped_by_preset=False,
        ),
        expression=ExpressionAnalysis(
            selected_shape=ResponseShape.SHORT_EXCHANGE,
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


def _preset(mode: PresetMode) -> PresetSelection:
    return PresetSelection(mode=mode, modifiers=[], confidence=0.8, reason="test")


# --- Crisis path ---------------------------------------------------------


def test_crisis_routes_to_opus_when_preset_is_serious():
    choice = select_model(
        _preset(PresetMode.RESPECTFUL_SERIOUS),
        _flow(),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.CRISIS
    assert choice.primary == CRISIS
    assert choice.fallback == DEPTH
    assert choice.reason == "crisis_trigger"


def test_crisis_routes_to_opus_when_disclosure_severity_ge_3():
    # Default preset but severe disclosure → still crisis.
    choice = select_model(
        _preset(PresetMode.DEFAULT_ABRASIVE),
        _flow(),
        disclosure_severity=3,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.CRISIS
    assert choice.primary == CRISIS


def test_crisis_routes_to_opus_when_vulnerable_and_high_pressure():
    choice = select_model(
        _preset(PresetMode.RELATIONAL_PROBE),
        _flow(state=UserState.VULNERABLE, pressure_level=4),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.CRISIS


def test_vulnerable_low_pressure_does_not_trigger_opus():
    # VULNERABLE alone isn't enough — requires pressure >= 4.
    choice = select_model(
        _preset(PresetMode.RELATIONAL_PROBE),
        _flow(state=UserState.VULNERABLE, pressure_level=2),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.DEPTH  # RELATIONAL_PROBE is a depth preset


def test_crisis_downgrades_to_sonnet_when_cap_reached():
    choice = select_model(
        _preset(PresetMode.RESPECTFUL_SERIOUS),
        _flow(),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
        opus_24h_count=20,
        opus_24h_cap=20,
    )
    assert choice.tier == ModelTier.DEPTH
    assert choice.primary == DEPTH
    assert choice.reason == "opus_cap_reached"


# --- Depth path ----------------------------------------------------------


def test_depth_preset_intellectual_routes_to_sonnet():
    choice = select_model(
        _preset(PresetMode.INTELLECTUAL_PRESSURE),
        _flow(),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.DEPTH
    assert choice.primary == DEPTH
    assert choice.fallback == DEPTH


def test_depth_preset_arc_routes_to_sonnet():
    choice = select_model(
        _preset(PresetMode.ARC),
        _flow(),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.DEPTH


def test_depth_preset_relational_probe_routes_to_sonnet():
    choice = select_model(
        _preset(PresetMode.RELATIONAL_PROBE),
        _flow(),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.DEPTH


# --- Casual path ---------------------------------------------------------


def test_casual_preset_routes_to_haiku():
    choice = select_model(
        _preset(PresetMode.DEFAULT_ABRASIVE),
        _flow(),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.CASUAL
    assert choice.primary == CASUAL


def test_casual_choice_has_depth_as_fallback():
    """Critical shape: Haiku must always fall back to Sonnet, never to Haiku."""
    for mode in (PresetMode.DEFAULT_ABRASIVE, PresetMode.PLAYFUL_ROAST, PresetMode.META_DEFLECTION):
        choice = select_model(
            _preset(mode),
            _flow(),
            disclosure_severity=0,
            casual_model=CASUAL,
            depth_model=DEPTH,
            crisis_model=CRISIS,
        )
        assert choice.tier == ModelTier.CASUAL, mode
        assert choice.primary == CASUAL, mode
        assert choice.fallback == DEPTH, mode


def test_meta_deflection_routes_to_haiku():
    choice = select_model(
        _preset(PresetMode.META_DEFLECTION),
        _flow(),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.CASUAL


# --- Safety defaults -----------------------------------------------------


def test_crisis_beats_casual_preset():
    # RESPECTFUL_SERIOUS always wins even if other signals would route casual.
    choice = select_model(
        _preset(PresetMode.RESPECTFUL_SERIOUS),
        _flow(),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
    )
    assert choice.tier == ModelTier.CRISIS


# --- OpusBudget ----------------------------------------------------------


def test_opus_budget_starts_empty():
    budget = OpusBudget()
    assert budget.count("u1") == 0


def test_opus_budget_records_and_counts():
    budget = OpusBudget()
    assert budget.record("u1", now=100.0) == 1
    assert budget.record("u1", now=101.0) == 2
    assert budget.count("u1", now=102.0) == 2


def test_opus_budget_is_per_user():
    budget = OpusBudget()
    budget.record("u1", now=100.0)
    budget.record("u1", now=101.0)
    assert budget.count("u1", now=102.0) == 2
    assert budget.count("u2", now=102.0) == 0


def test_opus_budget_window_expires_old_entries():
    budget = OpusBudget(window_seconds=10)
    budget.record("u1", now=100.0)
    budget.record("u1", now=105.0)
    # After 11s the first event is outside the window.
    assert budget.count("u1", now=111.0) == 1


def test_opus_budget_integrates_with_select_model():
    """End-to-end: a fresh budget permits crisis, a capped one downgrades."""
    budget = OpusBudget(cap=2)
    for _ in range(2):
        budget.record("u1", now=1000.0)
    choice = select_model(
        _preset(PresetMode.RESPECTFUL_SERIOUS),
        _flow(),
        disclosure_severity=0,
        casual_model=CASUAL,
        depth_model=DEPTH,
        crisis_model=CRISIS,
        opus_24h_count=budget.count("u1", now=1000.0),
        opus_24h_cap=budget.cap,
    )
    assert choice.tier == ModelTier.DEPTH
    assert choice.reason == "opus_cap_reached"
