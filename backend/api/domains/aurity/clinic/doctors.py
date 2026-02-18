"""Doctor Endpoints.

GET    /clinics/{id}/doctors - List doctors
GET    /clinics/{id}/doctors/{id} - Get doctor
POST   /clinics/{id}/doctors - Create doctor
PATCH  /clinics/{id}/doctors/{id} - Update doctor
DELETE /clinics/{id}/doctors/{id} - Delete doctor

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.api.audit.dependencies import get_audit_service
from backend.database import get_db_dependency
from backend.domain.clinic.services.doctor_limits import validate_can_add_doctor
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.infrastructure.auth.utils import validate_clinic_access
from backend.models.checkin_models import Clinic, Doctor
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .helpers import model_to_response
from .models import DoctorCreate, DoctorListResponse, DoctorResponse, DoctorUpdate

logger = get_logger(__name__)

router = APIRouter(tags=["Clinics - Doctors"])


@router.get("/{clinic_id}/doctors", response_model=DoctorListResponse)
def list_doctors(
    clinic_id: str,
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> DoctorListResponse:
    """List doctors for a clinic."""
    validate_clinic_access(clinic_id, current_user)

    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    query = db.query(Doctor).filter(Doctor.clinic_id == clinic_id)
    if active_only:
        query = query.filter(Doctor.is_active.is_(True))

    total = query.count()
    doctors = query.offset(skip).limit(limit).all()

    return DoctorListResponse(
        doctors=[model_to_response(d, DoctorResponse) for d in doctors],
        total=total,
    )


@router.get("/{clinic_id}/doctors/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    clinic_id: str,
    doctor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> DoctorResponse:
    """Get a doctor by ID."""
    validate_clinic_access(clinic_id, current_user)

    doctor = (
        db.query(Doctor)
        .filter(Doctor.clinic_id == clinic_id, Doctor.doctor_id == doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return model_to_response(doctor, DoctorResponse)


@router.post("/{clinic_id}/doctors", response_model=DoctorResponse, status_code=201)
def create_doctor(
    clinic_id: str,
    request: DoctorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> DoctorResponse:
    """Create a new doctor for a clinic."""
    validate_clinic_access(clinic_id, current_user, action="create doctor")

    # Verify clinic exists (with subscription for limit validation)
    clinic = (
        db.query(Clinic)
        .options(joinedload(Clinic.subscription))
        .filter(Clinic.clinic_id == clinic_id)
        .first()
    )
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Validate doctor limit (raises 403 if exceeded)
    validate_can_add_doctor(db, clinic)

    doctor = Doctor(clinic_id=clinic_id, **request.model_dump())

    # Auto-generate display_name if not provided
    if not doctor.display_name:
        doctor.display_name = f"Dr. {doctor.apellido}"

    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    logger.info(
        "DOCTOR_CREATED",
        doctor_id=str(doctor.doctor_id),
        clinic_id=clinic_id,
        name=doctor.display_name,
        user_id=current_user.id,
    )
    return model_to_response(doctor, DoctorResponse)


@router.patch("/{clinic_id}/doctors/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    clinic_id: str,
    doctor_id: str,
    request: DoctorUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
    audit_service=Depends(get_audit_service),
) -> DoctorResponse:
    """Update a doctor."""
    validate_clinic_access(clinic_id, current_user, action="update doctor")

    doctor = (
        db.query(Doctor)
        .filter(Doctor.clinic_id == clinic_id, Doctor.doctor_id == doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doctor, field, value)

    doctor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doctor)

    audit_service.log_action(
        action="doctor_updated",
        user_id=current_user.id,
        clinic_id=current_user.clinic_id or clinic_id,
        resource=doctor_id,
        result="success",
        metadata={"clinic_id": clinic_id},
    )
    return model_to_response(doctor, DoctorResponse)


@router.delete("/{clinic_id}/doctors/{doctor_id}", status_code=204)
def delete_doctor(
    clinic_id: str,
    doctor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
    audit_service=Depends(get_audit_service),
) -> None:
    """Soft delete a doctor."""
    validate_clinic_access(clinic_id, current_user, action="delete doctor")

    doctor = (
        db.query(Doctor)
        .filter(Doctor.clinic_id == clinic_id, Doctor.doctor_id == doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctor.is_active = False
    doctor.updated_at = datetime.now(timezone.utc)
    db.commit()

    audit_service.log_action(
        action="doctor_deleted",
        user_id=current_user.id,
        clinic_id=current_user.clinic_id or clinic_id,
        resource=doctor_id,
        result="success",
        metadata={"clinic_id": clinic_id},
    )
