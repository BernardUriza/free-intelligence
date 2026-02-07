"""Prescription CRUD Endpoints.

POST / - Create prescription
POST /from-soap - Create from SOAP data
GET /{id} - Get prescription
GET / - List prescriptions
PUT /{id} - Update prescription
GET /{id}/export - Export to text/json

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from typing import Any

from backend.domain.prescription.models.prescription import PrescriptionStatus
from backend.infrastructure.auth import User, get_current_user, validate_session_access
from backend.infrastructure.common.repository_singletons import get_task_repository
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.utils.common.logging.logger import get_logger
from backend.validators import validate_session_id
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .dependencies import get_template_engine_cached
from .models import (
    CreateFromSOAPRequest,
    CreatePrescriptionRequest,
    PrescriptionListResponse,
    PrescriptionResponse,
    UpdatePrescriptionRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions - CRUD"])


@router.post(
    "",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prescription(
    request: CreatePrescriptionRequest,
) -> PrescriptionResponse:
    """Create a new prescription."""
    engine = get_template_engine_cached()

    try:
        prescription = engine.create_prescription(
            template_id=request.template_id,
            patient=request.patient,
            physician=request.physician,
            diagnosis=request.diagnosis,
            medications=request.medications,
            session_id=request.session_id,
            diagnosis_code=request.diagnosis_code,
            general_instructions=request.general_instructions,
            next_appointment=request.next_appointment,
        )

        logger.info(
            "PRESCRIPTION_CREATED_API",
            prescription_id=prescription.id,
            medication_count=len(request.medications),
        )

        return PrescriptionResponse(
            success=True,
            prescription=prescription,
            message="Receta creada exitosamente",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/from-soap",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prescription_from_soap(
    request: CreateFromSOAPRequest,
    task_repo: ITaskRepository = Depends(get_task_repository),
    current_user: User = Depends(get_current_user),
) -> PrescriptionResponse:
    """Create a prescription from SOAP note data."""
    validate_session_id(request.session_id)
    validate_session_access(request.session_id, current_user, action="create prescription from SOAP")

    try:
        soap_data = task_repo.get_soap_data(request.session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SOAP data not found for session: {request.session_id}",
        ) from e

    engine = get_template_engine_cached()

    try:
        prescription = engine.create_prescription_from_soap(
            soap_data=soap_data,
            patient=request.patient,
            physician=request.physician,
            template_id=request.template_id,
            session_id=request.session_id,
        )

        logger.info(
            "PRESCRIPTION_FROM_SOAP_CREATED",
            prescription_id=prescription.id,
            session_id=request.session_id,
        )

        return PrescriptionResponse(
            success=True,
            prescription=prescription,
            message="Receta creada desde nota SOAP",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/{prescription_id}",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_prescription(prescription_id: str) -> PrescriptionResponse:
    """Get a prescription by ID."""
    engine = get_template_engine_cached()
    prescription = engine.get_prescription(prescription_id)

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription not found: {prescription_id}",
        )

    return PrescriptionResponse(success=True, prescription=prescription)


@router.get(
    "",
    response_model=PrescriptionListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_prescriptions(
    session_id: str | None = Query(default=None),
    patient_id: str | None = Query(default=None),
    physician_id: str | None = Query(default=None),
    status_filter: PrescriptionStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> PrescriptionListResponse:
    """List prescriptions with optional filters."""
    engine = get_template_engine_cached()
    prescriptions = engine.list_prescriptions(
        session_id=session_id,
        patient_id=patient_id,
        physician_id=physician_id,
        status=status_filter,
        limit=limit,
    )

    return PrescriptionListResponse(
        prescriptions=prescriptions,
        count=len(prescriptions),
    )


@router.put(
    "/{prescription_id}",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def update_prescription(
    prescription_id: str,
    request: UpdatePrescriptionRequest,
) -> PrescriptionResponse:
    """Update a draft prescription."""
    engine = get_template_engine_cached()

    updates: dict[str, Any] = {}
    for field, value in request.model_dump().items():
        if value is not None:
            updates[field] = value

    prescription = engine.update_prescription(prescription_id, updates)

    if not prescription:
        existing = engine.get_prescription(prescription_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update prescription in status: {existing.status}",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription not found: {prescription_id}",
        )

    return PrescriptionResponse(
        success=True,
        prescription=prescription,
        message="Receta actualizada",
    )


@router.get(
    "/{prescription_id}/export",
    status_code=status.HTTP_200_OK,
)
async def export_prescription(
    prescription_id: str,
    export_format: str = Query(default="text", description="Export format: text, json"),
) -> dict[str, Any]:
    """Export prescription to various formats."""
    engine = get_template_engine_cached()
    prescription = engine.get_prescription(prescription_id)

    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prescription not found: {prescription_id}",
        )

    if export_format == "text":
        content = engine.export_to_text(prescription_id)
        return {
            "format": "text",
            "content": content,
            "prescription_id": prescription_id,
        }
    elif export_format == "json":
        return {
            "format": "json",
            "content": prescription.model_dump(mode="json"),
            "prescription_id": prescription_id,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {export_format}. Use 'text' or 'json'.",
        )
