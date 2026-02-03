"""Patient CRUD Endpoints.

POST   /patients/validate-curp - Validate CURP format and availability
POST   /patients - Create patient
GET    /patients - List patients
GET    /patients/{id} - Get patient
PUT    /patients/{id} - Update patient
DELETE /patients/{id} - Delete patient

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
Card: FI-DATA-DB-001
"""

from __future__ import annotations

import re

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.database import get_db_dependency
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.models.db_models import Patient
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .models import (
    CurpValidationRequest,
    CurpValidationResponse,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Patients"])


# =============================================================================
# CURP Validation
# =============================================================================


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
        return CurpValidationResponse(
            valid=True,
            available=True,
            message="No se pudo verificar disponibilidad. Se validará al guardar.",
        )


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.post("/", response_model=PatientResponse, status_code=201)
def create_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
    """Create a new patient record."""
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
            clinic_id=None,
        )
        return db_patient.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="patient_created",
            user_id=current_user.id,
            resource="unknown",
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
    """List patients with optional search and pagination."""
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
    """Get patient by ID."""
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

        logger.info("PATIENT_RETRIEVED", patient_id=patient_id)
        return patient.to_dict()

    except HTTPException:
        raise
    except Exception as e:
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
    """Update patient record."""
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
            clinic_id=None,
            details={"fields_updated": list(update_data.keys())},
        )
        return patient.to_dict()

    except HTTPException:
        raise
    except Exception as e:
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
    """Delete patient record."""
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
            clinic_id=None,
        )
        return None

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="patient_deleted",
            user_id=current_user.id,
            resource=patient_id,
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(status_code=500, detail="Failed to delete patient")
