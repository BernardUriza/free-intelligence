"""Session Management Endpoints.

POST /checkin/session/start - Start check-in session
GET  /checkin/session/{id} - Get session state

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.database import get_db_dependency
from backend.models.checkin_models import (
    CheckinSession,
    CheckinStep,
    Clinic,
    DeviceType,
)
from backend.schemas.api.checkin import CheckinSessionResponse, StartSessionRequest
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .helpers import SESSION_EXPIRY_MINUTES

logger = get_logger(__name__)

router = APIRouter(tags=["Check-in - Sessions"])


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
