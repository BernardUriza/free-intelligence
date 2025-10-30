"""
Free Intelligence - Consultation Service (FastAPI)

RESTful API for SOAP-based medical consultations with event-sourcing.

File: backend/fi_consult_service.py
Created: 2025-10-28

Endpoints:
  POST   /consultations              - Start new consultation
  POST   /consultations/{id}/events  - Append event to consultation
  GET    /consultations/{id}         - Get consultation state (reconstructed from events)
  GET    /consultations/{id}/soap    - Get SOAP note view
  GET    /consultations/{id}/events  - Get event stream for consultation
  GET    /health                     - Health check

Usage:
  uvicorn backend.fi_consult_service:app --reload --port 7001
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import event store (to be implemented)
# from backend.fi_event_store import EventStore
# Import Sessions API router (FI-API-FEAT-009)
from backend.api.sessions import router as sessions_router
from backend.fi_consult_models import (AppendEventRequest, AppendEventResponse,
                                       Consultation, ConsultationEvent,
                                       EventType, GetConsultationResponse,
                                       GetSOAPResponse, SOAPNote,
                                       StartConsultationRequest,
                                       StartConsultationResponse)

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Free Intelligence - Consultation Service",
    description="Event-sourced SOAP consultation API for medical AI",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (LAN-only in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:9000",  # Aurity frontend (FI-UI-FEAT-201)
        "http://127.0.0.1:9000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Sessions API router (FI-API-FEAT-009)
# Note: router already has /api/sessions paths defined, so no prefix needed
app.include_router(sessions_router, tags=["sessions"])


# ============================================================================
# TEMPORARY IN-MEMORY STORE (for skeleton demo)
# Will be replaced with fi_event_store.py (HDF5/JSON)
# ============================================================================


class TemporaryStore:
    """Temporary in-memory store for demo purposes."""

    def __init__(self):
        self.consultations: dict[str, list[ConsultationEvent]] = {}

    def append_event(self, consultation_id: str, event: ConsultationEvent) -> None:
        """Append event to consultation stream."""
        if consultation_id not in self.consultations:
            self.consultations[consultation_id] = []
        self.consultations[consultation_id].append(event)

    def get_events(self, consultation_id: str) -> list[ConsultationEvent]:
        """Get all events for consultation."""
        return self.consultations.get(consultation_id, [])

    def get_event_count(self, consultation_id: str) -> int:
        """Get event count for consultation."""
        return len(self.consultations.get(consultation_id, []))

    def consultation_exists(self, consultation_id: str) -> bool:
        """Check if consultation exists."""
        return consultation_id in self.consultations


# Global temporary store
temp_store = TemporaryStore()


# ============================================================================
# STATE RECONSTRUCTION (Event Sourcing)
# ============================================================================


def reconstruct_consultation_state(
    consultation_id: str, events: list[ConsultationEvent]
) -> Consultation:
    """
    Reconstruct consultation state from event stream.
    This is the core of event-sourcing: state = f(events).
    """
    from uuid import uuid4

    # Initialize empty consultation
    consultation = Consultation(
        consultation_id=consultation_id,
        session_id=str(uuid4()),  # Will be overridden by first event
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        messages=[],
        event_count=0,
    )

    # Replay events to build current state
    for event in events:
        consultation.event_count += 1
        consultation.last_event_id = event.event_id
        consultation.updated_at = event.timestamp

        # Handle each event type
        if event.event_type == EventType.MESSAGE_RECEIVED:
            consultation.messages.append(event.payload)

        elif event.event_type == EventType.DEMOGRAPHICS_UPDATED:
            if consultation.patient_data is None:
                from backend.fi_consult_models import PatientStub

                consultation.patient_data = PatientStub()
            for key, value in event.payload.items():
                if hasattr(consultation.patient_data, key):
                    setattr(consultation.patient_data, key, value)

        elif event.event_type == EventType.EXTRACTION_COMPLETED:
            consultation.extraction_data = event.payload.get("extraction_data")
            consultation.extraction_iteration = event.payload.get("iteration", 0)

        elif event.event_type == EventType.SOAP_GENERATION_COMPLETED:
            soap_data = event.payload.get("soap_data")
            if soap_data:
                # Parse SOAP data into SOAPNote model
                try:
                    consultation.soap_note = SOAPNote(**soap_data)
                except Exception:
                    # If parsing fails, store raw data
                    consultation.soap_note = soap_data  # type: ignore

        elif event.event_type == EventType.URGENCY_CLASSIFIED:
            from backend.fi_consult_models import UrgencyAssessment

            consultation.urgency_assessment = UrgencyAssessment(
                urgency_level=event.payload.get("urgency_level"),
                gravity_score=event.payload.get("gravity_score"),
                time_to_action=event.payload.get("time_to_action"),
                identified_patterns=event.payload.get("identified_patterns", []),
                risk_factors=event.payload.get("risk_factors", []),
                immediate_actions=event.payload.get("immediate_actions", []),
            )

        elif event.event_type == EventType.CONSULTATION_COMMITTED:
            consultation.is_committed = True
            consultation.commit_hash = event.payload.get("commit_hash")

    return consultation


# ============================================================================
# API ENDPOINTS
# ============================================================================


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API info."""
    return {
        "service": "Free Intelligence - Consultation Service",
        "version": "0.3.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "consultations_count": len(temp_store.consultations),
        "service": "fi_consultation_service",
    }


