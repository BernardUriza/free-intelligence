"""Flow 2: Adaptive Pressure — classify user state and pick intensity level.

Maps the user's emotional/conversational posture to an intensity level
1-5 used downstream to shape the response. Preset guards clamp the
level for safety-first modes (RESPECTFUL_SERIOUS caps at 1)."""

from __future__ import annotations

from typing import Any

import structlog

from khimeras_shared.behavior.flows.analyzers.base import FlowContext
from khimeras_shared.behavior.flows.model.patterns import (
    STATE_PATTERNS,
    STATE_TO_PRESSURE,
    WINDOW_BOOST_STATES,
    count_hits,
)
from khimeras_shared.behavior.flows.model.types import PressureAnalysis, UserState
from khimeras_shared.behavior.presets import PresetMode, PresetSelection

log = structlog.get_logger()


class PressureAnalyzer:
    name = "pressure"

    def analyze(self, ctx: FlowContext, prior: dict[str, Any]) -> PressureAnalysis:
        return self._score(ctx.current_message, ctx.recent_messages, ctx.preset)

    def log_event(self, result: PressureAnalysis) -> None:
        log.info(
            "flow_pressure",
            state=result.detected_state.value,
            state_confidence=result.state_confidence,
            pressure_level=result.pressure_level,
            reason=result.pressure_reason,
            clamped_by_preset=result.clamped_by_preset,
        )

    # -- Internals --

    def _score(
        self,
        current_message: str,
        recent_messages: list[dict],
        preset: PresetSelection,
    ) -> PressureAnalysis:
        state_scores: dict[UserState, float] = {
            state: float(count_hits(current_message, patterns)) for state, patterns in STATE_PATTERNS.items()
        }

        # Window bonus: persistent states (confused, evasive, hostile) get
        # a half-score per hit in recent non-current user messages. The
        # intuition: confusion and hostility are sticky across turns.
        user_msgs = [m["content"] for m in recent_messages[-6:] if m.get("role") == "user"]
        for state in WINDOW_BOOST_STATES:
            for msg in user_msgs[:-1] if user_msgs else []:
                state_scores[state] += count_hits(msg, STATE_PATTERNS[state]) * 0.5

        # Tie-break: playful wins over hostile when both score equally, so
        # that friendly insults ("pendejo jajaja 😂") route to playful not
        # hostile. Without this, any rude word flips the state regardless
        # of the emoji cloud around it.
        if (
            state_scores.get(UserState.PLAYFUL, 0) >= state_scores.get(UserState.HOSTILE, 0)
            and state_scores.get(UserState.PLAYFUL, 0) > 0
        ):
            state_scores[UserState.HOSTILE] = 0

        best_state = max(state_scores, key=lambda s: state_scores[s])
        best_score = state_scores[best_state]

        if best_score < 1:
            best_state = UserState.NEUTRAL
            best_score = 0

        confidence = min(best_score / 3.0, 1.0)
        pressure_level = STATE_TO_PRESSURE[best_state]
        reason = f"state={best_state.value}_score={best_score:.1f}"

        # Preset guards — these override the pattern-derived level for
        # safety (serious) or playfulness-cap (playful_roast), and one
        # escalation for arc-mode + prejudiced (max ethical force).
        clamped = False
        if preset.mode == PresetMode.RESPECTFUL_SERIOUS:
            if pressure_level > 1:
                pressure_level = 1
                clamped = True
        elif preset.mode == PresetMode.PLAYFUL_ROAST:
            if pressure_level > 3:
                pressure_level = 3
                clamped = True
        elif preset.mode == PresetMode.ARC and best_state == UserState.PREJUDICED:
            pressure_level = 5
            reason += "_arc_boost"

        return PressureAnalysis(
            detected_state=best_state,
            state_confidence=round(confidence, 2),
            pressure_level=pressure_level,
            pressure_reason=reason,
            clamped_by_preset=clamped,
        )
