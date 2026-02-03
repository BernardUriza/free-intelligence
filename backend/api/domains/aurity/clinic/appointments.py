"""Appointment Endpoints.

POST   /clinics/{id}/appointments - Create appointment
GET    /clinics/{id}/appointments - List appointments
PATCH  /clinics/{id}/appointments/{id} - Update appointment
DELETE /clinics/{id}/appointments/{id} - Delete appointment

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.database import get_db_dependency
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.infrastructure.auth.utils import validate_clinic_access
from backend.models.checkin_models import (
    Appointment,
    AppointmentStatus,
    Clinic,
    Doctor,
)
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .helpers import generate_checkin_code
from .models import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdate,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Clinics - Appointments"])


def _appointment_to_response(appointment: Appointment) -> AppointmentResponse:
    """Convert Appointment model to response."""
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


@router.post(
    "/{clinic_id}/appointments", response_model=AppointmentResponse, status_code=201
)
def create_appointment(
    clinic_id: str,
    request: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> AppointmentResponse:
    """Create a new appointment with auto-generated check-in code.

    The check-in code is valid from midnight of the appointment day
    until 2 hours after the scheduled time.
    """
    validate_clinic_access(clinic_id, current_user, action="create appointment")

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

    return _appointment_to_response(appointment)


@router.get("/{clinic_id}/appointments", response_model=AppointmentListResponse)
def list_appointments(
    clinic_id: str,
    date: str | None = None,
    doctor_id: str | None = None,
    appt_status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> AppointmentListResponse:
    """List appointments for a clinic with filters."""
    validate_clinic_access(clinic_id, current_user)

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
            # Use UTC timezone to match database timestamps
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

    if appt_status:
        try:
            status_enum = AppointmentStatus(appt_status)
            query = query.filter(Appointment.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status

    total = query.count()
    appointments = query.order_by(Appointment.scheduled_at).offset(skip).limit(limit).all()

    return AppointmentListResponse(
        appointments=[_appointment_to_response(a) for a in appointments],
        total=total,
    )


@router.patch(
    "/{clinic_id}/appointments/{appointment_id}", response_model=AppointmentResponse
)
def update_appointment(
    clinic_id: str,
    appointment_id: str,
    request: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> AppointmentResponse:
    """Update an appointment (drag/drop, resize, edit)."""
    validate_clinic_access(clinic_id, current_user, action="update appointment")

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

    return _appointment_to_response(appointment)


@router.delete("/{clinic_id}/appointments/{appointment_id}", status_code=204)
def delete_appointment(
    clinic_id: str,
    appointment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> None:
    """Soft delete an appointment."""
    validate_clinic_access(clinic_id, current_user, action="delete appointment")

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