@app.post(
    "/consultations",
    response_model=StartConsultationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Consultations"],
)
async def start_consultation(request: StartConsultationRequest):
    """
    Start a new consultation.

    Creates a new consultation with unique ID and initializes event stream.

    Args:
        request: StartConsultationRequest with user_id and optional patient_stub

    Returns:
        StartConsultationResponse with consultation_id, session_id, created_at
    """
    from uuid import uuid4

    from backend.fi_consult_models import EventMetadata

    consultation_id = str(uuid4())
    session_id = str(uuid4())
    created_at = datetime.utcnow()

    # Create initial event (consultation started)
    initial_event = ConsultationEvent(
        consultation_id=consultation_id,
        timestamp=created_at,
        event_type=EventType.MESSAGE_RECEIVED,  # Placeholder
        payload={
            "message_content": "Consultation started",
            "message_role": "assistant",
            "metadata": {"consultation_started": True, "session_id": session_id},
        },
        metadata=EventMetadata(user_id=request.user_id, session_id=session_id),
    )

    # Append to store
    temp_store.append_event(consultation_id, initial_event)

    return StartConsultationResponse(
        consultation_id=consultation_id, session_id=session_id, created_at=created_at
    )


@app.post(
    "/consultations/{consultation_id}/events",
    response_model=AppendEventResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Consultations"],
)
async def append_event(
    consultation_id: str = Path(..., description="Consultation ID"),
    request: AppendEventRequest = ...,
):
    """
    Append event to consultation event stream.

    This is the core write operation in event-sourcing. All state changes
    are represented as events appended to the stream.

    Args:
        consultation_id: UUID of consultation
        request: AppendEventRequest with event_type, payload, user_id

    Returns:
        AppendEventResponse with event_id, consultation_id, event_count

    Raises:
        HTTPException 404: Consultation not found
    """
    from backend.fi_consult_models import EventMetadata

    # Check consultation exists
    if not temp_store.consultation_exists(consultation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation {consultation_id} not found",
        )

    # Get session_id from first event
    events = temp_store.get_events(consultation_id)
    session_id = events[0].metadata.session_id if events else "unknown"

    # Create event
    event = ConsultationEvent(
        consultation_id=consultation_id,
        timestamp=datetime.utcnow(),
        event_type=request.event_type,
        payload=request.payload,
        metadata=EventMetadata(user_id=request.user_id, session_id=session_id),
    )

    # TODO: Calculate SHA256 audit hash
    # event.audit_hash = calculate_sha256(event.payload)

    # Append to store
    temp_store.append_event(consultation_id, event)

    return AppendEventResponse(
        event_id=event.event_id,
        consultation_id=consultation_id,
        event_count=temp_store.get_event_count(consultation_id),
        timestamp=event.timestamp,
    )


