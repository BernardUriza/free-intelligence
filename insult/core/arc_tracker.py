"""Emotional arc tracking across conversation turns.

Tracks CRISIS -> RECOVERY -> STABILITY transitions per user per channel.
Replaces per-message-only analysis with cross-turn awareness so the bot
can modulate tone across an entire emotional episode rather than reacting
to each message in isolation.

All detection is rule-based (zero LLM cost).  This module is pure
functions + dataclasses — no DB access.  Persistence is handled by the
caller (chat.py via memory.py) using the serialization helpers at the
bottom of this file.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

import structlog

log = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════════════════
# Enums & data structures
# ═══════════════════════════════════════════════════════════════════════════


class EmotionalPhase(StrEnum):
    STABILITY = "stability"
    CRISIS = "crisis"
    RECOVERY = "recovery"


@dataclass
class ArcState:
    """Snapshot of a user's emotional arc in a channel.

    Fields are designed for cheap serialization to/from a dict so the
    caller can persist them in SQLite without this module knowing about DB.
    """

    phase: EmotionalPhase = EmotionalPhase.STABILITY
    phase_since: float = 0.0  # timestamp when phase started
    crisis_depth: int = 0  # 1=mild, 2=moderate, 3=severe
    recovery_signals: int = 0  # count of positive signals since crisis
    turns_in_phase: int = 0  # messages processed in current phase


# ═══════════════════════════════════════════════════════════════════════════
# User-state sets used by transition logic
# ═══════════════════════════════════════════════════════════════════════════

_POSITIVE_USER_STATES: frozenset[str] = frozenset({"sincere", "playful", "neutral"})

# ═══════════════════════════════════════════════════════════════════════════
# Core transition function
# ═══════════════════════════════════════════════════════════════════════════


def update_arc(
    current: ArcState,
    disclosure_severity: int,  # from disclosure.py (0-5)
    user_state: str,  # from flows.py UserState value
    preset_mode: str,  # from presets.py PresetMode value
) -> ArcState:
    """Compute next arc state based on current state + new signals.

    Returns a NEW ArcState (immutable update pattern).  The caller is
    responsible for persisting the returned state.

    Transition rules
    ----------------
    * STABILITY -> CRISIS when disclosure_severity >= 3 **or**
      preset_mode == "respectful_serious".
    * CRISIS -> RECOVERY after 3 consecutive positive turns with no
      new crisis signals.
    * RECOVERY -> STABILITY after 5 clean turns **and**
      recovery_signals >= 5.
    * Any phase -> CRISIS when disclosure_severity >= 4 (acute crisis
      always overrides).
    """

    now = time.time()

    # --- acute crisis override (any phase) ---
    if disclosure_severity >= 4:
        depth = min(3, disclosure_severity - 1)
        if current.phase != EmotionalPhase.CRISIS or depth > current.crisis_depth:
            log.info(
                "arc_acute_crisis",
                previous_phase=current.phase,
                depth=depth,
                severity=disclosure_severity,
            )
        return ArcState(
            phase=EmotionalPhase.CRISIS,
            phase_since=now,
            crisis_depth=depth,
            recovery_signals=0,
            turns_in_phase=1,
        )

    # --- phase-specific logic ---
    if current.phase == EmotionalPhase.STABILITY:
        return _update_stability(current, disclosure_severity, preset_mode, now)
    if current.phase == EmotionalPhase.CRISIS:
        return _update_crisis(current, disclosure_severity, user_state, now)
    # RECOVERY
    return _update_recovery(current, disclosure_severity, user_state, now)


# ───────────────────────────────────────────────────────────────────────────
# Phase-specific helpers
# ───────────────────────────────────────────────────────────────────────────


def _update_stability(
    current: ArcState,
    disclosure_severity: int,
    preset_mode: str,
    now: float,
) -> ArcState:
    """STABILITY -> CRISIS check."""

    crisis_triggered = disclosure_severity >= 3
    # preset_mode == respectful_serious can be forced by the chronic
    # vulnerability overlay (vulnerability.py) even when the user disclosed
    # nothing in this turn. Require some active signal (severity >= 1) to
    # avoid a permanent CRISIS yo-yo for chronically vulnerable users.
    preset_triggered = preset_mode == "respectful_serious" and disclosure_severity >= 1

    if crisis_triggered or preset_triggered:
        depth = min(3, max(disclosure_severity - 1, 1))
        log.info(
            "arc_enter_crisis",
            trigger="disclosure" if crisis_triggered else "preset",
            depth=depth,
            severity=disclosure_severity,
        )
        return ArcState(
            phase=EmotionalPhase.CRISIS,
            phase_since=now,
            crisis_depth=depth,
            recovery_signals=0,
            turns_in_phase=1,
        )

    # Stay in stability
    return ArcState(
        phase=EmotionalPhase.STABILITY,
        phase_since=current.phase_since or now,
        crisis_depth=0,
        recovery_signals=0,
        turns_in_phase=current.turns_in_phase + 1,
    )


def _update_crisis(
    current: ArcState,
    disclosure_severity: int,
    user_state: str,
    now: float,
) -> ArcState:
    """CRISIS -> RECOVERY check (needs 3 consecutive positive turns)."""

    # New crisis signal resets recovery counter
    if disclosure_severity >= 3:
        new_depth = min(3, max(current.crisis_depth, disclosure_severity - 1))
        return ArcState(
            phase=EmotionalPhase.CRISIS,
            phase_since=current.phase_since,
            crisis_depth=new_depth,
            recovery_signals=0,
            turns_in_phase=current.turns_in_phase + 1,
        )

    # Positive signal
    new_recovery = current.recovery_signals
    if user_state in _POSITIVE_USER_STATES:
        new_recovery += 1

    # Transition to RECOVERY after 3+ positive signals
    if new_recovery >= 3:
        log.info(
            "arc_enter_recovery",
            crisis_depth=current.crisis_depth,
            recovery_signals=new_recovery,
        )
        return ArcState(
            phase=EmotionalPhase.RECOVERY,
            phase_since=now,
            crisis_depth=current.crisis_depth,
            recovery_signals=new_recovery,
            turns_in_phase=1,
        )

    # Stay in crisis
    return ArcState(
        phase=EmotionalPhase.CRISIS,
        phase_since=current.phase_since,
        crisis_depth=current.crisis_depth,
        recovery_signals=new_recovery,
        turns_in_phase=current.turns_in_phase + 1,
    )


def _update_recovery(
    current: ArcState,
    disclosure_severity: int,
    user_state: str,
    now: float,
) -> ArcState:
    """RECOVERY -> STABILITY check (5+ clean turns, 5+ recovery signals)."""

    # Relapse into crisis
    if disclosure_severity >= 3:
        log.info(
            "arc_relapse_to_crisis",
            previous_recovery_signals=current.recovery_signals,
            severity=disclosure_severity,
        )
        return ArcState(
            phase=EmotionalPhase.CRISIS,
            phase_since=now,
            crisis_depth=min(3, disclosure_severity - 1),
            recovery_signals=0,
            turns_in_phase=1,
        )

    new_recovery = current.recovery_signals
    if user_state in _POSITIVE_USER_STATES:
        new_recovery += 1

    new_turns = current.turns_in_phase + 1

    # Full recovery
    if new_turns >= 5 and new_recovery >= 5:
        log.info(
            "arc_restored_stability",
            turns_in_recovery=new_turns,
            recovery_signals=new_recovery,
        )
        return ArcState(
            phase=EmotionalPhase.STABILITY,
            phase_since=now,
            crisis_depth=0,
            recovery_signals=0,
            turns_in_phase=1,
        )

    # Stay in recovery
    return ArcState(
        phase=EmotionalPhase.RECOVERY,
        phase_since=current.phase_since,
        crisis_depth=current.crisis_depth,
        recovery_signals=new_recovery,
        turns_in_phase=new_turns,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Prompt guidance
# ═══════════════════════════════════════════════════════════════════════════


def build_arc_prompt(arc: ArcState) -> str:
    """Generate system prompt guidance based on emotional arc phase.

    Returns an empty string for STABILITY (no special guidance needed).
    """

    if arc.phase == EmotionalPhase.CRISIS:
        return (
            f"The user is in emotional crisis (depth {arc.crisis_depth}). "
            "Prioritize presence over analysis. Short responses. No jokes. "
            "No challenges. Ask what they need, not what they think."
        )

    if arc.phase == EmotionalPhase.RECOVERY:
        return (
            f"The user is recovering from crisis ({arc.recovery_signals} "
            "positive signals). You can gently re-engage but don't push. "
            "Acknowledge progress without cheerleading. Stay observant."
        )

    return ""


# ═══════════════════════════════════════════════════════════════════════════
# Serialization helpers
# ═══════════════════════════════════════════════════════════════════════════


def arc_to_dict(arc: ArcState) -> dict:
    """Serialize an ArcState for DB storage (JSON-safe dict)."""

    return {
        "phase": str(arc.phase),
        "phase_since": arc.phase_since,
        "crisis_depth": arc.crisis_depth,
        "recovery_signals": arc.recovery_signals,
        "turns_in_phase": arc.turns_in_phase,
    }


def arc_from_dict(data: dict) -> ArcState:
    """Deserialize an ArcState from a DB row / JSON dict.

    Gracefully handles missing keys by falling back to defaults.
    """

    return ArcState(
        phase=EmotionalPhase(data.get("phase", "stability")),
        phase_since=float(data.get("phase_since", 0.0)),
        crisis_depth=int(data.get("crisis_depth", 0)),
        recovery_signals=int(data.get("recovery_signals", 0)),
        turns_in_phase=int(data.get("turns_in_phase", 0)),
    )
