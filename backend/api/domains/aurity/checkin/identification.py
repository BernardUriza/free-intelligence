"""Patient Identification Endpoints.

POST /checkin/identify/code - Identify by 6-digit code
POST /checkin/identify/curp - Identify by CURP (Mexican ID)
POST /checkin/identify/name - Identify by name + DOB

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.database import get_db_dependency
from backend.models.checkin_models import (
    Appointment,
    AppointmentStatus,
    CheckinSession,
    PendingActionStatus,
)
from backend.models.db_models import Patient
from backend.schemas.api.checkin import (
    AppointmentBrief,
    IdentifyByCodeRequest,
    IdentifyByCurpRequest,
    IdentifyByNameRequest,
    IdentifyPatientResponse,
    PatientBrief,
    PendingActionResponse,
)
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .helpers import MAX_IDENTIFICATION_ATTEMPTS, mask_curp

logger = get_logger(__name__)

router = APIRouter(tags=["Check-in - Identification"])


# =============================================================================
# HELPERS
# =============================================================================


def _check_rate_limit(session: CheckinSession) -> None:
    """Check if session has exceeded identification attempts."""
    if session.identification_attempts >= MAX_IDENTIFICATION_ATTEMPTS:  # type: ignore[operator]
        raise HTTPException(
            status_code=429,
            detail="Too many identification attempts. Please try again later.",
        )


def _find_appointment_for_patient(
    db: Session, clinic_id: str, patient_id: str
) -> Appointment | None:
    """Find today's appointment for patient at clinic."""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)

    return (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor), joinedload(Appointment.pending_actions))
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.patient_id == patient_id,
            Appointment.scheduled_at >= today_start,
            Appointment.scheduled_at <= today_end,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
            Appointment.is_deleted.is_(False),
        )
        .order_by(Appointment.scheduled_at)
        .first()
    )


def _build_identification_response(
    patient: Patient, appointment: Appointment
) -> IdentifyPatientResponse:
    """Build successful identification response."""
    full_name = f"{patient.nombre} {patient.apellido}"

    pending_actions = [
        PendingActionResponse(
            action_id=str(a.action_id),
            action_type=a.action_type.value,
            status=a.status.value,
            title=a.title,
            description=a.description,
            icon=a.icon,
            is_required=a.is_required,
            is_blocking=a.is_blocking,
            amount=float(a.amount) if a.amount else None,
            currency=a.currency,
            document_type=a.document_type,
            document_url=a.document_url,
            signed_at=a.signed_at.isoformat() if a.signed_at else None,
            uploaded_file_id=str(a.uploaded_file_id) if a.uploaded_file_id else None,
            completed_at=a.completed_at.isoformat() if a.completed_at else None,
        )
        for a in appointment.pending_actions
        if a.status == PendingActionStatus.PENDING
    ]

    return IdentifyPatientResponse(
        success=True,
        patient=PatientBrief(
            patient_id=str(patient.patient_id),
            full_name=full_name,
            masked_curp=mask_curp(patient.curp) if patient.curp else None,
        ),
        appointment=AppointmentBrief(
            appointment_id=str(appointment.appointment_id),
            scheduled_at=appointment.scheduled_at.isoformat(),
            doctor_name=appointment.doctor.full_display_name if appointment.doctor else "Doctor",
            appointment_type=appointment.appointment_type.value,
        ),
        pending_actions=pending_actions,
    )


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("/identify/code", response_model=IdentifyPatientResponse)
def identify_by_code(request: IdentifyByCodeRequest, db: Session = Depends(get_db_dependency)):
    """Identify patient by 6-digit check-in code.

    Most secure method - code is sent via SMS/email when booking.
    Code expires at end of appointment day.
    """
    now = datetime.now(UTC)

    # Find appointment by code
    appointment = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor), joinedload(Appointment.pending_actions))
        .filter(
            Appointment.clinic_id == request.clinic_id,
            Appointment.checkin_code == request.checkin_code,
            Appointment.checkin_code_expires_at >= now,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
            Appointment.is_deleted.is_(False),
        )
        .first()
    )

    if not appointment:
        logger.warning(
            "IDENTIFY_BY_CODE_FAILED",
            clinic_id=request.clinic_id,
            code=request.checkin_code[:2] + "****",
        )
        return IdentifyPatientResponse(
            success=False,
            error="Código no válido o expirado. Intente con otro método.",
        )

    # Get patient
    patient = db.query(Patient).filter(Patient.patient_id == appointment.patient_id).first()
    if not patient:
        return IdentifyPatientResponse(success=False, error="Paciente no encontrado")

    logger.info(
        "IDENTIFY_BY_CODE_SUCCESS",
        clinic_id=request.clinic_id,
        patient_id=str(patient.patient_id),
    )

    return _build_identification_response(patient, appointment)


@router.post("/identify/curp", response_model=IdentifyPatientResponse)
def identify_by_curp(request: IdentifyByCurpRequest, db: Session = Depends(get_db_dependency)):
    """Identify patient by CURP (Mexican national ID).

    CURP format: AAAA000000AAAAAA00
    """
    # Find patient by CURP
    patient = db.query(Patient).filter(Patient.curp == request.curp.upper()).first()

    if not patient:
        logger.warning(
            "IDENTIFY_BY_CURP_FAILED", clinic_id=request.clinic_id, curp=mask_curp(request.curp)
        )
        return IdentifyPatientResponse(
            success=False,
            error="CURP no encontrado. Verifique el dato o use otro método.",
        )

    # Find appointment
    appointment = _find_appointment_for_patient(db, request.clinic_id, str(patient.patient_id))

    if not appointment:
        return IdentifyPatientResponse(
            success=False,
            error="No tiene cita programada para hoy en esta clínica.",
        )

    logger.info(
        "IDENTIFY_BY_CURP_SUCCESS",
        clinic_id=request.clinic_id,
        patient_id=str(patient.patient_id),
    )

    return _build_identification_response(patient, appointment)


@router.post("/identify/name", response_model=IdentifyPatientResponse)
def identify_by_name(request: IdentifyByNameRequest, db: Session = Depends(get_db_dependency)):
    """Identify patient by name and date of birth.

    Fallback method when code or CURP not available.
    """
    # Parse date
    dob = datetime.strptime(request.date_of_birth, "%Y-%m-%d")

    # Find patient by name + DOB (case-insensitive)
    patient = (
        db.query(Patient)
        .filter(
            func.lower(Patient.nombre).contains(request.first_name.lower()),
            func.lower(Patient.apellido).contains(request.last_name.lower()),
            func.date(Patient.fecha_nacimiento) == dob.date(),
        )
        .first()
    )

    if not patient:
        logger.warning(
            "IDENTIFY_BY_NAME_FAILED",
            clinic_id=request.clinic_id,
            name=f"{request.first_name} {request.last_name[0]}...",
        )
        return IdentifyPatientResponse(
            success=False,
            error="No se encontró paciente con esos datos. Verifique nombre y fecha de nacimiento.",
        )

    # Find appointment
    appointment = _find_appointment_for_patient(db, request.clinic_id, str(patient.patient_id))

    if not appointment:
        return IdentifyPatientResponse(
            success=False,
            error="No tiene cita programada para hoy en esta clínica.",
        )

    logger.info(
        "IDENTIFY_BY_NAME_SUCCESS",
        clinic_id=request.clinic_id,
        patient_id=str(patient.patient_id),
    )

    return _build_identification_response(patient, appointment)
