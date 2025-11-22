"""FI Receptionist Check-in API endpoints.

Patient self-service check-in system for medical clinics.
Supports QR code check-in, multiple identification methods,
pending actions, and real-time waiting room updates.

Author: Bernard Uriza Orozco
Created: 2025-11-21
Card: FI-CHECKIN-001
"""

from __future__ import annotations

import base64
import io
import json
import qrcode
import secrets
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import List

from backend.database import get_db_dependency
from backend.logger import get_logger
from backend.models.checkin_models import (
    Appointment,
    AppointmentStatus,
    CheckinSession,
    CheckinStep,
    Clinic,
    DeviceType,
    PendingAction,
    PendingActionStatus,
    WaitingRoomEvent,
)
from backend.models.db_models import Patient
from backend.schemas.checkin_schemas import (
    AppointmentBrief,
    CheckinSessionResponse,
    CompleteActionRequest,
    CompleteCheckinRequest,
    CompleteCheckinResponse,
    GenerateQRRequest,
    GenerateQRResponse,
    GetActionsResponse,
    GetWaitingRoomResponse,
    IdentifyByCodeRequest,
    IdentifyByCurpRequest,
    IdentifyByNameRequest,
    IdentifyPatientResponse,
    PatientBrief,
    PendingActionResponse,
    StartSessionRequest,
    WaitingRoomPatient,
    WaitingRoomState,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/checkin", tags=["Check-in"])

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_IDENTIFICATION_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes
QR_EXPIRY_MINUTES = 5
SESSION_EXPIRY_MINUTES = 15

# WebSocket connections for waiting room updates
waiting_room_connections: dict[str, List[WebSocket]] = {}


# =============================================================================
# HELPER FUNCTIONS
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


def calculate_wait_time(position: int, avg_consultation_minutes: int = 20) -> int:
    """Estimate wait time based on queue position."""
    return max(0, (position - 1) * avg_consultation_minutes)


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
            Appointment.is_deleted == False,
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
            Appointment.is_deleted == False,
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
# QR CODE GENERATION
# =============================================================================


@router.post("/qr/generate", response_model=GenerateQRResponse)
def generate_qr(request: GenerateQRRequest, db: Session = Depends(get_db_dependency)):
    """Generate QR code for TV display.

    The QR encodes a URL that patients scan to start check-in.
    QR codes expire after 5 minutes for security.
    """
    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == request.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail=f"Clinic {request.clinic_id} not found")

    # Generate QR data
    now = datetime.now(UTC)
    expires_at = now.replace(second=0, microsecond=0)
    expires_at = expires_at.replace(minute=expires_at.minute + QR_EXPIRY_MINUTES)

    nonce = secrets.token_urlsafe(8)

    # URL for check-in page
    base_url = "https://app.aurity.io"
    qr_url = (
        f"{base_url}/checkin?clinic={request.clinic_id}&t={int(expires_at.timestamp())}&n={nonce}"
    )

    # Generate QR code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    logger.info("QR_GENERATED", clinic_id=request.clinic_id, expires_at=expires_at.isoformat())

    return GenerateQRResponse(
        qr_data=f"data:image/png;base64,{qr_base64}",
        qr_url=qr_url,
        expires_at=expires_at.isoformat(),
    )


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================


