"""
Free-Intelligence Assistant Workflow - AURITY

Conversational endpoints for Free-Intelligence AI persona.

Architecture:
  PUBLIC (this file) -> InternalLLMClient -> /internal/llm/* -> PersonaManager -> llm_generate

Endpoints:
- POST /workflows/aurity/assistant/introduction - Onboarding presentation
- POST /workflows/aurity/assistant/chat - General conversation (Auth0 required for memory)
- POST /workflows/aurity/assistant/public-chat - Public anonymous chat (rate-limited, DEPRECATED)

Modules:
- assistant_schemas.py - Pydantic request/response models
- emotional_analysis.py - Hybrid LLM + heuristic emotional detection

Author: Bernard Uriza Orozco
Created: 2025-11-18
Refactored: 2025-11-26
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request, status

from backend.clients import get_llm_client
from backend.logger import get_logger
from backend.security.rate_limiter import ip_rate_limiter, session_rate_limiter

# Import schemas from dedicated module
from .assistant_schemas import (
    IntroductionRequest,
    IntroductionResponse,
    ChatRequest,
    ChatResponse,
    PublicChatResponse,
)

# Import emotional analysis from dedicated module
from .emotional_analysis import analyze_emotional_state

logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# Introduction Endpoint
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
        message = _build_introduction_message(request)

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


def _build_introduction_message(request: IntroductionRequest) -> str:
    """Build the introduction prompt based on available context."""
    if request.physician_name and request.clinic_name:
        return (
            f"Present yourself to Dr. {request.physician_name} "
            f"from {request.clinic_name}. "
            "Explain who you are, where you reside (locally in their NAS), "
            "and how you'll help them with clinical documentation while "
            "ensuring their data sovereignty."
        )
    elif request.physician_name:
        return (
            f"Present yourself to Dr. {request.physician_name}. "
            "Explain who you are, where you reside (locally in their infrastructure), "
            "and how you'll help them with clinical workflows."
        )
    else:
        return (
            "Present yourself to a new physician who is onboarding. "
            "Explain who you are, where you reside (locally, not in the cloud), "
            "and how you help with clinical documentation while respecting data sovereignty."
        )


# ============================================================================
# Chat Endpoint
# ============================================================================


@router.post("/assistant/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest) -> ChatResponse:
    """General chat endpoint for Free-Intelligence conversations.

    This is a general-purpose endpoint for conversational interactions
    with Free-Intelligence outside of specific workflows.

    Enables infinite memory when doctor_id is provided in context.
    Supports hybrid emotional analysis when behavior_metrics is provided.

    Args:
        request: Message, optional context, and optional behavior_metrics

    Returns:
        Free-Intelligence's response with optional emotional_analysis

    Raises:
        500: If internal LLM call fails
    """
    try:
        # Extract doctor_id and persona from context (Auth0 user.sub)
        doctor_id = None
        persona = "general_assistant"  # Default persona
        if request.context:
            if "doctor_id" in request.context:
                doctor_id = request.context["doctor_id"]
            if "persona" in request.context:
                persona = request.context["persona"]

        logger.info(
            "ASSISTANT_CHAT_START",
            message_length=len(request.message),
            has_context=request.context is not None,
            has_behavior_metrics=request.behavior_metrics is not None,
            session_id=request.session_id,
            doctor_id=doctor_id,
            persona=persona,
            memory_enabled=doctor_id is not None,
        )

        llm_client = get_llm_client()

        # Run emotional analysis if metrics provided
        emotional_analysis = None
        if request.behavior_metrics is not None:
            emotional_analysis = await analyze_emotional_state(
                message=request.message,
                metrics=request.behavior_metrics,
                llm_client=llm_client,
            )
            logger.info(
                "EMOTIONAL_ANALYSIS_RESULT",
                state=emotional_analysis.state if emotional_analysis else "none",
                confidence=emotional_analysis.confidence if emotional_analysis else 0,
                suggested_tone=emotional_analysis.suggested_tone if emotional_analysis else "none",
            )

        result = await llm_client.chat(
            persona=persona,  # Use persona from context (frontend dropdown)
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
            emotional_analysis=emotional_analysis,
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
# Public Chat Endpoint (DEPRECATED)
# ============================================================================


@router.post("/assistant/public-chat", response_model=PublicChatResponse, deprecated=True)
async def public_chat(request_body: ChatRequest, http_request: Request) -> PublicChatResponse:
    """
    DEPRECATED: Use /assistant/chat instead.

    Public anonymous chat endpoint with rate-limiting.

    **DEPRECATION NOTICE**: This endpoint is deprecated and will be removed in a
    future version. Please use `/assistant/chat` instead, which handles both
    authenticated (with memory) and anonymous (ephemeral) conversations automatically.

    Architecture:
        - NO Auth0 required (doctor_id always None)
        - Rate-limit: 20 req/min per IP, 10 req/min per session
        - NO persistent memory (ephemeral conversation)
        - Kill-switch support via KILL_SWITCH_PUBLIC_CHAT env var

    Args:
        request_body: Chat request (message, context, session_id)
        http_request: FastAPI Request object (for IP extraction)

    Returns:
        ChatResponse with remaining_requests and retry_after

    Raises:
        503: If kill-switch is active
        429: If rate limit exceeded
        500: If internal LLM call fails
    """
    logger.warning(
        "PUBLIC_CHAT_DEPRECATED",
        message="Endpoint /assistant/public-chat is deprecated. Use /assistant/chat instead.",
        session_id=request_body.session_id,
    )

    # 1. Kill-switch check
    if os.getenv("KILL_SWITCH_PUBLIC_CHAT", "false").lower() == "true":
        logger.warning("PUBLIC_CHAT_KILL_SWITCH_ACTIVE")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Public chat is temporarily unavailable. Please try again later.",
            headers={"Retry-After": "60"},
        )

    # 2. Rate-limit: IP-based
    client_ip = http_request.client.host if http_request.client else "unknown"

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

    # 3. Rate-limit: Session-based
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

    # 4. Call LLM
    try:
        persona = "general_assistant"
        if request_body.context and "persona" in request_body.context:
            persona = request_body.context["persona"]

        logger.info(
            "PUBLIC_CHAT_START",
            message_length=len(request_body.message),
            session_id=session_id,
            client_ip=client_ip,
            persona=persona,
            memory_enabled=False,
        )

        llm_client = get_llm_client()

        result = await llm_client.chat(
            persona=persona,
            message=request_body.message,
            context=request_body.context or {},
            session_id=session_id,
            doctor_id=None,  # NO persistent memory
            use_memory=False,
        )

        # Calculate remaining requests
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
