"""
Free-Intelligence Assistant API - Public Endpoints

Endpoints conversacionales para Free-Intelligence, la IA residente del sistema.

Characteristics:
- Obsessive with clinical details
- Sharp empathy (direct, no corporate fluff)
- Focused on data sovereignty (physician owns the data)
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.clients import get_llm_client
from backend.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["assistant"])


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
    tokens_used: int = Field(default=0, description="Tokens consumed in this interaction")
    latency_ms: int = Field(default=0, description="Response latency in milliseconds")


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

        # Call internal LLM endpoint via HTTP client
        llm_client = get_llm_client()

        result = await llm_client.chat(
            persona="onboarding_guide",
            message=message,
            context=context if context else None,
            session_id=None,  # No session context for onboarding
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


@router.post("/assistant/chat")
async def chat_with_assistant(
    message: str,
    context: Optional[dict] = None,
    session_id: Optional[str] = None,
):
    """General chat endpoint for Free-Intelligence conversations.

    This is a general-purpose endpoint for conversational interactions
    with Free-Intelligence outside of specific workflows.

    Args:
        message: User's message
        context: Optional context dict
        session_id: Optional session ID for audit trail

    Returns:
        Free-Intelligence's response

    Raises:
        500: If internal LLM call fails
    """
    try:
        logger.info(
            "ASSISTANT_CHAT_START",
            message_length=len(message),
            has_context=context is not None,
            session_id=session_id,
        )

        llm_client = get_llm_client()

        result = await llm_client.chat(
            persona="general_assistant",
            message=message,
            context=context,
            session_id=session_id,
        )

        logger.info(
            "ASSISTANT_CHAT_SUCCESS",
            tokens=result.get("tokens_used", 0),
            latency=result.get("latency_ms", 0),
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(
            "ASSISTANT_CHAT_FAILED",
            error=str(e),
            error_type=type(e).__name__,
            session_id=session_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat with assistant failed: {e!s}",
        ) from e
