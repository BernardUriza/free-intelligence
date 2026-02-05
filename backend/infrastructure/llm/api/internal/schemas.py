"""Internal LLM API Schemas - Request/Response models.

Pydantic schemas for the internal LLM chat and structured extraction endpoints.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Infrastructure Migration)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# CHAT ENDPOINTS
# ============================================================================


class ChatMessage(BaseModel):
    """Single message in a conversation (OpenAI-compatible format)."""

    role: str = Field(..., description="Message role: system, user, assistant")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request for conversational chat with Free-Intelligence."""

    persona: str = Field(
        ...,
        description="Assistant mode: onboarding_guide, clinical_advisor, soap_editor",
        examples=["onboarding_guide", "clinical_advisor", "soap_editor"],
    )
    message: str = Field(..., min_length=1, max_length=5000)
    messages: list[ChatMessage] | None = Field(
        default=None,
        description="Full conversation history (OpenAI format). Used when memory is disabled.",
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional context (patient_id, session_id, soap_data, etc.)",
    )
    session_id: str | None = Field(default=None, description="Session ID for audit logging")
    doctor_id: str | None = Field(
        default=None,
        description="Doctor ID for conversation memory (required for memory)",
    )
    use_memory: bool = Field(
        default=False,
        description="Enable conversation memory (requires doctor_id)",
    )
    provider: str | None = Field(
        default=None, description="LLM provider name (defaults to policy)"
    )


class ChatResponse(BaseModel):
    """Response with ultra-detailed logging."""

    response: str
    thinking: str | None = Field(
        default=None, description="Optional model reasoning (if available)"
    )
    persona: str
    tokens_used: int
    latency_ms: int
    model: str
    voice: str = Field(
        description="Azure TTS voice for this persona (nova, alloy, echo, fable, onyx, shimmer)"
    )

    # Observability metadata
    prompt_hash: str = Field(description="SHA256 of prompt sent (first 12 chars)")
    response_hash: str = Field(description="SHA256 of response (first 12 chars)")
    logged_at: str = Field(description="ISO8601 timestamp")


# ============================================================================
# STRUCTURED EXTRACTION ENDPOINTS
# ============================================================================


class StructuredRequest(BaseModel):
    """Request for structured extraction via LLM."""

    persona: str = Field(..., description="Assistant mode")
    command: str = Field(..., min_length=1, description="Natural language command")
    context: dict[str, Any] = Field(..., description="Required context (e.g., current_soap)")
    output_schema: dict[str, str] = Field(..., description="Expected JSON output schema")
    session_id: str | None = Field(default=None, description="Session ID for audit")
    provider: str | None = Field(
        default=None, description="LLM provider name (defaults to policy)"
    )


class StructuredResponse(BaseModel):
    """Response with structured data + observability."""

    data: dict[str, Any] = Field(description="Extracted data per schema")
    explanation: str = Field(description="Explanation of what was done")
    tokens_used: int
    latency_ms: int
    model: str

    # Observability
    prompt_hash: str
    response_hash: str
    logged_at: str
