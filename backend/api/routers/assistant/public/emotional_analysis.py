"""Emotional analysis for assistant conversations.

Provides emotional state detection using Ollama Llama 3.1 8B with heuristic fallback.
"""

from __future__ import annotations

import json
from typing import Any

from backend.services.assistant.services.monitor_client import get_ollama_chat
from backend.utils.common.logging.logger import get_logger

from .assistant_schemas import EmotionalAnalysis

logger = get_logger(__name__)


def _heuristic_analysis(message: str, metrics: dict[str, Any]) -> EmotionalAnalysis:
    """Fallback heuristic analysis when Ollama unavailable.

    Args:
        message: User's message text
        metrics: Behavior metrics dict

    Returns:
        EmotionalAnalysis based on keyword matching
    """
    # Check for urgency indicators
    urgency_words = ["urgente", "emergencia", "rápido", "inmediato", "ahora"]
    has_urgency = any(word in message.lower() for word in urgency_words)

    # Check for frustration indicators
    frustration_words = ["problema", "no funciona", "error", "mal", "terrible"]
    has_frustration = any(word in message.lower() for word in frustration_words)

    # Check for anxiety indicators from behavior
    rapid_clicks = metrics.get("rapid_clicks", 0)
    repeated_messages = metrics.get("repeated_messages", 0)
    has_anxiety = rapid_clicks > 3 or repeated_messages > 2

    # Determine state based on heuristics
    if has_urgency:
        state = "urgent"
        confidence = 0.75
        suggested_tone = "calm_supportive"
    elif has_frustration:
        state = "frustrated"
        confidence = 0.70
        suggested_tone = "empathetic"
    elif has_anxiety:
        state = "anxious"
        confidence = 0.65
        suggested_tone = "reassuring"
    else:
        state = "neutral"
        confidence = 0.60
        suggested_tone = "professional"

    reason = f"Heuristic: urgency={has_urgency}, frustration={has_frustration}, anxiety={has_anxiety}"

    return EmotionalAnalysis(
        state=state, confidence=confidence, suggested_tone=suggested_tone, reason=reason
    )


async def analyze_emotional_state(
    message: str,
    metrics: dict[str, Any],
    llm_client: Any = None,  # Deprecated, using Ollama via monitor_client
) -> EmotionalAnalysis | None:
    """Analyze emotional state from message and behavior metrics.

    Uses Ollama Llama 3.1 8B for nuanced medical-context analysis.
    Falls back to heuristics if Ollama unavailable.

    Args:
        message: User's message text
        metrics: Behavior metrics (rapid_clicks, repeated_messages, etc.)
        llm_client: Deprecated (ignored, using Ollama)

    Returns:
        EmotionalAnalysis or None if analysis fails completely
    """
    try:
        # Build medical-context prompt for Llama 3.1 8B
        system_prompt = """You are an emotional analysis AI for medical conversations.
Analyze the patient's message and behavior metrics to determine their emotional state.

Output ONLY valid JSON with this structure:
{
  "state": "neutral|anxious|calm|frustrated|urgent",
  "confidence": 0.0-1.0,
  "suggested_tone": "professional|reassuring|empathetic|calm_supportive",
  "reason": "brief explanation (1-2 sentences)"
}

Guidelines:
- "neutral": Normal conversation, no emotional signals
- "anxious": Worry, concern, uncertainty (rapid clicks, repeated questions)
- "calm": Relaxed, confident tone
- "frustrated": Impatience, complaints, errors mentioned
- "urgent": Emergency language, immediate need

Be concise and precise. Focus on medical context (symptoms, appointments, concerns)."""

        user_prompt = f"""Message: "{message}"

Behavior metrics:
- Rapid clicks: {metrics.get('rapid_clicks', 0)}
- Repeated messages: {metrics.get('repeated_messages', 0)}
- Idle time: {metrics.get('idle_time_seconds', 0)}s
- Recent errors: {metrics.get('recent_errors', 0)}

Analyze emotional state:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Call Ollama via monitor (timeout: 10s for emotional analysis)
        response_text = await get_ollama_chat(messages, model="llama3.1:8b", timeout=10.0)

        # Parse JSON response
        response_json = json.loads(response_text)

        analysis = EmotionalAnalysis(
            state=response_json["state"],
            confidence=float(response_json["confidence"]),
            suggested_tone=response_json["suggested_tone"],
            reason=response_json["reason"],
        )

        logger.info(
            "EMOTIONAL_ANALYSIS_COMPLETED",
            state=analysis.state,
            confidence=analysis.confidence,
            method="ollama_llama3.1_8b",
        )

        return analysis

    except (ConnectionError, TimeoutError, json.JSONDecodeError) as e:
        # Ollama unavailable or response malformed → fallback to heuristic
        logger.warning(
            "EMOTIONAL_ANALYSIS_OLLAMA_FAILED",
            error=str(e),
            error_type=type(e).__name__,
            fallback="heuristic",
        )

        analysis = _heuristic_analysis(message, metrics)

        logger.info(
            "EMOTIONAL_ANALYSIS_COMPLETED",
            state=analysis.state,
            confidence=analysis.confidence,
            method="heuristic_fallback",
        )

        return analysis

    except Exception as e:
        # Unexpected error → return None (caller handles gracefully)
        logger.error("EMOTIONAL_ANALYSIS_FAILED", error=str(e), error_type=type(e).__name__)
        return None
