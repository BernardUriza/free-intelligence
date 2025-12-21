"""FI Receptionist Clinic Management API endpoints.

CRUD operations for clinic and doctor management.
Supports multi-tenant architecture with clinic isolation.

Author: Bernard Uriza Orozco
Created: 2025-11-21
Card: FI-CHECKIN-002
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.database import get_db_dependency
from backend.models.checkin_models import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    Clinic,
    Doctor,
)
from backend.src.fi_common.logging.logger import get_logger

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
    welcome_message: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default="#6366f1", max_length=20)
    logo_url: str | None = None
    checkin_qr_enabled: bool = True
    chat_enabled: bool = True
    payments_enabled: bool = False
    subscription_plan: str = Field(default="free", max_length=50)


class ClinicUpdate(BaseModel):
    """Schema for updating a clinic."""

    name: str | None = Field(default=None, max_length=200)
    specialty: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=50)
    welcome_message: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default=None, max_length=20)
    logo_url: str | None = None
    checkin_qr_enabled: bool | None = None
    chat_enabled: bool | None = None
    payments_enabled: bool | None = None
    subscription_plan: str | None = Field(default=None, max_length=50)


class ClinicResponse(BaseModel):
    """Clinic response schema."""

    clinic_id: str
    name: str
    specialty: str
    timezone: str
    welcome_message: str | None = None
    primary_color: str | None = None
    logo_url: str | None = None
    checkin_qr_enabled: bool
    chat_enabled: bool
    payments_enabled: bool
    subscription_plan: str
    is_active: bool
    created_at: str
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DoctorCreate(BaseModel):
    """Schema for creating a doctor."""

    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    especialidad: str | None = Field(default=None, max_length=100)
    cedula_profesional: str | None = Field(default=None, max_length=20)
    avg_consultation_minutes: int = Field(default=20, ge=5, le=180)


class DoctorUpdate(BaseModel):
    """Schema for updating a doctor."""

    nombre: str | None = Field(default=None, max_length=100)
    apellido: str | None = Field(default=None, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    especialidad: str | None = Field(default=None, max_length=100)
    cedula_profesional: str | None = Field(default=None, max_length=20)
    avg_consultation_minutes: int | None = Field(default=None, ge=5, le=180)
    work_start_time: str | None = Field(default=None, pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    work_end_time: str | None = Field(default=None, pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    is_active: bool | None = None


class DoctorResponse(BaseModel):
    """Doctor response schema."""

    doctor_id: str
    clinic_id: str
    nombre: str
    apellido: str
    display_name: str | None = None
    especialidad: str | None = None
    cedula_profesional: str | None = None
    avg_consultation_minutes: int
    work_start_time: str | None = None
    work_end_time: str | None = None
    is_active: bool
    created_at: str
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentCreate(BaseModel):
    """Schema for creating an appointment with auto-generated check-in code."""

    patient_id: str = Field(..., min_length=1)
    doctor_id: str = Field(..., min_length=1)
    scheduled_at: str = Field(..., description="ISO datetime")
    appointment_type: AppointmentType = AppointmentType.FOLLOW_UP
    estimated_duration: int = Field(default=20, ge=5, le=180)
    reason: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment."""

    scheduled_at: str | None = Field(default=None, description="ISO datetime")
    estimated_duration: int | None = Field(default=None, ge=5, le=180)
    doctor_id: str | None = Field(default=None, min_length=1)
    appointment_type: AppointmentType | None = None
    status: AppointmentStatus | None = None
    reason: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)


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
    reason: str | None = None
    notes: str | None = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


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

    clinic.updated_at = datetime.now(UTC)
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
    clinic.updated_at = datetime.now(UTC)
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

    doctor.updated_at = datetime.now(UTC)
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
    doctor.updated_at = datetime.now(UTC)
    db.commit()

    logger.info("DOCTOR_DELETED", doctor_id=doctor_id, clinic_id=clinic_id)


# =============================================================================
# APPOINTMENT ENDPOINTS (with auto check-in code)
# =============================================================================


@router.post("/{clinic_id}/appointments", response_model=AppointmentResponse, status_code=201)
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
                Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
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
    date: str | None = None,
    doctor_id: str | None = None,
    status: str | None = None,
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
            # FIXED: Use UTC timezone to match database timestamps
            start_of_day = datetime.combine(filter_date, datetime.min.time(), tzinfo=UTC)
            end_of_day = start_of_day + timedelta(days=1)
            query = query.filter(
                Appointment.scheduled_at >= start_of_day,
                Appointment.scheduled_at < end_of_day,
            )
            logger.debug(
                "DATE_FILTER",
                date=date,
                start=start_of_day.isoformat(),
                end=end_of_day.isoformat(),
            )
        except ValueError as e:
            logger.warning("INVALID_DATE_FORMAT", date=date, error=str(e))
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


@router.patch("/{clinic_id}/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    clinic_id: str,
    appointment_id: str,
    request: AppointmentUpdate,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> AppointmentResponse:
    """Update an appointment (drag/drop, resize, edit)."""
    # Fetch appointment
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.appointment_id == appointment_id,
            Appointment.clinic_id == clinic_id,
            Appointment.is_deleted.is_(False),
        )
        .first()
    )

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Prevent editing completed/cancelled appointments
    if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update appointment with status {appointment.status.value}",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)

    # Validate doctor belongs to clinic if doctor_id is being updated
    if "doctor_id" in update_data:
        doctor = (
            db.query(Doctor)
            .filter(
                Doctor.doctor_id == update_data["doctor_id"],
                Doctor.clinic_id == clinic_id,
                Doctor.is_active.is_(True),
            )
            .first()
        )
        if not doctor:
            raise HTTPException(
                status_code=400, detail="Doctor not found or not active in this clinic"
            )

    # Parse scheduled_at if provided
    if "scheduled_at" in update_data:
        try:
            scheduled_at = datetime.fromisoformat(update_data["scheduled_at"])
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=UTC)
            update_data["scheduled_at"] = scheduled_at

            # Regenerate checkin code expiration (2 hours after new scheduled time)
            appointment.checkin_code_expires_at = scheduled_at + timedelta(hours=2)
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid scheduled_at format: {e!s}"
            ) from e

    # Apply updates
    for field, value in update_data.items():
        setattr(appointment, field, value)

    appointment.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(appointment)

    logger.info(
        "APPOINTMENT_UPDATED",
        appointment_id=str(appointment.appointment_id),
        clinic_id=clinic_id,
        updated_fields=list(update_data.keys()),
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


@router.delete("/{clinic_id}/appointments/{appointment_id}", status_code=204)
def delete_appointment(
    clinic_id: str,
    appointment_id: str,
    db: Session = Depends(get_db_dependency),  # noqa: B008
) -> None:
    """Soft delete an appointment."""
    # Fetch appointment
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.appointment_id == appointment_id,
            Appointment.clinic_id == clinic_id,
            Appointment.is_deleted.is_(False),
        )
        .first()
    )

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Prevent deleting completed appointments
    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot delete completed appointments")

    # Soft delete
    appointment.is_deleted = True
    appointment.updated_at = datetime.now(UTC)
    db.commit()

    logger.info(
        "APPOINTMENT_DELETED",
        appointment_id=str(appointment.appointment_id),
        clinic_id=clinic_id,
    )
