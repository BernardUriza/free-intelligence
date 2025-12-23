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


class ReceptionistState(BaseModel):
    """Receptionist conversation state for check-in flows."""

    state: str = Field(..., description="Current state in check-in flow")
    quick_replies: list[str] = Field(default_factory=list, description="Quick reply options")
    actions: list[dict] = Field(default_factory=list, description="Actions to execute")
    metadata: dict = Field(default_factory=dict, description="Additional state metadata")


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
# OpenAI-Style Message Schemas
# ============================================================================


class Message(BaseModel):
    """OpenAI-style message format."""

    role: str = Field(
        ..., description="Role of the message author", examples=["system", "user", "assistant"]
    )
    content: str = Field(..., description="Content of the message")
    name: str | None = Field(
        None, description="Optional name for the author (for function calling)"
    )


class ChatCompletionRequest(BaseModel):
    """OpenAI-style chat completion request."""

    messages: list[Message] = Field(
        ..., min_length=1, description="List of messages in the conversation"
    )
    model: str = Field(
        default="qwen3:1.7b", description="Model to use for completion (Ollama local)"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=2048, ge=1, le=4096, description="Maximum tokens to generate")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    stop: str | list[str] | None = Field(None, description="Stop sequences")
    stream: bool = Field(default=False, description="Whether to stream the response")
    user: str | None = Field(None, description="Unique identifier for the user")

    # AURITY-specific extensions
    persona: str = Field(..., description="AURITY persona to use (REQUIRED)")
    session_id: str | None = Field(None, description="Session ID for audit trail")
    response_mode: str = Field(
        default="explanatory",
        description="Response style: 'concise' (3-4 sentences) or 'explanatory' (detailed)",
    )
    behavior_metrics: BehaviorMetrics | None = Field(
        None, description="User behavior metrics for emotional analysis"
    )
    receptionist_config: dict | None = Field(
        None, description="Receptionist-specific configuration for check-in flows"
    )
    enable_thinking: bool = Field(
        default=True,
        description="Enable model reasoning/thinking (Qwen3). Set false to skip thinking phase and save compute.",
    )


class ChatCompletionChoice(BaseModel):
    """OpenAI-style completion choice."""

    index: int = Field(..., description="Index of the choice")
    message: Message = Field(..., description="The message generated by the model")
    finish_reason: str = Field(
        ...,
        description="Reason the generation finished",
        examples=["stop", "length", "function_call"],
    )


class ChatCompletionUsage(BaseModel):
    """OpenAI-style token usage statistics."""

    prompt_tokens: int = Field(..., description="Number of tokens in the prompt")
    completion_tokens: int = Field(..., description="Number of tokens in the completion")
    total_tokens: int = Field(..., description="Total number of tokens used")


class ChatCompletionResponse(BaseModel):
    """OpenAI-style chat completion response (non-streaming)."""

    id: str = Field(..., description="Unique identifier for the completion")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used for completion")
    choices: list[ChatCompletionChoice] = Field(..., description="List of completion choices")
    usage: ChatCompletionUsage = Field(..., description="Token usage statistics")

    # AURITY-specific extensions
    persona: str = Field(
        default="general_assistant", description="AURITY persona used for this response"
    )
    emotional_analysis: EmotionalAnalysis | None = Field(
        None, description="Emotional analysis if behavior_metrics was provided"
    )
    receptionist_state: ReceptionistState | None = Field(
        None, description="Receptionist conversation state for check-in flows"
    )
    is_anonymous: bool = Field(
        default=False,
        description="True if no doctor_id was provided. Messages saved to 'anonymous' storage.",
    )
    thinking: str | None = Field(
        None,
        description="Model reasoning/thinking process (Qwen3 thinking mode). Only populated when model supports it.",
    )


class ChatCompletionDelta(BaseModel):
    """OpenAI-style streaming delta."""

    role: str | None = Field(None, description="Role of the message (only for first chunk)")
    content: str | None = Field(None, description="Content delta")


class ChatCompletionStreamChoice(BaseModel):
    """OpenAI-style streaming choice."""

    index: int = Field(..., description="Index of the choice")
    delta: ChatCompletionDelta = Field(..., description="Delta content")
    finish_reason: str | None = Field(None, description="Reason the generation finished")


class ChatCompletionStreamResponse(BaseModel):
    """OpenAI-style streaming response chunk."""

    id: str = Field(..., description="Unique identifier for the completion")
    object: str = Field(default="chat.completion.chunk", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used for completion")
    choices: list[ChatCompletionStreamChoice] = Field(..., description="List of streaming choices")
