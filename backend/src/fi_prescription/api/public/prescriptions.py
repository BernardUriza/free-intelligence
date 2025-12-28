"""Prescription API Endpoints - Templates and Prescriptions.

PUBLIC layer endpoints for prescription management:
- GET /templates → List available templates
- GET /templates/{id} → Get template details
- POST /prescriptions → Create prescription
- GET /prescriptions/{id} → Get prescription
- PUT /prescriptions/{id} → Update prescription
- POST /prescriptions/{id}/sign → Sign prescription
- POST /prescriptions/{id}/cancel → Cancel prescription
- GET /prescriptions/{id}/export → Export to text/PDF

Architecture:
  PUBLIC (this file) → SERVICE (TemplateEngine) → Storage

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-002
"""

from __future__ import annotations

from typing import Any, Optional

from backend.src.fi_common.logging.logger import get_logger
from backend.validators import validate_session_id
from fastapi import APIRouter, HTTPException, Query, status
from fi_prescription.models.medication import Medication
from fi_prescription.models.prescription import (
    PatientInfo,
    PhysicianInfo,
    Prescription,
    PrescriptionStatus,
)
from fi_prescription.models.template import PrescriptionTemplate
from fi_prescription.services.template_engine import get_template_engine
from pydantic import BaseModel, Field

logger = get_logger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


# ============================================================================
# Request/Response Models
# ============================================================================


class CreatePrescriptionRequest(BaseModel):
    """Request body for creating a prescription."""

    template_id: str = Field(
        default="default",
        description="Template ID to use",
    )
    session_id: str | None = Field(
        default=None,
        description="Session ID to link prescription",
    )
    patient: PatientInfo = Field(
        ...,
        description="Patient information",
    )
    physician: PhysicianInfo = Field(
        ...,
        description="Physician information",
    )
    diagnosis: str = Field(
        ...,
        min_length=1,
        description="Primary diagnosis",
    )
    diagnosis_code: str | None = Field(
        default=None,
        description="ICD-10 code",
    )
    medications: list[Medication] = Field(
        ...,
        min_length=1,
        description="List of medications",
    )
    general_instructions: str | None = Field(
        default=None,
        description="General instructions for patient",
    )
    next_appointment: str | None = Field(
        default=None,
        description="Next appointment info",
    )


class UpdatePrescriptionRequest(BaseModel):
    """Request body for updating a prescription."""

    diagnosis: str | None = Field(default=None)
    diagnosis_code: str | None = Field(default=None)
    medications: list[Medication] | None = Field(default=None)
    general_instructions: str | None = Field(default=None)
    next_appointment: str | None = Field(default=None)
    patient: PatientInfo | None = Field(default=None)


class CreateFromSOAPRequest(BaseModel):
    """Request body for creating prescription from SOAP data."""

    session_id: str = Field(
        ...,
        description="Session ID containing SOAP data",
    )
    template_id: str = Field(
        default="default",
        description="Template ID to use",
    )
    patient: PatientInfo = Field(
        ...,
        description="Patient information",
    )
    physician: PhysicianInfo = Field(
        ...,
        description="Physician information",
    )


class CancelPrescriptionRequest(BaseModel):
    """Request body for cancelling a prescription."""

    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Cancellation reason",
    )


class PrescriptionResponse(BaseModel):
    """Standard response for prescription operations."""

    success: bool = Field(default=True)
    prescription: Prescription | None = Field(default=None)
    message: str | None = Field(default=None)


class TemplateListResponse(BaseModel):
    """Response for template list."""

    templates: list[PrescriptionTemplate]
    count: int


class PrescriptionListResponse(BaseModel):
    """Response for prescription list."""

    prescriptions: list[Prescription]
    count: int


# ============================================================================
# Template Endpoints
# ============================================================================


@router.get(
    "/templates",
    response_model=TemplateListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_templates(
    owner_id: str | None = Query(default=None, description="Filter by owner"),
    include_system: bool = Query(default=True, description="Include system templates"),
) -> TemplateListResponse:
    """List available prescription templates.

    Returns templates accessible to the user, including system templates
    and any custom templates owned by the specified owner.

    Args:
        owner_id: Optional owner filter
        include_system: Whether to include system templates

    Returns:
        List of templates
    """
    engine = get_template_engine()
    templates = engine.list_templates(owner_id=owner_id, include_system=include_system)

    logger.info("TEMPLATES_LISTED", count=len(templates), owner_id=owner_id)

    return TemplateListResponse(templates=templates, count=len(templates))


@router.get(
    "/templates/{template_id}",
    response_model=PrescriptionTemplate,
    status_code=status.HTTP_200_OK,
)
async def get_template(template_id: str) -> PrescriptionTemplate:
    """Get a specific template by ID.

    Args:
        template_id: Template identifier

    Returns:
        Template details

    Raises:
        404: Template not found
    """
    engine = get_template_engine()
    template = engine.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )

    return template


