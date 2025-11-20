"""
Free-Intelligence Assistant Workflow - AURITY

Conversational endpoints for Free-Intelligence AI persona.

Architecture:
  PUBLIC (this file) → InternalLLMClient → /internal/llm/* → PersonaManager → llm_generate

Endpoints:
- POST /workflows/aurity/assistant/introduction - Onboarding presentation
- POST /workflows/aurity/assistant/chat - General conversation (Auth0 required for memory)
- POST /workflows/aurity/assistant/public-chat - Public anonymous chat (rate-limited)

Author: Bernard Uriza Orozco
Created: 2025-11-18
"""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.clients import get_llm_client
from backend.logger import get_logger
from backend.security.rate_limiter import ip_rate_limiter, session_rate_limiter

logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================


class IntroductionRequest(BaseModel):
    """Request for Free-Intelligence introduction."""

    physician_name: Optional[str] = Field(
        None, description="Physician's name for personalized greeting"
    )
    clinic_name: Optional[str] = Field(None, description="Clinic/practice name")


class IntroductionResponse(BaseModel):
    """Free-Intelligence introduction response."""

    message: str = Field(..., description="Free-Intelligence's introduction message")
    persona: str = Field(
        default="onboarding_guide",
        description="Persona used for this response",
    )
    tokens_used: int = Field(
        default=0, description="Tokens consumed in this interaction"
    )
    latency_ms: int = Field(default=0, description="Response latency in milliseconds")


class ChatRequest(BaseModel):
    """General chat request."""

    message: str = Field(..., description="User's message")
    context: Optional[dict] = Field(None, description="Optional context")
    session_id: Optional[str] = Field(None, description="Session ID for audit trail")


class ChatResponse(BaseModel):
    """Chat response."""

    message: str = Field(..., description="Free-Intelligence's response")
    persona: str = Field(default="general_assistant")
    tokens_used: int = Field(default=0)
    latency_ms: int = Field(default=0)


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/assistant/introduction", response_model=IntroductionResponse)
async def get_introduction(request: IntroductionRequest) -> IntroductionResponse:
    """Get Free-Intelligence's introduction for onboarding.

    Free-Intelligence presents herself with her characteristic personality:
    - Obsessive with clinical details
    - Sharp empathy (direct, no marketing)
    - Focused on data sovereignty

    This endpoint is designed for the onboarding flow to introduce
    the AI resident that will accompany the physician throughout
    the clinical workflow lifecycle.

    Args:
        request: Optional physician/clinic context for personalization

    Returns:
        IntroductionResponse with Free-Intelligence's message

    Raises:
        500: If internal LLM call fails
    """
    try:
        logger.info(
            "ASSISTANT_INTRODUCTION_START",
            has_physician_name=request.physician_name is not None,
            has_clinic_name=request.clinic_name is not None,
        )

        # Build context for persona
        context = {}
        if request.physician_name:
            context["physician_name"] = request.physician_name
        if request.clinic_name:
            context["clinic_name"] = request.clinic_name

        # Build message for Free-Intelligence
        if request.physician_name and request.clinic_name:
            message = (
                f"Present yourself to Dr. {request.physician_name} "
                f"from {request.clinic_name}. "
                "Explain who you are, where you reside (locally in their NAS), "
                "and how you'll help them with clinical documentation while "
                "ensuring their data sovereignty."
            )
        elif request.physician_name:
            message = (
                f"Present yourself to Dr. {request.physician_name}. "
                "Explain who you are, where you reside (locally in their infrastructure), "
                "and how you'll help them with clinical workflows."
            )
        else:
            message = (
                "Present yourself to a new physician who is onboarding. "
                "Explain who you are, where you reside (locally, not in the cloud), "
                "and how you help with clinical documentation while respecting data sovereignty."
            )

        # Extract doctor_id from context (Auth0 user.sub) if available
        doctor_id = context.get("doctor_id") if context else None

        # Call internal LLM endpoint via HTTP client
        llm_client = get_llm_client()

        result = await llm_client.chat(
            persona="onboarding_guide",
            message=message,
            context=context if context else None,
            session_id=None,  # No session context for onboarding
            doctor_id=doctor_id,  # Pass doctor_id for memory
            use_memory=doctor_id is not None,  # Enable memory if doctor_id present
        )

        logger.info(
            "ASSISTANT_INTRODUCTION_SUCCESS",
            tokens=result.get("tokens_used", 0),
            latency=result.get("latency_ms", 0),
            response_length=len(result.get("response", "")),
        )

        return IntroductionResponse(
            message=result["response"],
            persona=result["persona"],
            tokens_used=result.get("tokens_used", 0),
            latency_ms=result.get("latency_ms", 0),
        )

    except Exception as e:
        logger.error(
            "ASSISTANT_INTRODUCTION_FAILED",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Free-Intelligence introduction: {e!s}",
        ) from e


