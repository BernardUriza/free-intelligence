from __future__ import annotations

from typing import TYPE_CHECKING

from backend.clients.dependencies import get_llm_client_dep
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, status

from ..assistant_schemas import IntroductionRequest, IntroductionResponse

if TYPE_CHECKING:
    from backend.clients.internal_llm_client import InternalLLMClient

logger = get_logger(__name__)

router = APIRouter()


@router.post("/assistant/introduction", response_model=IntroductionResponse)
async def get_introduction(
    request: IntroductionRequest,
    llm_client: "InternalLLMClient" = Depends(get_llm_client_dep),
) -> IntroductionResponse:
    """Get Free-Intelligence's introduction for onboarding.

    Presents the assistant with clinical-grade tone and data sovereignty focus.
    """
    try:
        logger.info(
            "ASSISTANT_INTRODUCTION_START",
            has_physician_name=request.physician_name is not None,
            has_clinic_name=request.clinic_name is not None,
        )

        context: dict[str, str] = {}
        if request.physician_name:
            context["physician_name"] = request.physician_name
        if request.clinic_name:
            context["clinic_name"] = request.clinic_name

        message = _build_introduction_message(request)

        doctor_id = context.get("doctor_id") if context else None

        # INJECTED: llm_client comes from Depends(get_llm_client_dep)

        result = await llm_client.chat(
            persona="onboarding_guide",
            message=message,
            context=context if context else None,
            session_id=None,
            doctor_id=doctor_id,
            use_memory=doctor_id is not None,
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
