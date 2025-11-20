"""Patient management API endpoints.

CRUD operations for patient records with PostgreSQL persistence.
Public API - accessible to authenticated users.

Author: Bernard Uriza Orozco
Created: 2025-11-17
Card: FI-DATA-DB-001
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db_dependency
from backend.logger import get_logger
from backend.models.db_models import Patient

logger = get_logger(__name__)

router = APIRouter(prefix="/patients", tags=["Patients"])


# ============================================================================
# Pydantic Schemas
# ============================================================================


class PatientCreate(BaseModel):
    """Schema for creating a new patient."""

    nombre: str = Field(..., min_length=1, max_length=100, description="First name(s)")
    apellido: str = Field(..., min_length=1, max_length=100, description="Last name(s)")
    fecha_nacimiento: datetime = Field(..., description="Date of birth (ISO 8601)")
    curp: str | None = Field(None, min_length=18, max_length=18, description="CURP (18 chars)")


class PatientUpdate(BaseModel):
    """Schema for updating patient data."""

    nombre: str | None = Field(None, min_length=1, max_length=100)
    apellido: str | None = Field(None, min_length=1, max_length=100)
    fecha_nacimiento: datetime | None = None
    curp: str | None = Field(None, min_length=18, max_length=18)


class PatientResponse(BaseModel):
    """Schema for patient API responses."""

    patient_id: str
    nombre: str
    apellido: str
    fecha_nacimiento: str
    curp: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ============================================================================
# CRUD Endpoints
# ============================================================================


@router.post("/", response_model=PatientResponse, status_code=201)
def create_patient(patient: PatientCreate, db: Session = Depends(get_db_dependency)):
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
            curp=patient.curp,
        )
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)

        logger.info("PATIENT_CREATED", patient_id=db_patient.patient_id, nombre=patient.nombre)
        return db_patient.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PATIENT_CREATE_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create patient")


@router.get("/", response_model=List[PatientResponse])
def list_patients(
    search: str | None = Query(None, description="Search by nombre or apellido"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    db: Session = Depends(get_db_dependency),
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
        logger.error("PATIENTS_LIST_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list patients")


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str, db: Session = Depends(get_db_dependency)):
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
        logger.error("PATIENT_GET_FAILED", error=str(e), patient_id=patient_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve patient")


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: str, updates: PatientUpdate, db: Session = Depends(get_db_dependency)
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
        update_data = updates.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(patient, key, value)

        db.commit()
        db.refresh(patient)

        logger.info("PATIENT_UPDATED", patient_id=patient_id, fields=list(update_data.keys()))
        return patient.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PATIENT_UPDATE_FAILED", error=str(e), patient_id=patient_id)
        raise HTTPException(status_code=500, detail="Failed to update patient")


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: str, db: Session = Depends(get_db_dependency)):
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

        logger.info("PATIENT_DELETED", patient_id=patient_id)
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PATIENT_DELETE_FAILED", error=str(e), patient_id=patient_id)
        raise HTTPException(status_code=500, detail="Failed to delete patient")