@router.post("/assistant/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest) -> ChatResponse:
    """General chat endpoint for Free-Intelligence conversations.

    This is a general-purpose endpoint for conversational interactions
    with Free-Intelligence outside of specific workflows.

    Enables infinite memory when doctor_id is provided in context.

    Args:
        request: Message and optional context (context.doctor_id enables memory)

    Returns:
        Free-Intelligence's response

    Raises:
        500: If internal LLM call fails
    """
    try:
        # Extract doctor_id from context (Auth0 user.sub)
        doctor_id = None
        if request.context and "doctor_id" in request.context:
            doctor_id = request.context["doctor_id"]

        logger.info(
            "ASSISTANT_CHAT_START",
            message_length=len(request.message),
            has_context=request.context is not None,
            session_id=request.session_id,
            doctor_id=doctor_id,
            memory_enabled=doctor_id is not None,
        )

        llm_client = get_llm_client()

        result = await llm_client.chat(
            persona="general_assistant",
            message=request.message,
            context=request.context,
            session_id=request.session_id,
            doctor_id=doctor_id,  # Pass doctor_id for memory
            use_memory=doctor_id is not None,  # Auto-enable memory if doctor_id present
        )

        logger.info(
            "ASSISTANT_CHAT_SUCCESS",
            tokens=result.get("tokens_used", 0),
            latency=result.get("latency_ms", 0),
            session_id=request.session_id,
        )

        return ChatResponse(
            message=result["response"],
            persona=result["persona"],
            tokens_used=result.get("tokens_used", 0),
            latency_ms=result.get("latency_ms", 0),
        )

    except Exception as e:
        logger.error(
            "ASSISTANT_CHAT_FAILED",
            error=str(e),
            error_type=type(e).__name__,
            session_id=request.session_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat with assistant failed: {e!s}",
        ) from e


# ============================================================================
# PUBLIC CHAT (Anonymous, Rate-Limited, Ephemeral)
# ⚠️ DEPRECATED: Use /assistant/chat instead (handles both authenticated + anonymous)
# This endpoint will be removed in a future version.
# ============================================================================


class PublicChatResponse(ChatResponse):
    """Extended response for public chat with rate-limit info.

    DEPRECATED: Use /assistant/chat instead. This endpoint remains for backward
    compatibility but will be removed in a future version.
    """

    remaining_requests: int = Field(
        ..., description="Remaining requests before rate limit"
    )
    retry_after: Optional[int] = Field(
        None, description="Seconds to wait if rate limited"
    )


@router.post("/assistant/public-chat", response_model=PublicChatResponse, deprecated=True)
async def public_chat(
    request_body: ChatRequest, http_request: Request
) -> PublicChatResponse:
    """
    ⚠️ DEPRECATED: Use /assistant/chat instead.

    Public anonymous chat endpoint with rate-limiting.

    **DEPRECATION NOTICE**: This endpoint is deprecated and will be removed in a
    future version. Please use `/assistant/chat` instead, which handles both
    authenticated (with memory) and anonymous (ephemeral) conversations automatically.

    Architecture:
        - NO Auth0 required (doctor_id always None)
        - Rate-limit: 20 req/min per IP, 10 req/min per session
        - NO persistent memory (ephemeral conversation)
        - Kill-switch support via KILL_SWITCH_PUBLIC_CHAT env var

    Constraints:
        - IP rate-limit: 20 requests/min, burst 5
        - Session rate-limit: 10 requests/min, burst 3
        - No message count limit (handled client-side for UX)
        - No TTL storage (uses localStorage client-side)

    Args:
        request_body: Chat request (message, context, session_id)
        http_request: FastAPI Request object (for IP extraction)

    Returns:
        ChatResponse with remaining_requests and retry_after

    Raises:
        503: If kill-switch is active
        429: If rate limit exceeded
        500: If internal LLM call fails

    Example:
        >>> # Frontend (no Auth0) - DEPRECATED, use /assistant/chat instead
        >>> response = await fetch("/api/workflows/aurity/assistant/public-chat", {
        ...     method: "POST",
        ...     body: JSON.stringify({ message: "¿Qué es AURITY?" })
        ... })
        >>> console.log(response.remaining_requests)  # 19 (if 20 rpm limit)
    """
    logger.warning(
        "PUBLIC_CHAT_DEPRECATED",
        message="Endpoint /assistant/public-chat is deprecated. Use /assistant/chat instead.",
        session_id=request_body.session_id,
    )
    # 1. Kill-switch check (priority: fail fast without consuming resources)
    if os.getenv("KILL_SWITCH_PUBLIC_CHAT", "false").lower() == "true":
        logger.warning("PUBLIC_CHAT_KILL_SWITCH_ACTIVE")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Public chat is temporarily unavailable. Please try again later.",
            headers={"Retry-After": "60"},
        )

    # 2. Rate-limit: IP-based (prevent abuse from single IP)
    client_ip = (
        http_request.client.host if http_request.client else "unknown"
    )

    if not ip_rate_limiter.allow(client_ip):
        retry_after = ip_rate_limiter.get_retry_after(client_ip)

        logger.warning(
            "PUBLIC_CHAT_IP_RATE_LIMITED",
            ip=client_ip,
            retry_after=retry_after,
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for IP {client_ip}. Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    # 3. Rate-limit: Session-based (prevent spam within session)
    session_id = request_body.session_id or "anonymous"

    if not session_rate_limiter.allow(session_id):
        retry_after = session_rate_limiter.get_retry_after(session_id)

        logger.warning(
            "PUBLIC_CHAT_SESSION_RATE_LIMITED",
            session_id=session_id,
            retry_after=retry_after,
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests for this session. Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    # 4. Call LLM (reuse exact logic from /assistant/chat but doctor_id=None)
    try:
        logger.info(
            "PUBLIC_CHAT_START",
            message_length=len(request_body.message),
            session_id=session_id,
            client_ip=client_ip,
            memory_enabled=False,  # Always false for public
        )

        llm_client = get_llm_client()

        result = await llm_client.chat(
            persona="general_assistant",
            message=request_body.message,
            context=request_body.context or {},
            session_id=session_id,
            doctor_id=None,  # NO doctor_id → NO persistent memory
            use_memory=False,  # Explicitly disable memory
        )

        # Calculate remaining requests (for X-RateLimit-Remaining header)
        remaining_ip = ip_rate_limiter.get_remaining(client_ip)
        remaining_session = session_rate_limiter.get_remaining(session_id)
        remaining = min(remaining_ip, remaining_session)

        logger.info(
            "PUBLIC_CHAT_SUCCESS",
            tokens=result.get("tokens_used", 0),
            latency=result.get("latency_ms", 0),
            session_id=session_id,
            remaining_requests=remaining,
        )

        return PublicChatResponse(
            message=result["response"],
            persona=result["persona"],
            tokens_used=result.get("tokens_used", 0),
            latency_ms=result.get("latency_ms", 0),
            remaining_requests=remaining,
            retry_after=None,
        )

    except Exception as e:
        logger.error(
            "PUBLIC_CHAT_FAILED",
            error=str(e),
            error_type=type(e).__name__,
            session_id=session_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Public chat failed: {e!s}",
        ) from e