@router.post("/session/start", response_model=CheckinSessionResponse)
def start_session(request: StartSessionRequest, db: Session = Depends(get_db_dependency)):
    """Start a new check-in session.

    Called when patient scans QR code. Session expires in 15 minutes.
    """
    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == request.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail=f"Clinic {request.clinic_id} not found")

    # Create session
    now = datetime.now(UTC)
    session = CheckinSession(
        clinic_id=request.clinic_id,
        device_type=DeviceType(request.device_type.value),
        current_step=CheckinStep.IDENTIFY,
        started_at=now,
        expires_at=now.replace(minute=now.minute + SESSION_EXPIRY_MINUTES),
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(
        "CHECKIN_SESSION_STARTED",
        session_id=str(session.session_id),
        clinic_id=request.clinic_id,
        device_type=request.device_type.value,
    )

    return CheckinSessionResponse(
        session_id=str(session.session_id),
        clinic_id=str(session.clinic_id),
        current_step=CheckinStep(session.current_step.value),
        started_at=session.started_at.isoformat(),
        completed_at=None,
        identification_method=session.identification_method,
        appointment_id=str(session.appointment_id) if session.appointment_id else None,
        patient_id=str(session.patient_id) if session.patient_id else None,
        device_type=DeviceType(session.device_type.value),
        expires_at=session.expires_at.isoformat(),
    )


@router.get("/session/{session_id}", response_model=CheckinSessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db_dependency)):
    """Get current session state."""
    session = db.query(CheckinSession).filter(CheckinSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_expired:
        raise HTTPException(status_code=410, detail="Session expired")

    return CheckinSessionResponse(
        session_id=str(session.session_id),
        clinic_id=str(session.clinic_id),
        current_step=CheckinStep(session.current_step.value),
        started_at=session.started_at.isoformat(),
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
        identification_method=session.identification_method,
        appointment_id=str(session.appointment_id) if session.appointment_id else None,
        patient_id=str(session.patient_id) if session.patient_id else None,
        device_type=DeviceType(session.device_type.value),
        expires_at=session.expires_at.isoformat(),
    )


# =============================================================================
# PATIENT IDENTIFICATION
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
            Appointment.is_deleted == False,
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
            Appointment.is_deleted == False,
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


# =============================================================================
# PENDING ACTIONS
# =============================================================================


@router.get("/actions/{appointment_id}", response_model=GetActionsResponse)
def get_pending_actions(appointment_id: str, db: Session = Depends(get_db_dependency)):
    """Get pending actions for an appointment."""
    actions = (
        db.query(PendingAction)
        .filter(PendingAction.appointment_id == appointment_id)
        .order_by(PendingAction.is_blocking.desc(), PendingAction.is_required.desc())
        .all()
    )

    return GetActionsResponse(
        actions=[
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
            for a in actions
        ]
    )


@router.post("/actions/{action_id}/complete", response_model=PendingActionResponse)
def complete_action(
    action_id: str,
    request: CompleteActionRequest,
    db: Session = Depends(get_db_dependency),
):
    """Complete a pending action."""
    action = db.query(PendingAction).filter(PendingAction.action_id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.status == PendingActionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Action already completed")

    now = datetime.now(UTC)

    # Handle specific action types
    if request.signature_data:
        action.signature_data = request.signature_data
        action.signed_at = now

    if request.payment_intent_id:
        action.payment_intent_id = request.payment_intent_id

    if request.file_id:
        action.uploaded_file_id = request.file_id

    action.status = PendingActionStatus.COMPLETED
    action.completed_at = now
    action.completed_by = "patient"

    db.commit()
    db.refresh(action)

    logger.info("ACTION_COMPLETED", action_id=action_id, action_type=action.action_type.value)

    return PendingActionResponse(
        action_id=str(action.action_id),
        action_type=action.action_type.value,
        status=action.status.value,
        title=action.title,
        description=action.description,
        icon=action.icon,
        is_required=action.is_required,
        is_blocking=action.is_blocking,
        amount=float(action.amount) if action.amount else None,
        currency=action.currency,
        document_type=action.document_type,
        document_url=action.document_url,
        signed_at=action.signed_at.isoformat() if action.signed_at else None,
        uploaded_file_id=str(action.uploaded_file_id) if action.uploaded_file_id else None,
        completed_at=action.completed_at.isoformat() if action.completed_at else None,
    )


@router.post("/actions/{action_id}/skip", response_model=PendingActionResponse)
def skip_action(action_id: str, db: Session = Depends(get_db_dependency)):
    """Skip a non-required pending action."""
    action = db.query(PendingAction).filter(PendingAction.action_id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.is_required:
        raise HTTPException(status_code=400, detail="Cannot skip required action")

    if action.status != PendingActionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Action cannot be skipped in current state")

    action.status = PendingActionStatus.SKIPPED
    action.completed_at = datetime.now(UTC)
    action.completed_by = "patient"

    db.commit()
    db.refresh(action)

    logger.info("ACTION_SKIPPED", action_id=action_id, action_type=action.action_type.value)

    return PendingActionResponse(
        action_id=str(action.action_id),
        action_type=action.action_type.value,
        status=action.status.value,
        title=action.title,
        description=action.description,
        icon=action.icon,
        is_required=action.is_required,
        is_blocking=action.is_blocking,
        amount=float(action.amount) if action.amount else None,
        currency=action.currency,
        document_type=action.document_type,
        document_url=action.document_url,
        signed_at=action.signed_at.isoformat() if action.signed_at else None,
        uploaded_file_id=str(action.uploaded_file_id) if action.uploaded_file_id else None,
        completed_at=action.completed_at.isoformat() if action.completed_at else None,
    )


# =============================================================================
# COMPLETE CHECK-IN
# =============================================================================


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
    event = WaitingRoomEvent(
        clinic_id=str(appointment.clinic_id),
        event_type="patient_checkin",
        event_data=json.dumps(
            {
                "appointment_id": str(appointment.appointment_id),
                "patient_id": str(appointment.patient_id),
                "queue_position": queue_position,
            }
        ),
        appointment_id=appointment.appointment_id,
        patient_id=appointment.patient_id,
    )
    db.add(event)

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


# =============================================================================
# WAITING ROOM
# =============================================================================


@router.get("/waiting-room/{clinic_id}", response_model=GetWaitingRoomResponse)
def get_waiting_room(clinic_id: str, db: Session = Depends(get_db_dependency)):
    """Get current waiting room state for a clinic."""
    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail=f"Clinic {clinic_id} not found")

    state = get_waiting_room_state(db, clinic_id)

    return GetWaitingRoomResponse(state=state)


@router.websocket("/waiting-room/{clinic_id}/ws")
async def waiting_room_websocket(websocket: WebSocket, clinic_id: str):
    """WebSocket endpoint for real-time waiting room updates.

    TV displays connect here to receive live updates when
    patients check in or are called.
    """
    await websocket.accept()

    # Add to connections
    if clinic_id not in waiting_room_connections:
        waiting_room_connections[clinic_id] = []
    waiting_room_connections[clinic_id].append(websocket)

    logger.info("WEBSOCKET_CONNECTED", clinic_id=clinic_id)

    try:
        # Keep connection alive
        while True:
            # Wait for messages (mainly for ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WEBSOCKET_DISCONNECTED", clinic_id=clinic_id)
    finally:
        # Clean up
        if clinic_id in waiting_room_connections:
            try:
                waiting_room_connections[clinic_id].remove(websocket)
            except ValueError:
                pass
