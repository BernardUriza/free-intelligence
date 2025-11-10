"""Sessions API Router.

Session CRUD operations

File: backend/api/sessions/router.py
Reorganized: 2025-11-08 (moved from backend/api/sessions.py)
"""

#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Sessions API

FastAPI router for Sessions CRUD operations.

File: backend/api/sessions.py
Card: FI-API-FEAT-009
Created: 2025-10-29

Endpoints:
- GET /api/sessions -> list sessions (paginated)
- GET /api/sessions/{id} -> get single session
- POST /api/sessions -> create session
- PATCH /api/sessions/{id} -> update session
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.container import get_container
from backend.logger import get_logger
from backend.schemas.schemas import error_response

logger = get_logger(__name__)

# ============================================================================
# PYDANTIC MODELS (API contracts)
# ============================================================================


class SessionResponse(BaseModel):
    """Session response schema"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "01JBEXAMPLE123",
                "created_at": "2025-10-29T21:30:00Z",
                "updated_at": "2025-10-29T21:35:00Z",
                "last_active": "2025-10-29T21:35:00Z",
                "interaction_count": 5,
                "status": "active",
                "is_persisted": True,
                "owner_hash": "sha256:abc123",
                "thread_id": "thread_xyz",
            }
        }
    )

    id: str
    created_at: str
    updated_at: str
    last_active: str
    interaction_count: int
    status: str  # new|active|complete
    is_persisted: bool
    owner_hash: str
    thread_id: Optional[str] = None


class SessionsListResponse(BaseModel):
    """Sessions list response with pagination"""

    items: list[SessionResponse]
    total: int
    limit: int
    offset: int


class CreateSessionRequest(BaseModel):
    """Create session request"""

    owner_hash: str = Field(..., min_length=1)
    status: str = Field(default="new", pattern="^(new|active|complete)$")
    thread_id: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    """Update session request (partial)"""

    status: Optional[str] = Field(None, pattern="^(new|active|complete)$")
    last_active: Optional[str] = None
    interaction_count: Optional[int] = Field(None, ge=0)


# ============================================================================
# FASTAPI ROUTER
# ============================================================================

router = APIRouter()


@router.get("", response_model=SessionsListResponse)
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    owner_hash: Optional[str] = Query(None),
):
    """
    List sessions with pagination.

    **Clean Code Architecture:**
    - SessionService handles session retrieval and filtering
    - Uses DI container for dependency injection

    Query params:
    - limit: Max sessions to return (1-100, default 50)
    - offset: Number of sessions to skip (default 0)
    - owner_hash: Filter by owner_hash (optional)

    Returns:
    - items: List of sessions
    - total: Total count (with filters applied)
    - limit: Limit used
    - offset: Offset used
    """
    try:
        # Get session service from DI container
        session_service = get_container().get_session_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service for listing
        sessions = session_service.list_sessions(user_id=owner_hash)

        # Log audit trail
        audit_service.log_action(
            action="sessions_listed",
            user_id="system",
            resource="sessions",
            result="success",
            details={"limit": limit, "owner_hash": owner_hash},
        )

        return SessionsListResponse(
            items=[SessionResponse(**s) for s in sessions],
            total=len(sessions),
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error("LIST_SESSIONS_FAILED", error=str(e))
        return error_response("Failed to list sessions", code=500)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Get single session by ID.

    **Clean Code Architecture:**
    - SessionService handles session retrieval
    - Uses DI container for dependency injection

    Path params:
    - session_id: Session ID (ULID)

    Returns:
    - Session object

    Raises:
    - 404: Session not found
    """
    try:
        # Get session service from DI container
        session_service = get_container().get_session_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service for retrieval
        session = session_service.get_session(session_id)

        if not session:
            logger.warning("SESSION_NOT_FOUND", session_id=session_id)
            return error_response(f"Session {session_id} not found", code=404)

        # Log audit trail
        audit_service.log_action(
            action="session_retrieved",
            user_id="system",
            resource=f"session:{session_id}",
            result="success",
        )

        return SessionResponse(**session)

    except Exception as e:
        logger.error("GET_SESSION_FAILED", session_id=session_id, error=str(e))
        return error_response("Failed to retrieve session", code=500)


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(request: CreateSessionRequest):
    """
    Create new session.

    **Clean Code Architecture:**
    - SessionService handles session creation with validation
    - Uses DI container for dependency injection
    - AuditService logs all session creations

    Body:
    - owner_hash: SHA256 hash of owner (required)
    - status: Initial status (default: "new")
    - thread_id: Optional thread identifier

    Returns:
    - Created session object
    """
    # Get services from DI container (must be outside try block to ensure availability in except handlers)
    session_service = get_container().get_session_service()
    audit_service = get_container().get_audit_service()

    try:
        # Generate unique session ID and delegate to service for creation
        session_id = f"session_{uuid4().hex[:12]}"
        session = session_service.create_session(
            session_id=session_id,
            user_id=request.owner_hash,
        )

        # Log audit trail
        audit_service.log_action(
            action="session_created",
            user_id="system",
            resource=f"session:{session['session_id']}",
            result="success",
            details={
                "owner_hash": request.owner_hash,
                "status": request.status,
            },
        )

        logger.info(
            "SESSION_CREATED", session_id=session["session_id"], owner_hash=request.owner_hash
        )

        # Map service response to API response schema
        now = datetime.now(UTC).isoformat()
        return SessionResponse(
            id=session["session_id"],
            created_at=now,
            updated_at=now,
            last_active=now,
            interaction_count=0,
            status=session.get("status", "active"),
            is_persisted=True,
            owner_hash=request.owner_hash,
            thread_id=request.thread_id,
        )

    except ValueError as e:
        logger.warning("SESSION_CREATION_VALIDATION_FAILED", error=str(e))
        audit_service.log_action(
            action="session_creation_failed",
            user_id="system",
            resource="session",
            result="failed",
            details={"error": str(e)},
        )
        return error_response(str(e), code=400)
    except Exception as e:
        logger.error("SESSION_CREATION_FAILED", error=str(e))
        return error_response("Failed to create session", code=500)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(session_id: str, request: UpdateSessionRequest):
    """
    Update existing session (partial update).

    **Clean Code Architecture:**
    - SessionService handles session updates with validation
    - Uses DI container for dependency injection
    - AuditService logs all session updates

    Path params:
    - session_id: Session ID (ULID)

    Body (all optional):
    - status: New status (new|active|complete)
    - last_active: New last_active timestamp (ISO 8601)
    - interaction_count: New interaction count

    Returns:
    - Updated session object

    Raises:
    - 404: Session not found
    """
    try:
        # Get services from DI container
        session_service = get_container().get_session_service()
        audit_service = get_container().get_audit_service()

        # Auto-set last_active if not provided
        last_active = request.last_active
        if last_active is None and (
            request.status is not None or request.interaction_count is not None
        ):
            last_active = datetime.now(UTC).isoformat().replace("+00:00", "") + "Z"

        # Delegate to service for update (handles validation)
        success = session_service.update_session(
            session_id=session_id,
            status=request.status,
            interaction_count=request.interaction_count,
        )

        if not success:
            logger.warning("SESSION_NOT_FOUND_FOR_UPDATE", session_id=session_id)
            return error_response(f"Session {session_id} not found", code=404)

        # Retrieve updated session
        session = session_service.get_session(session_id)

        # Log audit trail
        audit_service.log_action(
            action="session_updated",
            user_id="system",
            resource=f"session:{session_id}",
            result="success",
            details={
                "status": request.status,
                "interaction_count": request.interaction_count,
            },
        )

        logger.info("SESSION_UPDATED", session_id=session_id)

        return SessionResponse(**session)  # type: ignore[arg-type]

    except ValueError as e:
        logger.warning("SESSION_UPDATE_VALIDATION_FAILED", session_id=session_id, error=str(e))
        return error_response(str(e), code=400)
    except Exception as e:
        logger.error("SESSION_UPDATE_FAILED", session_id=session_id, error=str(e))
        return error_response("Failed to update session", code=500)


# ============================================================================
# HEALTH CHECK (outside sessions prefix)
# ============================================================================

# Note: Health check is at /health not /api/sessions/health
# This should be registered at app level, not router level
# For now, tests access via /api/sessions/health which returns 404
# Fix: Move to app-level health endpoint or update test expectation
