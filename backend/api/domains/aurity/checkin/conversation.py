"""Conversational Check-in Endpoints.

POST   /checkin/conversation/start - Start conversation
POST   /checkin/conversation/{id}/message - Send message
GET    /checkin/conversation/{id}/context - Get context
DELETE /checkin/conversation/{id} - End conversation

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
Card: FI-CHECKIN-004 (Sprint 4)
"""

from __future__ import annotations

import secrets

from backend.database import get_db_dependency
from backend.models.checkin_models import Clinic
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy.orm import Session

logger = get_logger(__name__)

router = APIRouter(tags=["Check-in - Conversation"])


# =============================================================================
# SCHEMAS
# =============================================================================


class ConversationStartRequest(PydanticBaseModel):
    """Request to start a conversational check-in."""

    clinic_id: str
    clinic_name: str | None = None


class ConversationMessageRequest(PydanticBaseModel):
    """Request to send a message in conversation."""

    message: str


class ConversationResponse(PydanticBaseModel):
    """Response from conversation endpoint."""

    message: str
    state: str
    requires_input: bool = True
    quick_replies: list[str] = []
    actions: list[dict] = []
    metadata: dict = {}


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("/conversation/start", response_model=ConversationResponse)
async def start_conversation(
    request: ConversationStartRequest,
    db: Session = Depends(get_db_dependency),
) -> ConversationResponse:
    """Start a conversational check-in session.

    Returns initial greeting and begins the guided check-in flow.
    """
    from backend.services.checkin.services.checkin_conversation import checkin_conversation_service

    # Get clinic name if not provided
    clinic_name = request.clinic_name
    if not clinic_name:
        clinic = db.query(Clinic).filter(Clinic.clinic_id == request.clinic_id).first()
        clinic_name = clinic.name if clinic else "la clínica"

    # Generate session ID
    session_id = f"conv_{secrets.token_hex(8)}"

    # Start conversation
    response = checkin_conversation_service.start_conversation(
        session_id=session_id,
        clinic_id=request.clinic_id,
        clinic_name=clinic_name,
    )

    logger.info(
        "CONVERSATION_STARTED",
        session_id=session_id,
        clinic_id=request.clinic_id,
    )

    return ConversationResponse(
        message=response.message,
        state=response.state.value,
        requires_input=response.requires_input,
        quick_replies=response.quick_replies,
        actions=response.actions,
        metadata={"session_id": session_id, **response.metadata},
    )


@router.post("/conversation/{session_id}/message", response_model=ConversationResponse)
async def send_conversation_message(
    session_id: str,
    request: ConversationMessageRequest,
    db: Session = Depends(get_db_dependency),
) -> ConversationResponse:
    """Send a message in an ongoing conversation.

    Processes user input and returns next step in guided flow.
    """
    from backend.services.checkin.services.checkin_conversation import checkin_conversation_service

    response = await checkin_conversation_service.process_message(
        session_id=session_id,
        user_message=request.message,
        db_session=db,
    )

    return ConversationResponse(
        message=response.message,
        state=response.state.value,
        requires_input=response.requires_input,
        quick_replies=response.quick_replies,
        actions=response.actions,
        metadata=response.metadata,
    )


@router.get("/conversation/{session_id}/context")
async def get_conversation_context(session_id: str) -> dict:
    """Get current conversation context and state.

    Useful for resuming conversations or debugging.
    """
    from backend.services.checkin.services.checkin_conversation import checkin_conversation_service

    context = checkin_conversation_service.get_context(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "session_id": context.session_id,
        "clinic_id": context.clinic_id,
        "state": context.state.value,
        "patient_id": context.patient_id,
        "patient_name": context.patient_name,
        "appointment_id": context.appointment_id,
        "attempts": context.attempts,
        "message_count": len(context.messages),
        "created_at": context.created_at.isoformat(),
        "last_updated": context.last_updated.isoformat(),
    }


@router.delete("/conversation/{session_id}")
async def end_conversation(session_id: str) -> dict:
    """End and clean up a conversation session."""
    from backend.services.checkin.services.checkin_conversation import checkin_conversation_service

    checkin_conversation_service.end_conversation(session_id)

    return {"status": "ended", "session_id": session_id}
