from __future__ import annotations

import re
from typing import TYPE_CHECKING

from backend.clients.dependencies import get_llm_client_dep
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, status

from ..assistant_schemas import IntroductionRequest, IntroductionResponse

if TYPE_CHECKING:
    from backend.clients.internal_llm_client import InternalLLMClient

logger = get_logger(__name__)

# Regex to strip Qwen3 thinking tags that may leak into response
_THINKING_TAG_PATTERN = re.compile(r"<think>.*?</think>|<think>", re.DOTALL | re.IGNORECASE)

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

        context: dict[str, str | bool] = {
            "enable_thinking": False,  # Disable thinking for faster response (~7x speedup)
        }
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

        # Defense-in-depth: strip any leaked <think> tags from Qwen3
        # Note: GenericParser already sanitizes, but this catches edge cases from cache/legacy
        response_text = result["response"]
        if "<think>" in response_text.lower():
            response_text = _THINKING_TAG_PATTERN.sub("", response_text).strip()
            logger.debug("INTRODUCTION_SANITIZED_THINKING_TAGS", original_len=len(result["response"]), sanitized_len=len(response_text))

        return IntroductionResponse(
            message=response_text,
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
    """Build the introduction prompt based on available context.

    OPTIMIZED: Short prompts for faster inference (~3-5s vs 20s+).
    """
    if request.physician_name and request.clinic_name:
        return f"Preséntate brevemente a Dr. {request.physician_name} de {request.clinic_name}."
    elif request.physician_name:
        return f"Preséntate brevemente a Dr. {request.physician_name}."
    else:
        return "Preséntate brevemente a un médico nuevo."
