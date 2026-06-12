"""Tests for insult.core.arc_tracker — emotional arc tracking."""

from __future__ import annotations

from personas.insult.core.arc_tracker import (
    ArcState,
    EmotionalPhase,
    arc_from_dict,
    arc_to_dict,
    build_arc_prompt,
    update_arc,
)

# ═══════════════════════════════════════════════════════════════════════════
# update_arc transitions
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateArc:
    """Phase transition logic."""

    def test_default_state_is_stability(self):
        state = ArcState()
        assert state.phase == EmotionalPhase.STABILITY
        assert state.crisis_depth == 0
        assert state.recovery_signals == 0
        assert state.turns_in_phase == 0

    def test_stability_to_crisis_on_high_disclosure(self):
        state = ArcState()
        result = update_arc(state, disclosure_severity=3, user_state="vulnerable", preset_mode="default_abrasive")
        assert result.phase == EmotionalPhase.CRISIS
        assert result.crisis_depth >= 1
        assert result.turns_in_phase == 1

    def test_stability_to_crisis_on_serious_preset_with_disclosure(self):
        # respectful_serious + disclosure>=1 → CRISIS (real crisis pattern)
        state = ArcState()
        result = update_arc(state, disclosure_severity=1, user_state="neutral", preset_mode="respectful_serious")
        assert result.phase == EmotionalPhase.CRISIS
        assert result.crisis_depth >= 1

    def test_stability_stays_when_serious_preset_forced_by_overlay(self):
        # vulnerability_overlay forces respectful_serious chronically; without
        # active disclosure this MUST NOT push the user into CRISIS.
        state = ArcState()
        result = update_arc(state, disclosure_severity=0, user_state="neutral", preset_mode="respectful_serious")
        assert result.phase == EmotionalPhase.STABILITY

    def test_crisis_stays_in_crisis_without_recovery_signals(self):
        state = ArcState(phase=EmotionalPhase.CRISIS, crisis_depth=2, turns_in_phase=1)
        # Send non-positive user states (not in sincere/playful/neutral)
        result = update_arc(state, disclosure_severity=0, user_state="aggressive", preset_mode="default_abrasive")
        assert result.phase == EmotionalPhase.CRISIS
        assert result.recovery_signals == 0

    def test_crisis_to_recovery_after_3_positive_turns(self):
        state = ArcState(phase=EmotionalPhase.CRISIS, crisis_depth=2, recovery_signals=0, turns_in_phase=1)
        # 3 positive turns
        for _i in range(3):
            state = update_arc(state, disclosure_severity=0, user_state="sincere", preset_mode="default_abrasive")
        assert state.phase == EmotionalPhase.RECOVERY

    def test_recovery_to_stability_after_5_clean_turns(self):
        # Start in recovery with 3 recovery signals already (from crisis exit)
        state = ArcState(
            phase=EmotionalPhase.RECOVERY,
            crisis_depth=1,
            recovery_signals=3,
            turns_in_phase=1,
        )
        # Need turns_in_phase >= 5 and recovery_signals >= 5
        # Already have 3 signals, 1 turn.  Send 4 more positive turns.
        for _ in range(4):
            state = update_arc(state, disclosure_severity=0, user_state="playful", preset_mode="default_abrasive")
        assert state.phase == EmotionalPhase.STABILITY
        assert state.crisis_depth == 0
        assert state.recovery_signals == 0

    def test_acute_crisis_overrides_recovery(self):
        state = ArcState(phase=EmotionalPhase.RECOVERY, crisis_depth=1, recovery_signals=4, turns_in_phase=3)
        result = update_arc(state, disclosure_severity=4, user_state="vulnerable", preset_mode="default_abrasive")
        assert result.phase == EmotionalPhase.CRISIS
        assert result.crisis_depth == 3
        assert result.recovery_signals == 0

    def test_crisis_depth_scales_with_severity(self):
        state = ArcState()
        r3 = update_arc(state, disclosure_severity=3, user_state="vulnerable", preset_mode="default_abrasive")
        r4 = update_arc(state, disclosure_severity=4, user_state="vulnerable", preset_mode="default_abrasive")
        r5 = update_arc(state, disclosure_severity=5, user_state="vulnerable", preset_mode="default_abrasive")
        assert r3.crisis_depth == 2
        assert r4.crisis_depth == 3
        assert r5.crisis_depth == 3  # capped at 3

    def test_recovery_signals_increment(self):
        state = ArcState(phase=EmotionalPhase.CRISIS, crisis_depth=1, recovery_signals=0, turns_in_phase=1)
        result = update_arc(state, disclosure_severity=0, user_state="sincere", preset_mode="default_abrasive")
        assert result.recovery_signals == 1
        result = update_arc(result, disclosure_severity=0, user_state="playful", preset_mode="default_abrasive")
        assert result.recovery_signals == 2

    def test_turns_in_phase_increment(self):
        state = ArcState(phase=EmotionalPhase.STABILITY, turns_in_phase=5)
        result = update_arc(state, disclosure_severity=0, user_state="neutral", preset_mode="default_abrasive")
        assert result.turns_in_phase == 6


# ═══════════════════════════════════════════════════════════════════════════
# build_arc_prompt
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildArcPrompt:
    """Prompt guidance generation."""

    def test_build_arc_prompt_crisis(self):
        arc = ArcState(phase=EmotionalPhase.CRISIS, crisis_depth=2)
        prompt = build_arc_prompt(arc)
        assert prompt != ""
        assert "crisis" in prompt.lower()
        assert "depth 2" in prompt

    def test_build_arc_prompt_stability(self):
        arc = ArcState(phase=EmotionalPhase.STABILITY)
        assert build_arc_prompt(arc) == ""

    def test_build_arc_prompt_recovery(self):
        arc = ArcState(phase=EmotionalPhase.RECOVERY, recovery_signals=4)
        prompt = build_arc_prompt(arc)
        assert prompt != ""
        assert "recovering" in prompt.lower()
        assert "4" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# Serialization
# ═══════════════════════════════════════════════════════════════════════════


class TestSerialization:
    """Round-trip serialization."""

    def test_serialization_roundtrip(self):
        original = ArcState(
            phase=EmotionalPhase.RECOVERY,
            phase_since=1700000000.0,
            crisis_depth=2,
            recovery_signals=4,
            turns_in_phase=7,
        )
        data = arc_to_dict(original)
        restored = arc_from_dict(data)
        assert restored.phase == original.phase
        assert restored.phase_since == original.phase_since
        assert restored.crisis_depth == original.crisis_depth
        assert restored.recovery_signals == original.recovery_signals
        assert restored.turns_in_phase == original.turns_in_phase
