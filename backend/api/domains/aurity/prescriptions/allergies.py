"""Allergy Check Endpoints.

POST /allergies/check - Check medications vs patient allergies
GET /allergies/medication/{name} - Get allergens for medication
GET /allergies/stats - Get allergen db stats

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from typing import Any

from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, status

from .dependencies import get_allergy_checker_cached
from .models import CheckAllergiesRequest
from .transformers import format_allergy_result

logger = get_logger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions - Allergies"])


@router.post(
    "/allergies/check",
    status_code=status.HTTP_200_OK,
)
async def check_allergies(
    request: CheckAllergiesRequest,
) -> dict[str, Any]:
    """Check medications against patient allergies."""
    checker = get_allergy_checker_cached()
    result = checker.check_medications(
        medications=request.medications,
        patient_allergies=request.patient_allergies,
    )

    logger.info(
        "ALLERGIES_CHECKED_API",
        medication_count=len(request.medications),
        allergy_count=len(request.patient_allergies),
        alert_count=len(result.alerts),
        has_severe=result.has_severe_allergies,
    )

    return format_allergy_result(result)


@router.get(
    "/allergies/medication/{medication_name}",
    status_code=status.HTTP_200_OK,
)
async def get_medication_allergens(medication_name: str) -> dict[str, Any]:
    """Get allergens related to a specific medication."""
    checker = get_allergy_checker_cached()
    allergens = checker.get_allergens_for_medication(medication_name)

    return {
        "medication_name": medication_name,
        "allergen_count": len(allergens),
        "allergens": [
            {
                "id": a.id,
                "name": a.name_es,
                "type": a.allergen_type.value,
                "severity": a.severity.value,
                "notes": a.notes_es,
            }
            for a in allergens
        ],
    }


@router.get(
    "/allergies/stats",
    status_code=status.HTTP_200_OK,
)
async def get_allergy_stats() -> dict[str, Any]:
    """Get statistics about the allergen database."""
    checker = get_allergy_checker_cached()
    stats = checker.get_stats()

    return {"stats": stats}
