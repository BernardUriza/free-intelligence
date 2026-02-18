"""Check-in Helpers - Utility functions for check-in operations.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from backend.models.checkin_models import (
    Appointment,
    AppointmentStatus,
    WaitingRoomEvent,
)
from backend.models.db_models import Patient
from backend.schemas.api.checkin import WaitingRoomPatient, WaitingRoomState
from fastapi import WebSocket
from sqlalchemy.orm import Session, joinedload

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_IDENTIFICATION_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes
QR_EXPIRY_MINUTES = 5
SESSION_EXPIRY_MINUTES = 15

# WebSocket connections for waiting room updates
waiting_room_connections: dict[str, list[WebSocket]] = {}


# =============================================================================
# PRIVACY HELPERS
# =============================================================================


def mask_curp(curp: str) -> str:
    """Mask CURP for privacy display."""
    if not curp or len(curp) != 18:
        return curp
    return f"{curp[:4]}{'*' * 10}{curp[14:]}"


def get_display_name(full_name: str) -> str:
    """Get privacy-aware display name (María García -> María G.)."""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[-1][0]}."
    return full_name


# =============================================================================
# WAITING ROOM HELPERS
# =============================================================================


def calculate_wait_time(position: int, avg_consultation_minutes: int = 20) -> int:
    """Estimate wait time based on queue position."""
    return max(0, (position - 1) * avg_consultation_minutes)


async def broadcast_waiting_room_update(clinic_id: str, state: WaitingRoomState) -> None:
    """Broadcast waiting room update to all connected WebSocket clients."""
    connections = waiting_room_connections.get(clinic_id, [])
    if not connections:
        return

    message = state.model_dump_json()
    disconnected = []

    for ws in connections:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)

    # Clean up disconnected clients
    for ws in disconnected:
        connections.remove(ws)


def get_waiting_room_state(db: Session, clinic_id: str) -> WaitingRoomState:
    """Build current waiting room state."""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Get checked-in patients waiting
    waiting_appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.doctor))
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.status == AppointmentStatus.CHECKED_IN,
            Appointment.checked_in_at >= today_start,
            not Appointment.is_deleted,
        )
        .order_by(Appointment.checked_in_at)
        .all()
    )

    # Get patients seen today
    patients_seen = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == clinic_id,
            Appointment.status.in_([AppointmentStatus.COMPLETED, AppointmentStatus.IN_PROGRESS]),
            Appointment.scheduled_at >= today_start,
            not Appointment.is_deleted,
        )
        .count()
    )

    # Build patient list
    patients_waiting = []
    total_wait = 0

    for idx, appt in enumerate(waiting_appointments, start=1):
        # Get patient info
        patient = db.query(Patient).filter(Patient.patient_id == appt.patient_id).first()
        if not patient:
            continue

        full_name = f"{patient.nombre} {patient.apellido}"
        wait_minutes = calculate_wait_time(
            idx, appt.doctor.avg_consultation_minutes if appt.doctor else 20
        )
        total_wait += wait_minutes

        patients_waiting.append(
            WaitingRoomPatient(
                patient_id=str(appt.patient_id),
                patient_name=full_name,
                appointment_id=str(appt.appointment_id),
                checked_in_at=appt.checked_in_at.isoformat()
                if appt.checked_in_at
                else now.isoformat(),
                position_in_queue=idx,
                estimated_wait_minutes=wait_minutes,
                doctor_id=str(appt.doctor_id),
                doctor_name=appt.doctor.full_display_name if appt.doctor else "Doctor",
                display_name=get_display_name(full_name),
                is_next=(idx == 1),
            )
        )

    avg_wait = total_wait // len(patients_waiting) if patients_waiting else 0

    return WaitingRoomState(
        clinic_id=clinic_id,
        patients_waiting=patients_waiting,
        total_waiting=len(patients_waiting),
        avg_wait_time_minutes=avg_wait,
        patients_seen_today=patients_seen,
        next_available_slot=None,  # Could calculate from schedule
        updated_at=now.isoformat(),
    )


# =============================================================================
# EVENT LOGGING
# =============================================================================


def log_waiting_room_event(
    db: Session,
    clinic_id: str,
    event_type: str,
    appointment_id: str,
    patient_id: str,
    extra_data: dict | None = None,
) -> WaitingRoomEvent:
    """Log a waiting room event."""
    event_data = {
        "appointment_id": appointment_id,
        "patient_id": patient_id,
    }
    if extra_data:
        event_data.update(extra_data)

    event = WaitingRoomEvent(
        clinic_id=clinic_id,
        event_type=event_type,
        event_data=json.dumps(event_data),
        appointment_id=appointment_id,
        patient_id=patient_id,
    )
    db.add(event)
    return event
