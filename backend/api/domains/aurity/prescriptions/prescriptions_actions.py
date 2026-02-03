"""Prescription Action Endpoints.

POST /{id}/sign - Sign prescription
POST /{id}/cancel - Cancel prescription

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, HTTPException, status

from .dependencies import get_template_engine_cached
from .models import CancelPrescriptionRequest, PrescriptionResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions - Actions"])


@router.post(
    "/{prescription_id}/sign",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def sign_prescription(prescription_id: str) -> PrescriptionResponse:
    """Sign a prescription."""
    engine = get_template_engine_cached()

    try:
        prescription = engine.sign_prescription(prescription_id)

        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prescription not found: {prescription_id}",
            )

        logger.info(
            "PRESCRIPTION_SIGNED_API",
            prescription_id=prescription_id,
            hash=prescription.signature_hash[:16] if prescription.signature_hash else None,
        )

        return PrescriptionResponse(
            success=True,
            prescription=prescription,
            message="Receta firmada exitosamente",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/{prescription_id}/cancel",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_prescription(
    prescription_id: str,
    request: CancelPrescriptionRequest,
) -> PrescriptionResponse:
    """Cancel a prescription."""
    engine = get_template_engine_cached()

    try:
        prescription = engine.cancel_prescription(prescription_id, request.reason)

        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prescription not found: {prescription_id}",
            )

        logger.info(
            "PRESCRIPTION_CANCELLED_API",
            prescription_id=prescription_id,
            reason=request.reason,
        )

        return PrescriptionResponse(
            success=True,
            prescription=prescription,
            message="Receta cancelada",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
