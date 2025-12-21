"""
Emotional Analysis Module - AURITY

Hybrid emotional state detection using LLM + heuristics.

Architecture:
    1. LLM Analysis: Uses behavior metrics + message text for accurate detection
    2. Heuristic Fallback: Keyword + punctuation + metric scoring when LLM fails

Author: Bernard Uriza Orozco
Created: 2025-11-26
"""

from __future__ import annotations

import json
import re

from fi_common.logging.logger import get_logger
from backend.observability.logging import CTX_REQUEST_ID

from .assistant_schemas import BehaviorMetrics, EmotionalAnalysis

logger = get_logger(__name__)


# ============================================================================
# LLM-Based Analysis
# ============================================================================


async def analyze_emotional_state(
    message: str,
    metrics: BehaviorMetrics | None,
    llm_client,
) -> EmotionalAnalysis | None:
    """Analyze user's emotional state using LLM with behavior metrics context.

    This uses a lightweight LLM call to analyze both:
    1. The text content (sentiment, keywords, punctuation)
    2. Behavior metrics (clicks, errors, idle time)

    Args:
        message: User's message text
        metrics: Behavior metrics from frontend
        llm_client: LLM client for analysis

    Returns:
        EmotionalAnalysis or None if metrics not provided
    """
    if metrics is None:
        return None

    # Build analysis prompt
    analysis_prompt = f"""Analyze the user's emotional state based on their message and behavior.

MESSAGE: "{message}"

BEHAVIOR METRICS:
- Rapid clicks (frustration signal): {metrics.rapid_clicks}
- Repeated messages: {metrics.repeated_messages}
- Idle time: {metrics.idle_time_seconds} seconds
- Back navigations: {metrics.back_navigations}
- Recent errors: {metrics.recent_errors}
- Time on current phase: {metrics.phase_time_seconds} seconds

Based on BOTH the message content AND behavior metrics, determine:
1. Emotional state: "frustrated", "successful", "hesitant", or "neutral"
2. Confidence: 0.0 to 1.0
3. Suggested tone for response: "empathetic" (for frustrated), "celebratory" (for successful), "guiding" (for hesitant), or "neutral"
4. Brief reason for your assessment

Respond in JSON format ONLY:
{{"state": "...", "confidence": 0.X, "suggested_tone": "...", "reason": "..."}}"""

    try:
        request_id = CTX_REQUEST_ID.get() or None
        result = await llm_client.chat(
            persona="general_assistant",
            message=analysis_prompt,
            context={"task": "emotional_analysis"},
            session_id=None,
            doctor_id=None,
            use_memory=False,
            request_id=request_id,
            caller="public",
        )

        response_text = result.get("response", "{}")
        # Extract JSON from response (in case there's extra text)
        json_match = re.search(r"\{[^{}]+\}", response_text)
        if json_match:
            analysis_data = json.loads(json_match.group())
            return EmotionalAnalysis(
                state=analysis_data.get("state", "neutral"),
                confidence=float(analysis_data.get("confidence", 0.7)),
                suggested_tone=analysis_data.get("suggested_tone", "neutral"),
                reason=analysis_data.get("reason", ""),
            )
    except Exception as e:
        logger.warning(
            "EMOTIONAL_ANALYSIS_LLM_FAILED",
            error=str(e),
            error_type=type(e).__name__,
        )

    # Fallback to heuristics-based analysis
    return heuristic_emotional_analysis(message, metrics)


# ============================================================================
# Heuristic-Based Analysis (Fallback)
# ============================================================================


# Keyword dictionaries for heuristic analysis
FRUSTRATION_KEYWORDS = [
    "no entiendo",
    "confuso",
    "difícil",
    "no funciona",
    "error",
    "ayuda",
    "frustrado",
    "imposible",
    "problema",
    "falla",
]

SUCCESS_KEYWORDS = [
    "genial",
    "perfecto",
    "gracias",
    "entendí",
    "funciona",
    "excelente",
    "listo",
    "bien",
    "correcto",
    "sí",
]


def heuristic_emotional_analysis(
    message: str,
    metrics: BehaviorMetrics,
) -> EmotionalAnalysis:
    """Fallback heuristic analysis when LLM fails.

    Uses three signal types:
    1. Text signals: Keywords and punctuation
    2. Behavior signals: Clicks, errors, navigation
    3. Time signals: Idle time, phase duration

    Args:
        message: User's message text
        metrics: Behavior metrics from frontend

    Returns:
        EmotionalAnalysis with heuristic-based detection
    """
    message_lower = message.lower()
    reasons: list[str] = []

    # Calculate scores for each state
    frustration_score = _calculate_frustration_score(message_lower, message, metrics, reasons)
    success_score = _calculate_success_score(message_lower)
    hesitation_score = _calculate_hesitation_score(metrics, reasons)

    # Determine state based on highest score
    if frustration_score >= 0.5:
        return EmotionalAnalysis(
            state="frustrated",
            confidence=min(frustration_score, 1.0),
            suggested_tone="empathetic",
            reason=", ".join(reasons) or "Frustration signals detected",
        )
    elif success_score >= 0.5:
        return EmotionalAnalysis(
            state="successful",
            confidence=min(success_score, 1.0),
            suggested_tone="celebratory",
            reason="Positive keywords detected",
        )
    elif hesitation_score >= 0.4:
        return EmotionalAnalysis(
            state="hesitant",
            confidence=min(hesitation_score, 1.0),
            suggested_tone="guiding",
            reason=", ".join(reasons) or "Hesitation signals detected",
        )
    else:
        return EmotionalAnalysis(
            state="neutral",
            confidence=0.7,
            suggested_tone="neutral",
            reason="No strong emotional signals",
        )


def _calculate_frustration_score(
    message_lower: str,
    message: str,
    metrics: BehaviorMetrics,
    reasons: list[str],
) -> float:
    """Calculate frustration score from text and behavior signals."""
    score = 0.0

    # Text-based signals
    for kw in FRUSTRATION_KEYWORDS:
        if kw in message_lower:
            score += 0.2
            reasons.append(f"keyword '{kw}'")

    # Punctuation signals
    if message.count("!") >= 3:
        score += 0.15
        reasons.append("multiple exclamations")
    if message.count("?") >= 3:
        score += 0.1
        reasons.append("multiple questions")

    # Behavior signals
    if metrics.rapid_clicks >= 5:
        score += 0.2
        reasons.append(f"{metrics.rapid_clicks} rapid clicks")
    if metrics.recent_errors >= 3:
        score += 0.25
        reasons.append(f"{metrics.recent_errors} errors")
    if metrics.repeated_messages >= 2:
        score += 0.15
        reasons.append("repeated messages")

    return score


def _calculate_success_score(message_lower: str) -> float:
    """Calculate success score from positive keywords."""
    score = 0.0
    for kw in SUCCESS_KEYWORDS:
        if kw in message_lower:
            score += 0.25
    return score


def _calculate_hesitation_score(metrics: BehaviorMetrics, reasons: list[str]) -> float:
    """Calculate hesitation score from time and navigation signals."""
    score = 0.0

    if metrics.idle_time_seconds >= 30:
        score += 0.3
        reasons.append(f"{metrics.idle_time_seconds}s idle")
    if metrics.back_navigations >= 2:
        score += 0.2
        reasons.append(f"{metrics.back_navigations} back navigations")

    return score
