"""
Assistant Workflow Schemas - AURITY

Pydantic models for request/response validation in assistant endpoints.

Author: Bernard Uriza Orozco
Created: 2025-11-18
Refactored: 2025-11-26
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ============================================================================
# Behavior & Emotional Analysis Schemas
# ============================================================================


class BehaviorMetrics(BaseModel):
    """User behavior metrics for emotional analysis.

    These metrics are collected on the frontend and sent with each message
    to enable hybrid LLM + heuristic emotional analysis.
    """

    rapid_clicks: int = Field(default=0, description="Number of rapid clicks (<500ms apart)")
    repeated_messages: int = Field(default=0, description="Number of repeated messages")
    idle_time_seconds: int = Field(default=0, description="Seconds since last interaction")
    back_navigations: int = Field(default=0, description="Number of back navigations")
    recent_errors: int = Field(default=0, description="Recent error count")
    phase_time_seconds: int = Field(default=0, description="Time on current phase")


class EmotionalAnalysis(BaseModel):
    """LLM-analyzed emotional state.

    Returned when behavior_metrics is provided in ChatRequest.
    Uses hybrid approach: LLM analysis with heuristic fallback.
    """

    state: str = Field(default="neutral", description="Detected emotional state")
    confidence: float = Field(default=0.7, description="Confidence score 0-1")
    suggested_tone: str = Field(default="neutral", description="Suggested response tone")
    reason: str = Field(default="", description="Reason for detection")


# ============================================================================
# Introduction Schemas
# ============================================================================


class IntroductionRequest(BaseModel):
    """Request for Free-Intelligence introduction."""

    physician_name: str | None = Field(
        None, description="Physician's name for personalized greeting"
    )
    clinic_name: str | None = Field(None, description="Clinic/practice name")


class IntroductionResponse(BaseModel):
    """Free-Intelligence introduction response."""

    message: str = Field(..., description="Free-Intelligence's introduction message")
    persona: str = Field(
        default="onboarding_guide",
        description="Persona used for this response",
    )
    tokens_used: int = Field(default=0, description="Tokens consumed in this interaction")
    latency_ms: int = Field(default=0, description="Response latency in milliseconds")


# ============================================================================
# Chat Schemas
# ============================================================================


class ChatRequest(BaseModel):
    """General chat request."""

    message: str = Field(..., description="User's message")
    context: dict | None = Field(None, description="Optional context")
    session_id: str | None = Field(None, description="Session ID for audit trail")
    behavior_metrics: BehaviorMetrics | None = Field(
        None, description="User behavior metrics for emotional analysis"
    )


class ChatResponse(BaseModel):
    """Chat response."""

    message: str = Field(..., description="Free-Intelligence's response")
    persona: str = Field(default="general_assistant")
    tokens_used: int = Field(default=0)
    latency_ms: int = Field(default=0)
    emotional_analysis: EmotionalAnalysis | None = Field(
        None, description="LLM-analyzed emotional state (if behavior_metrics provided)"
    )


class PublicChatResponse(ChatResponse):
    """Extended response for public chat with rate-limit info.

    DEPRECATED: Use /assistant/chat instead. This endpoint remains for backward
    compatibility but will be removed in a future version.
    """

    remaining_requests: int = Field(..., description="Remaining requests before rate limit")
    retry_after: int | None = Field(None, description="Seconds to wait if rate limited")
