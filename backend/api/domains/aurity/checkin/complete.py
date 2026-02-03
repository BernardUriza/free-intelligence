"""Complete Check-in Endpoint.

POST /checkin/complete - Complete the check-in process

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.database import get_db_dependency
from backend.models.checkin_models import (
    Appointment,
    AppointmentStatus,
    CheckinSession,
    CheckinStep,
    PendingActionStatus,
)
from backend.schemas.api.checkin import CompleteCheckinRequest, CompleteCheckinResponse
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .helpers import (
    broadcast_waiting_room_update,
    calculate_wait_time,
    get_waiting_room_state,
    log_waiting_room_event,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Check-in - Complete"])


@router.post("/complete", response_model=CompleteCheckinResponse)
async def complete_checkin(
    request: CompleteCheckinRequest, db: Session = Depends(get_db_dependency)
):
    """Complete the check-in process.

    Marks appointment as checked-in, updates queue position,
    and broadcasts to waiting room displays.
    """
    # Validate session
    session = (
        db.query(CheckinSession).filter(CheckinSession.session_id == request.session_id).first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_expired:
        raise HTTPException(status_code=410, detail="Session expired")

    # Get appointment
    appointment = (
        db.query(Appointment)
        .options(joinedload(Appointment.pending_actions))
        .filter(Appointment.appointment_id == request.appointment_id)
        .first()
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Check for blocking actions not completed
    blocking_pending = [
        a
        for a in appointment.pending_actions
        if a.is_blocking and a.status == PendingActionStatus.PENDING
    ]
    if blocking_pending:
        return CompleteCheckinResponse(
            success=False,
            checkin_time="",
            position_in_queue=0,
            estimated_wait_minutes=0,
            message="",
            error="Debe completar las acciones requeridas antes del check-in",
        )

    now = datetime.now(UTC)

    # Calculate queue position
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    queue_position = (
        db.query(Appointment)
        .filter(
            Appointment.clinic_id == appointment.clinic_id,
            Appointment.status == AppointmentStatus.CHECKED_IN,
            Appointment.checked_in_at >= today_start,
        )
        .count()
        + 1
    )

    # Update appointment
    appointment.status = AppointmentStatus.CHECKED_IN
    appointment.checked_in_at = now
    appointment.queue_position = queue_position

    # Update session
    session.current_step = CheckinStep.SUCCESS
    session.completed_at = now
    session.appointment_id = appointment.appointment_id
    session.patient_id = appointment.patient_id

    # Log event
    log_waiting_room_event(
        db=db,
        clinic_id=str(appointment.clinic_id),
        event_type="patient_checkin",
        appointment_id=str(appointment.appointment_id),
        patient_id=str(appointment.patient_id),
        extra_data={"queue_position": queue_position},
    )

    db.commit()

    # Broadcast update to waiting room displays
    state = get_waiting_room_state(db, str(appointment.clinic_id))
    await broadcast_waiting_room_update(str(appointment.clinic_id), state)

    estimated_wait = calculate_wait_time(queue_position)

    logger.info(
        "CHECKIN_COMPLETED",
        appointment_id=str(appointment.appointment_id),
        patient_id=str(appointment.patient_id),
        queue_position=queue_position,
    )

    return CompleteCheckinResponse(
        success=True,
        checkin_time=now.isoformat(),
        position_in_queue=queue_position,
        estimated_wait_minutes=estimated_wait,
        message="¡Check-in exitoso! Te llamaremos por tu nombre cuando sea tu turno.",
    )