@app.get(
    "/consultations/{consultation_id}",
    response_model=GetConsultationResponse,
    tags=["Consultations"],
)
async def get_consultation(consultation_id: str = Path(..., description="Consultation ID")):
    """
    Get consultation state (reconstructed from events).

    Reconstructs the current state by replaying all events in the stream.
    This is the core read operation in event-sourcing.

    Args:
        consultation_id: UUID of consultation

    Returns:
        GetConsultationResponse with full consultation state

    Raises:
        HTTPException 404: Consultation not found
    """
    # Check consultation exists
    if not temp_store.consultation_exists(consultation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation {consultation_id} not found",
        )

    # Get events
    events = temp_store.get_events(consultation_id)

    # Reconstruct state from events
    consultation = reconstruct_consultation_state(consultation_id, events)

    return GetConsultationResponse(consultation=consultation)


@app.get(
    "/consultations/{consultation_id}/soap", response_model=GetSOAPResponse, tags=["Consultations"]
)
async def get_soap(consultation_id: str = Path(..., description="Consultation ID")):
    """
    Get SOAP note view for consultation.

    Returns the current SOAP note with completeness metrics and urgency
    assessment. This is a projection/view of the consultation state.

    Args:
        consultation_id: UUID of consultation

    Returns:
        GetSOAPResponse with SOAP note, completeness, urgency

    Raises:
        HTTPException 404: Consultation not found
    """
    # Check consultation exists
    if not temp_store.consultation_exists(consultation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation {consultation_id} not found",
        )

    # Get events and reconstruct
    events = temp_store.get_events(consultation_id)
    consultation = reconstruct_consultation_state(consultation_id, events)

    # Check if SOAP ready for commit
    is_ready = (
        consultation.soap_note is not None
        and consultation.completeness is not None
        and consultation.completeness.ready_for_commit
    )

    return GetSOAPResponse(
        consultation_id=consultation_id,
        soap_note=consultation.soap_note,
        completeness=consultation.completeness,
        urgency_assessment=consultation.urgency_assessment,
        is_ready_for_commit=is_ready,
    )


@app.get("/consultations/{consultation_id}/events", tags=["Consultations"])
async def get_events(
    consultation_id: str = Path(..., description="Consultation ID"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Max events to return"),
    offset: Optional[int] = Query(0, ge=0, description="Event offset"),
):
    """
    Get event stream for consultation.

    Returns raw event stream for debugging, audit, or replay purposes.

    Args:
        consultation_id: UUID of consultation
        limit: Maximum number of events to return (default: all)
        offset: Event offset for pagination

    Returns:
        List of events with metadata

    Raises:
        HTTPException 404: Consultation not found
    """
    # Check consultation exists
    if not temp_store.consultation_exists(consultation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consultation {consultation_id} not found",
        )

    # Get events
    events = temp_store.get_events(consultation_id)

    # Apply pagination
    if offset:
        events = events[offset:]
    if limit:
        events = events[:limit]

    return {
        "consultation_id": consultation_id,
        "event_count": temp_store.get_event_count(consultation_id),
        "returned_count": len(events),
        "offset": offset,
        "events": [event.model_dump() for event in events],
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with structured JSON response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    from backend.logger import get_logger

    logger = get_logger(__name__)
    logger.info(
        "CONSULTATION_SERVICE_STARTED", version="0.3.0", port=7001, timezone="America/Mexico_City"
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    from backend.logger import get_logger

    logger = get_logger(__name__)
    logger.info(
        "CONSULTATION_SERVICE_STOPPED", consultations_processed=len(temp_store.consultations)
    )


# ============================================================================
# MAIN (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.fi_consult_service:app", host="127.0.0.1", port=7001, reload=True, log_level="info"
    )
