"""Drug Interaction Endpoints.

POST /interactions/check - Check drug-drug interactions
POST /interactions/check-prescription - Check with Medication objects
GET /interactions/drug/{name} - Get interactions for drug
GET /interactions/stats - Get interaction db stats

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from typing import Any

from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, status

from .dependencies import get_interaction_checker_cached
from .models import CheckInteractionsRequest, CheckPrescriptionInteractionsRequest
from .transformers import format_interaction_result

logger = get_logger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions - Interactions"])


@router.post(
    "/interactions/check",
    status_code=status.HTTP_200_OK,
)
async def check_interactions(
    request: CheckInteractionsRequest,
) -> dict[str, Any]:
    """Check medications for drug-drug interactions."""
    checker = get_interaction_checker_cached()
    result = checker.check_medications(request.medications)

    logger.info(
        "INTERACTIONS_CHECKED_API",
        medication_count=len(request.medications),
        alert_count=len(result.alerts),
        has_major=result.has_major_interactions,
    )

    return format_interaction_result(result)


@router.post(
    "/interactions/check-prescription",
    status_code=status.HTTP_200_OK,
)
async def check_prescription_interactions(
    request: CheckPrescriptionInteractionsRequest,
) -> dict[str, Any]:
    """Check Medication objects for drug-drug interactions."""
    checker = get_interaction_checker_cached()
    result = checker.check_medication_objects(request.medications)

    return format_interaction_result(result)


@router.get(
    "/interactions/drug/{drug_name}",
    status_code=status.HTTP_200_OK,
)
async def get_drug_interactions(drug_name: str) -> dict[str, Any]:
    """Get all known interactions for a specific drug."""
    checker = get_interaction_checker_cached()
    interactions = checker.get_interactions_for_drug(drug_name)

    return {
        "drug_name": drug_name,
        "interaction_count": len(interactions),
        "interactions": [
            {
                "id": i.id,
                "interacting_drug": i.get_other_drug(drug_name),
                "severity": i.severity.value,
                "effect": i.effect_es,
                "recommendation": i.recommendation_es,
                "mechanism": i.mechanism.value if i.mechanism else None,
            }
            for i in interactions
        ],
    }


@router.get(
    "/interactions/stats",
    status_code=status.HTTP_200_OK,
)
async def get_interaction_stats() -> dict[str, Any]:
    """Get statistics about the interaction database."""
    checker = get_interaction_checker_cached()
    stats = checker.get_stats()

    return {"stats": stats}