# ============================================================================
# Prescription CRUD Endpoints
# ============================================================================


@router.post(
    "",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prescription(
    request: CreatePrescriptionRequest,
) -> PrescriptionResponse:
    """Create a new prescription.

    Creates a draft prescription from the specified template
    with the provided patient, physician, and medication data.

    Args:
        request: Prescription creation request

    Returns:
        Created prescription

    Raises:
        400: Validation error
        404: Template not found
    """
    engine = get_template_engine()

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
) -> PrescriptionResponse:
    """Create a prescription from SOAP note data.

    Extracts diagnosis and medications from the session's SOAP data
    and creates a draft prescription.

    Args:
        request: Request with session ID and metadata

    Returns:
        Created prescription

    Raises:
        400: Invalid session or SOAP data
        404: Session not found
    """
    # Validate session ID
    validate_session_id(request.session_id)

    # Get SOAP data from storage
    from backend.src.fi_storage.infrastructure.hdf5.task_repository import get_soap_data

    try:
        soap_data = get_soap_data(request.session_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SOAP data not found for session: {request.session_id}",
        ) from e

    engine = get_template_engine()

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
    """Get a prescription by ID.

    Args:
        prescription_id: Prescription identifier

    Returns:
        Prescription details

    Raises:
        404: Prescription not found
    """
    engine = get_template_engine()
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
    """List prescriptions with optional filters.

    Args:
        session_id: Filter by session
        patient_id: Filter by patient
        physician_id: Filter by physician
        status_filter: Filter by status
        limit: Maximum results

    Returns:
        List of prescriptions
    """
    engine = get_template_engine()
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
    """Update a draft prescription.

    Only prescriptions in DRAFT status can be updated.

    Args:
        prescription_id: Prescription to update
        request: Fields to update

    Returns:
        Updated prescription

    Raises:
        400: Cannot update non-draft prescription
        404: Prescription not found
    """
    engine = get_template_engine()

    # Build updates dict from non-None fields
    updates: dict[str, Any] = {}
    for field, value in request.model_dump().items():
        if value is not None:
            updates[field] = value

    prescription = engine.update_prescription(prescription_id, updates)

    if not prescription:
        # Check if it exists but can't be updated
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


# ============================================================================
# Prescription Actions
# ============================================================================


@router.post(
    "/{prescription_id}/sign",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_200_OK,
)
async def sign_prescription(prescription_id: str) -> PrescriptionResponse:
    """Sign a prescription.

    Validates the prescription and marks it as signed.
    Generates a verification hash.

    Args:
        prescription_id: Prescription to sign

    Returns:
        Signed prescription

    Raises:
        400: Validation failed or already signed
        404: Prescription not found
    """
    engine = get_template_engine()

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
    """Cancel a prescription.

    Args:
        prescription_id: Prescription to cancel
        request: Cancellation reason

    Returns:
        Cancelled prescription

    Raises:
        400: Cannot cancel dispensed prescription
        404: Prescription not found
    """
    engine = get_template_engine()

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


# ============================================================================
# Export Endpoints
# ============================================================================


@router.get(
    "/{prescription_id}/export",
    status_code=status.HTTP_200_OK,
)
async def export_prescription(
    prescription_id: str,
    export_format: str = Query(default="text", description="Export format: text, json"),
) -> dict[str, Any]:
    """Export prescription to various formats.

    Args:
        prescription_id: Prescription to export
        export_format: Export format (text, json)

    Returns:
        Exported content

    Raises:
        404: Prescription not found
    """
    engine = get_template_engine()
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


# ============================================================================
# Medication Catalog Endpoints (FI-RX-004)
# ============================================================================


