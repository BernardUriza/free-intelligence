"""Pending Actions Endpoints.

GET  /checkin/actions/{appointment_id} - Get pending actions
POST /checkin/actions/{action_id}/complete - Complete action
POST /checkin/actions/{action_id}/skip - Skip non-required action

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.database import get_db_dependency
from backend.models.checkin_models import PendingAction, PendingActionStatus
from backend.schemas.api.checkin import (
    CompleteActionRequest,
    GetActionsResponse,
    PendingActionResponse,
)
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

logger = get_logger(__name__)

router = APIRouter(tags=["Check-in - Actions"])


def _action_to_response(action: PendingAction) -> PendingActionResponse:
    """Convert PendingAction model to response."""
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


@router.get("/actions/{appointment_id}", response_model=GetActionsResponse)
def get_pending_actions(appointment_id: str, db: Session = Depends(get_db_dependency)):
    """Get pending actions for an appointment."""
    actions = (
        db.query(PendingAction)
        .filter(PendingAction.appointment_id == appointment_id)
        .order_by(PendingAction.is_blocking.desc(), PendingAction.is_required.desc())
        .all()
    )

    return GetActionsResponse(actions=[_action_to_response(a) for a in actions])


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

    now = datetime.now(timezone.utc)

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

    return _action_to_response(action)


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
    action.completed_at = datetime.now(timezone.utc)
    action.completed_by = "patient"

    db.commit()
    db.refresh(action)

    logger.info("ACTION_SKIPPED", action_id=action_id, action_type=action.action_type.value)

    return _action_to_response(action)
