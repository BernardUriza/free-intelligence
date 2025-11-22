"""FI Receptionist Clinic Management API endpoints.

CRUD operations for clinic and doctor management.
Supports multi-tenant architecture with clinic isolation.

Author: Bernard Uriza Orozco
Created: 2025-11-21
Card: FI-CHECKIN-002
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db_dependency
from backend.logger import get_logger
from backend.models.checkin_models import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    Clinic,
    Doctor,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/clinics", tags=["Clinics"])


# =============================================================================
# SCHEMAS
# =============================================================================


class ClinicCreate(BaseModel):
    """Schema for creating a new clinic."""

    name: str = Field(..., min_length=1, max_length=200)
    specialty: str = Field(default="general", max_length=100)
    timezone: str = Field(default="America/Mexico_City", max_length=50)
    welcome_message: Optional[str] = Field(default=None, max_length=500)
    primary_color: Optional[str] = Field(default="#6366f1", max_length=20)
    logo_url: Optional[str] = None
    checkin_qr_enabled: bool = True
    chat_enabled: bool = True
    payments_enabled: bool = False
    subscription_plan: str = Field(default="free", max_length=50)


class ClinicUpdate(BaseModel):
    """Schema for updating a clinic."""

    name: Optional[str] = Field(default=None, max_length=200)
    specialty: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=50)
    welcome_message: Optional[str] = Field(default=None, max_length=500)
    primary_color: Optional[str] = Field(default=None, max_length=20)
    logo_url: Optional[str] = None
    checkin_qr_enabled: Optional[bool] = None
    chat_enabled: Optional[bool] = None
    payments_enabled: Optional[bool] = None
    subscription_plan: Optional[str] = Field(default=None, max_length=50)


class ClinicResponse(BaseModel):
    """Clinic response schema."""

    clinic_id: str
    name: str
    specialty: str
    timezone: str
    welcome_message: Optional[str] = None
    primary_color: Optional[str] = None
    logo_url: Optional[str] = None
    checkin_qr_enabled: bool
    chat_enabled: bool
    payments_enabled: bool
    subscription_plan: str
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class DoctorCreate(BaseModel):
    """Schema for creating a doctor."""

    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = Field(default=None, max_length=100)
    especialidad: Optional[str] = Field(default=None, max_length=100)
    cedula_profesional: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)
    avg_consultation_minutes: int = Field(default=20, ge=5, le=180)


class DoctorUpdate(BaseModel):
    """Schema for updating a doctor."""

    nombre: Optional[str] = Field(default=None, max_length=100)
    apellido: Optional[str] = Field(default=None, max_length=100)
    display_name: Optional[str] = Field(default=None, max_length=100)
    especialidad: Optional[str] = Field(default=None, max_length=100)
    cedula_profesional: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)
    avg_consultation_minutes: Optional[int] = Field(default=None, ge=5, le=180)
    is_active: Optional[bool] = None


class DoctorResponse(BaseModel):
    """Doctor response schema."""

    doctor_id: str
    clinic_id: str
    nombre: str
    apellido: str
    display_name: Optional[str] = None
    especialidad: Optional[str] = None
    cedula_profesional: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avg_consultation_minutes: int
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class AppointmentCreate(BaseModel):
    """Schema for creating an appointment with auto-generated check-in code."""

    patient_id: str = Field(..., min_length=1)
    doctor_id: str = Field(..., min_length=1)
    scheduled_at: str = Field(..., description="ISO datetime")
    appointment_type: AppointmentType = AppointmentType.FOLLOW_UP
    estimated_duration: int = Field(default=20, ge=5, le=180)
    reason: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=1000)


class AppointmentResponse(BaseModel):
    """Appointment response with check-in code."""

    appointment_id: str
    clinic_id: str
    patient_id: str
    doctor_id: str
    scheduled_at: str
    estimated_duration: int
    appointment_type: str
    status: str
    checkin_code: str
    checkin_code_expires_at: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class ClinicListResponse(BaseModel):
    """Response for clinic list."""

    clinics: list[ClinicResponse]
    total: int


class DoctorListResponse(BaseModel):
    """Response for doctor list."""

    doctors: list[DoctorResponse]
    total: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def generate_checkin_code() -> str:
    """Generate a 6-digit check-in code."""
    return "".join([str(secrets.randbelow(10)) for _ in range(6)])


def model_to_response(model, response_class):
    """Convert SQLAlchemy model to Pydantic response."""
    data = {}
    for field in response_class.model_fields:
        value = getattr(model, field, None)
        if isinstance(value, datetime):
            value = value.isoformat()
        data[field] = value
    return response_class(**data)


# =============================================================================
# CLINIC ENDPOINTS
# =============================================================================


@router.get("", response_model=ClinicListResponse)
def list_clinics(
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> ClinicListResponse:
    """List all clinics with pagination."""
    query = db.query(Clinic)
    if active_only:
        query = query.filter(Clinic.is_active.is_(True))

    total = query.count()
    clinics = query.offset(skip).limit(limit).all()

    return ClinicListResponse(
        clinics=[model_to_response(c, ClinicResponse) for c in clinics],
        total=total,
    )


@router.get("/{clinic_id}", response_model=ClinicResponse)
def get_clinic(
    clinic_id: str,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> ClinicResponse:
    """Get a clinic by ID."""
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return model_to_response(clinic, ClinicResponse)


@router.post("", response_model=ClinicResponse, status_code=201)
def create_clinic(
    request: ClinicCreate,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> ClinicResponse:
    """Create a new clinic."""
    clinic = Clinic(**request.model_dump())
    db.add(clinic)
    db.commit()
    db.refresh(clinic)

    logger.info("CLINIC_CREATED", clinic_id=str(clinic.clinic_id), name=clinic.name)
    return model_to_response(clinic, ClinicResponse)


@router.patch("/{clinic_id}", response_model=ClinicResponse)
def update_clinic(
    clinic_id: str,
    request: ClinicUpdate,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> ClinicResponse:
    """Update a clinic."""
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clinic, field, value)

    clinic.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(clinic)

    logger.info("CLINIC_UPDATED", clinic_id=clinic_id)
    return model_to_response(clinic, ClinicResponse)


@router.delete("/{clinic_id}", status_code=204)
def delete_clinic(
    clinic_id: str,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> None:
    """Soft delete a clinic (set is_active=False)."""
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    clinic.is_active = False
    clinic.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info("CLINIC_DELETED", clinic_id=clinic_id)


# =============================================================================
# DOCTOR ENDPOINTS
# =============================================================================


@router.get("/{clinic_id}/doctors", response_model=DoctorListResponse)
def list_doctors(
    clinic_id: str,
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> DoctorListResponse:
    """List doctors for a clinic."""
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
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> DoctorResponse:
    """Get a doctor by ID."""
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
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> DoctorResponse:
    """Create a new doctor for a clinic."""
    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

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
    )
    return model_to_response(doctor, DoctorResponse)


@router.patch("/{clinic_id}/doctors/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    clinic_id: str,
    doctor_id: str,
    request: DoctorUpdate,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> DoctorResponse:
    """Update a doctor."""
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

    logger.info("DOCTOR_UPDATED", doctor_id=doctor_id, clinic_id=clinic_id)
    return model_to_response(doctor, DoctorResponse)


@router.delete("/{clinic_id}/doctors/{doctor_id}", status_code=204)
def delete_doctor(
    clinic_id: str,
    doctor_id: str,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> None:
    """Soft delete a doctor."""
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

    logger.info("DOCTOR_DELETED", doctor_id=doctor_id, clinic_id=clinic_id)


# =============================================================================
# APPOINTMENT ENDPOINTS (with auto check-in code)
# =============================================================================


@router.post(
    "/{clinic_id}/appointments", response_model=AppointmentResponse, status_code=201
)
def create_appointment(
    clinic_id: str,
    request: AppointmentCreate,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> AppointmentResponse:
    """
    Create a new appointment with auto-generated check-in code.

    The check-in code is valid from midnight of the appointment day
    until 2 hours after the scheduled time.
    """
    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Verify doctor belongs to clinic
    doctor = (
        db.query(Doctor)
        .filter(Doctor.clinic_id == clinic_id, Doctor.doctor_id == request.doctor_id)
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found in this clinic")

    # Parse scheduled_at
    try:
        scheduled_at = datetime.fromisoformat(request.scheduled_at.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail="Invalid datetime format. Use ISO format."
        ) from e

    # Generate unique check-in code (retry if collision)
    checkin_code = generate_checkin_code()
    attempts = 0
    while attempts < 10:
        existing = (
            db.query(Appointment)
            .filter(
                Appointment.clinic_id == clinic_id,
                Appointment.checkin_code == checkin_code,
                Appointment.status.in_(
                    [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
                ),
            )
            .first()
        )
        if not existing:
            break
        checkin_code = generate_checkin_code()
        attempts += 1

    # Code expires 2 hours after scheduled time
    checkin_code_expires_at = scheduled_at + timedelta(hours=2)

    appointment = Appointment(
        clinic_id=clinic_id,
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        scheduled_at=scheduled_at,
        appointment_type=request.appointment_type,
        estimated_duration=request.estimated_duration,
        status=AppointmentStatus.SCHEDULED,
        checkin_code=checkin_code,
        checkin_code_expires_at=checkin_code_expires_at,
        reason=request.reason,
        notes=request.notes,
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    logger.info(
        "APPOINTMENT_CREATED",
        appointment_id=str(appointment.appointment_id),
        clinic_id=clinic_id,
        checkin_code=checkin_code,
        scheduled_at=scheduled_at.isoformat(),
    )

    return AppointmentResponse(
        appointment_id=str(appointment.appointment_id),
        clinic_id=str(appointment.clinic_id),
        patient_id=str(appointment.patient_id),
        doctor_id=str(appointment.doctor_id),
        scheduled_at=appointment.scheduled_at.isoformat(),
        estimated_duration=appointment.estimated_duration,
        appointment_type=appointment.appointment_type.value,
        status=appointment.status.value,
        checkin_code=appointment.checkin_code,
        checkin_code_expires_at=appointment.checkin_code_expires_at.isoformat(),
        reason=appointment.reason,
        notes=appointment.notes,
        created_at=appointment.created_at.isoformat(),
    )


@router.get("/{clinic_id}/appointments", response_model=dict)
def list_appointments(
    clinic_id: str,
    date: Optional[str] = None,
    doctor_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> dict:
    """List appointments for a clinic with filters."""
    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    query = db.query(Appointment).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.is_deleted.is_(False),
    )

    # Apply filters
    if date:
        try:
            filter_date = datetime.fromisoformat(date).date()
            query = query.filter(
                Appointment.scheduled_at >= datetime.combine(
                    filter_date, datetime.min.time()
                ),
                Appointment.scheduled_at
                < datetime.combine(filter_date, datetime.min.time()) + timedelta(days=1),
            )
        except ValueError:
            pass  # Ignore invalid date

    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)

    if status:
        try:
            status_enum = AppointmentStatus(status)
            query = query.filter(Appointment.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status

    total = query.count()
    appointments = query.order_by(Appointment.scheduled_at).offset(skip).limit(limit).all()

    return {
        "appointments": [
            AppointmentResponse(
                appointment_id=str(a.appointment_id),
                clinic_id=str(a.clinic_id),
                patient_id=str(a.patient_id),
                doctor_id=str(a.doctor_id),
                scheduled_at=a.scheduled_at.isoformat(),
                estimated_duration=a.estimated_duration,
                appointment_type=a.appointment_type.value,
                status=a.status.value,
                checkin_code=a.checkin_code,
                checkin_code_expires_at=a.checkin_code_expires_at.isoformat(),
                reason=a.reason,
                notes=a.notes,
                created_at=a.created_at.isoformat(),
            )
            for a in appointments
        ],
        "total": total,
    }
