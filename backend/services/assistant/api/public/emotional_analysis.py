"""Emotional analysis for assistant conversations.

Provides emotional state detection using heuristic analysis.
"""

from __future__ import annotations

from typing import Any

from backend.utils.common.logging.logger import get_logger

from .assistant_schemas import EmotionalAnalysis

logger = get_logger(__name__)


async def analyze_emotional_state(
    message: str,
    metrics: dict[str, Any],
    llm_client: Any = None,  # Not used for now
) -> EmotionalAnalysis | None:
    """Analyze emotional state from message and behavior metrics.

    Uses heuristic analysis for now.
    Returns None if analysis fails.
    """
    try:
        # Simple heuristic-based analysis for now
        # TODO: Implement proper LLM-based emotional analysis

        # Check for urgency indicators
        urgency_words = ["urgente", "emergencia", "rápido", "inmediato", "ahora"]
        has_urgency = any(word in message.lower() for word in urgency_words)

        # Check for frustration indicators
        frustration_words = ["problema", "no funciona", "error", "mal", "terrible"]
        has_frustration = any(word in message.lower() for word in frustration_words)

        # Determine state based on heuristics
        if has_urgency:
            state = "urgent"
            confidence = 0.8
            suggested_tone = "calm_supportive"
        elif has_frustration:
            state = "frustrated"
            confidence = 0.7
            suggested_tone = "empathetic"
        else:
            state = "neutral"
            confidence = 0.6
            suggested_tone = "professional"

        reason = f"Heuristic analysis: urgency={has_urgency}, frustration={has_frustration}"

        logger.info(
            "EMOTIONAL_ANALYSIS_COMPLETED", state=state, confidence=confidence, method="heuristic"
        )

        return EmotionalAnalysis(
            state=state, confidence=confidence, suggested_tone=suggested_tone, reason=reason
        )

    except Exception as e:
        logger.error("EMOTIONAL_ANALYSIS_FAILED", error=str(e))
        return None
