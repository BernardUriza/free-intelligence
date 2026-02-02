"""Patient management API endpoints.

CRUD operations for patient records with PostgreSQL persistence.
Public API - accessible to authenticated users.

Author: Bernard Uriza Orozco
Created: 2025-11-17
Card: FI-DATA-DB-001
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
# PEP 585: use built-in list

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.database import get_db_dependency
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.models.db_models import Patient
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

logger = get_logger(__name__)

router = APIRouter(prefix="/patients", tags=["Patients"])


# ============================================================================
# Enums
# ============================================================================


class GenderEnum(str, Enum):
    """Patient gender options - matches database enum."""

    MASCULINO = "MASCULINO"
    FEMENINO = "FEMENINO"
    OTRO = "OTRO"
    NO_ESPECIFICADO = "NO_ESPECIFICADO"


# ============================================================================
# Pydantic Schemas
# ============================================================================


class PatientCreate(BaseModel):
    """Schema for creating a new patient."""

    nombre: str = Field(..., min_length=1, max_length=100, description="First name(s)")
    apellido: str = Field(..., min_length=1, max_length=100, description="Last name(s)")
    fecha_nacimiento: datetime = Field(..., description="Date of birth (ISO 8601)")
    genero: GenderEnum | None = Field(
        None, description="Gender (MASCULINO, FEMENINO, OTRO, NO_ESPECIFICADO)"
    )
    curp: str | None = Field(None, min_length=18, max_length=18, description="CURP (18 chars)")


class PatientUpdate(BaseModel):
    """Schema for updating patient data."""

    nombre: str | None = Field(None, min_length=1, max_length=100)
    apellido: str | None = Field(None, min_length=1, max_length=100)
    fecha_nacimiento: datetime | None = None
    genero: GenderEnum | None = None
    curp: str | None = Field(None, min_length=18, max_length=18)


class PatientResponse(BaseModel):
    """Schema for patient API responses."""

    patient_id: str
    nombre: str
    apellido: str
    fecha_nacimiento: str
    genero: str | None
    curp: str | None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CRUD Endpoints
# ============================================================================


class CurpValidationRequest(BaseModel):
    """Schema for CURP validation request."""

    curp: str = Field(..., min_length=18, max_length=18, description="CURP to validate")
    exclude_patient_id: str | None = Field(None, description="Patient ID to exclude (for updates)")


class CurpValidationResponse(BaseModel):
    """Schema for CURP validation response."""

    valid: bool = Field(..., description="Whether CURP format is valid")
    available: bool = Field(..., description="Whether CURP is available (not in use)")
    message: str | None = Field(None, description="Error or info message")


@router.post("/validate-curp", response_model=CurpValidationResponse)
def validate_curp(
    request: CurpValidationRequest,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
    """Validate CURP format and availability.

    Checks:
    1. CURP format is valid (18 chars, matches pattern)
    2. CURP is not already in use by another patient

    Args:
        request: CURP validation request
        db: Database session (injected)

    Returns:
        Validation result with availability status
    """
    # CURP format validation
    curp_pattern = r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$"
    if not re.match(curp_pattern, request.curp):
        return CurpValidationResponse(
            valid=False,
            available=False,
            message="Formato de CURP inválido. Debe tener 18 caracteres alfanuméricos.",
        )

    # Check availability in database
    try:
        query = db.query(Patient).filter(Patient.curp == request.curp)

        # Exclude specific patient (for updates)
        if request.exclude_patient_id:
            query = query.filter(Patient.patient_id != request.exclude_patient_id)

        existing = query.first()

        if existing:
            logger.info("CURP_VALIDATION_DUPLICATE", curp_prefix=request.curp[:4])
            return CurpValidationResponse(
                valid=True,
                available=False,
                message="Este CURP ya está registrado para otro paciente.",
            )

        logger.info("CURP_VALIDATION_OK", curp_prefix=request.curp[:4])
        return CurpValidationResponse(valid=True, available=True, message=None)

    except Exception as e:
        # Audit failure for compliance tracking
        audit_service.log_action(
            action="curp_validated",
            user_id=current_user.id,
            resource=request.curp[:4] + "****",  # Partial CURP for privacy
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        # On error, return valid=True but available=True to not block form
        # The final create/update will catch duplicates
        return CurpValidationResponse(
            valid=True,
            available=True,
            message="No se pudo verificar disponibilidad. Se validará al guardar.",
        )


@router.post("/", response_model=PatientResponse, status_code=201)
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
    """Create a new patient record.

    Args:
        patient: Patient data
        db: Database session (injected)

    Returns:
        Created patient with assigned ID

    Raises:
        400: CURP already exists
        500: Database error
    """
    try:
        # Check for duplicate CURP
        if patient.curp:
            existing = db.query(Patient).filter(Patient.curp == patient.curp).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"CURP {patient.curp} already exists")

        # Create patient
        db_patient = Patient(
            nombre=patient.nombre,
            apellido=patient.apellido,
            fecha_nacimiento=patient.fecha_nacimiento,
            genero=patient.genero.value if patient.genero else None,
            curp=patient.curp,
        )
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)

        audit_service.log_action(
            action="patient_created",
            user_id=current_user.id,
            resource=str(db_patient.patient_id),
            result="success",
            clinic_id=None,  # TODO: Add clinic_id filtering (Phase 2)
        )
        return db_patient.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        # Audit failure for compliance tracking
        audit_service.log_action(
            action="patient_created",
            user_id=current_user.id,
            resource="unknown",  # Patient ID not available on failure
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(status_code=500, detail="Failed to create patient")


@router.get("/", response_model=list[PatientResponse])
def list_patients(
    search: str | None = Query(None, description="Search by nombre or apellido"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
    """List patients with optional search and pagination.

    Args:
        search: Search query (nombre or apellido)
        limit: Maximum results (1-100)
        offset: Skip N results
        db: Database session (injected)

    Returns:
        List of patients matching criteria
    """
    try:
        query = db.query(Patient)

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Patient.nombre.ilike(search_pattern)) | (Patient.apellido.ilike(search_pattern))
            )

        # Apply pagination
        patients = (
            query.order_by(Patient.apellido, Patient.nombre).offset(offset).limit(limit).all()
        )

        logger.info("PATIENTS_LISTED", count=len(patients), search=search)
        return [p.to_dict() for p in patients]

    except Exception as e:
        # Audit failure for compliance tracking
        audit_service.log_action(
            action="patients_listed",
            user_id=current_user.id,
            resource="list",
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__, "search": search},
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to list patients: {type(e).__name__}: {e!s}"
        )


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
    """Get patient by ID.

    Args:
        patient_id: Patient UUID
        db: Database session (injected)

    Returns:
        Patient record

    Raises:
        404: Patient not found
    """
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

        logger.info("PATIENT_RETRIEVED", patient_id=patient_id)
        return patient.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        # Audit failure for compliance tracking
        audit_service.log_action(
            action="patient_retrieved",
            user_id=current_user.id,
            resource=patient_id,
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve patient")


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: str,
    updates: PatientUpdate,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
    """Update patient record.

    Args:
        patient_id: Patient UUID
        updates: Fields to update
        db: Database session (injected)

    Returns:
        Updated patient record

    Raises:
        404: Patient not found
        400: CURP conflict
    """
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

        # Check CURP conflict
        if updates.curp and updates.curp != patient.curp:
            existing = db.query(Patient).filter(Patient.curp == updates.curp).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"CURP {updates.curp} already exists")

        # Apply updates
        update_data = updates.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            # Convert enum to string value for database
            if key == "genero" and value is not None:
                value = value.value if hasattr(value, "value") else value
            setattr(patient, key, value)

        db.commit()
        db.refresh(patient)

        audit_service.log_action(
            action="patient_updated",
            user_id=current_user.id,
            resource=patient_id,
            result="success",
            clinic_id=None,  # TODO: Add clinic_id filtering (Phase 2)
            details={"fields_updated": list(update_data.keys())}
        )
        return patient.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        # Audit failure for compliance tracking
        audit_service.log_action(
            action="patient_updated",
            user_id=current_user.id,
            resource=patient_id,
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(status_code=500, detail="Failed to update patient")


@router.delete("/{patient_id}", status_code=204)
def delete_patient(
    patient_id: str,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
    """Delete patient record.

    Args:
        patient_id: Patient UUID
        db: Database session (injected)

    Raises:
        404: Patient not found
    """
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

        db.delete(patient)
        db.commit()

        audit_service.log_action(
            action="patient_deleted",
            user_id=current_user.id,
            resource=patient_id,
            result="success",
            clinic_id=None,  # TODO: Add clinic_id filtering (Phase 2)
        )
        return None

    except HTTPException:
        raise
    except Exception as e:
        # Audit failure for compliance tracking
        audit_service.log_action(
            action="patient_deleted",
            user_id=current_user.id,
            resource=patient_id,
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(status_code=500, detail="Failed to delete patient")
