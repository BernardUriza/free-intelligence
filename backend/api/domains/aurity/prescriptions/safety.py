"""Combined Safety Check Endpoint.

POST /safety/check - Full safety check (interactions + allergies)

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from typing import Any

from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, status

from .dependencies import get_template_engine_cached
from .models import FullSafetyCheckRequest
from .transformers import format_allergy_alert_brief, format_interaction_alert_brief

logger = get_logger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions - Safety"])


@router.post(
    "/safety/check",
    status_code=status.HTTP_200_OK,
)
async def full_safety_check(
    request: FullSafetyCheckRequest,
) -> dict[str, Any]:
    """Run comprehensive safety checks on medications."""
    engine = get_template_engine_cached()
    result = engine.full_safety_check(
        medications=request.medications,
        patient_allergies=request.patient_allergies,
    )

    logger.info(
        "FULL_SAFETY_CHECK_API",
        medication_count=len(request.medications),
        can_proceed=result["can_proceed"],
        has_critical=result["has_critical_issues"],
    )

    return {
        "medications_checked": [m.name for m in request.medications],
        "patient_allergies": request.patient_allergies,
        "can_proceed": result["can_proceed"],
        "has_critical_issues": result["has_critical_issues"],
        "summary": result["summary"],
        "interactions": {
            "alert_count": len(result["interactions"].alerts),
            "has_major": result["interactions"].has_major_interactions,
            "can_proceed": result["interactions"].can_proceed,
            "summary": result["interactions"].summary,
            "alerts": [
                format_interaction_alert_brief(a) for a in result["interactions"].alerts
            ],
        },
        "allergies": {
            "alert_count": len(result["allergies"].alerts),
            "has_severe": result["allergies"].has_severe_allergies,
            "can_proceed": result["allergies"].can_proceed,
            "summary": result["allergies"].summary,
            "alerts": [format_allergy_alert_brief(a) for a in result["allergies"].alerts],
        },
    }