@router.get(
    "/catalog/search",
    status_code=status.HTTP_200_OK,
)
async def search_catalog(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    essential_only: bool = Query(default=False, description="Only essential medications"),
    otc_only: bool = Query(default=False, description="Only OTC medications"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
) -> dict[str, Any]:
    """Search medication catalog.

    Args:
        q: Search query (medication name, active ingredient, or brand name)
        category: Optional category filter
        essential_only: Only return cuadro básico medications
        otc_only: Only return over-the-counter medications
        limit: Maximum results to return

    Returns:
        Search results with relevance scores
    """
    from fi_prescription.models.catalog import DrugCategory
    from fi_prescription.services.catalog_service import (
        CatalogSearchRequest,
        catalog_service,
    )

    # Parse category if provided
    category_enum = None
    if category:
        try:
            category_enum = DrugCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {category}",
            )

    request = CatalogSearchRequest(
        query=q,
        category=category_enum,
        essential_only=essential_only,
        otc_only=otc_only,
        limit=limit,
    )

    response = catalog_service.search(request)

    logger.info(
        "CATALOG_SEARCH",
        query=q,
        results=response.total_matches,
    )

    return {
        "query": response.query,
        "total_matches": response.total_matches,
        "results": [
            {
                "medication": r.medication.model_dump(mode="json"),
                "score": r.score,
                "match_type": r.match_type,
            }
            for r in response.results
        ],
    }


@router.get(
    "/catalog/autocomplete",
    status_code=status.HTTP_200_OK,
)
async def autocomplete_medication(
    prefix: str = Query(..., min_length=2, max_length=50, description="Text prefix"),
    limit: int = Query(default=5, ge=1, le=20, description="Max suggestions"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
) -> dict[str, Any]:
    """Get autocomplete suggestions for medication names.

    Args:
        prefix: Text prefix to match
        limit: Maximum suggestions
        category: Optional category filter

    Returns:
        List of medication name suggestions
    """
    from fi_prescription.models.catalog import DrugCategory
    from fi_prescription.services.catalog_service import catalog_service

    # Parse category if provided
    category_enum = None
    if category:
        try:
            category_enum = DrugCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {category}",
            )

    suggestions = catalog_service.autocomplete(
        prefix=prefix,
        limit=limit,
        category=category_enum,
    )

    return {
        "prefix": prefix,
        "suggestions": suggestions,
    }


@router.get(
    "/catalog/{medication_id}",
    status_code=status.HTTP_200_OK,
)
async def get_catalog_medication(medication_id: str) -> dict[str, Any]:
    """Get medication details by ID.

    Args:
        medication_id: Medication identifier

    Returns:
        Medication details

    Raises:
        404: Medication not found
    """
    from fi_prescription.services.catalog_service import catalog_service

    medication = catalog_service.get_by_id(medication_id)

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication not found: {medication_id}",
        )

    return {"medication": medication.model_dump(mode="json")}


@router.get(
    "/catalog/categories/list",
    status_code=status.HTTP_200_OK,
)
async def list_categories() -> dict[str, Any]:
    """Get all available drug categories.

    Returns:
        List of categories with value and label
    """
    from fi_prescription.services.catalog_service import catalog_service

    categories = catalog_service.get_categories()
    return {"categories": categories}


@router.get(
    "/catalog/stats",
    status_code=status.HTTP_200_OK,
)
async def get_catalog_stats() -> dict[str, Any]:
    """Get medication catalog statistics.

    Returns:
        Catalog statistics
    """
    from fi_prescription.services.catalog_service import catalog_service

    stats = catalog_service.get_catalog_stats()
    return {"stats": stats}


@router.get(
    "/catalog/essential",
    status_code=status.HTTP_200_OK,
)
async def list_essential_medications(
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Get essential medications (cuadro básico).

    Args:
        limit: Maximum results

    Returns:
        List of essential medications
    """
    from fi_prescription.services.catalog_service import catalog_service

    medications = catalog_service.get_essential_medications(limit=limit)
    return {
        "count": len(medications),
        "medications": [m.model_dump(mode="json") for m in medications],
    }


@router.get(
    "/catalog/otc",
    status_code=status.HTTP_200_OK,
)
async def list_otc_medications(
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Get over-the-counter medications.

    Args:
        limit: Maximum results

    Returns:
        List of OTC medications
    """
    from fi_prescription.services.catalog_service import catalog_service

    medications = catalog_service.get_otc_medications(limit=limit)
    return {
        "count": len(medications),
        "medications": [m.model_dump(mode="json") for m in medications],
    }
