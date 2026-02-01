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

from datetime import UTC, datetime
from uuid import uuid4

from backend.api.audit.services.audit_service import AuditService
from backend.domain.session.dependencies import get_audit_service, get_session_service
from backend.domain.session.services.session_service import SessionService
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain import User
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

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
    status: str  # Union[new, active, complete]
    is_persisted: bool
    owner_hash: str
    thread_id: str | None = None


class SessionsListResponse(BaseModel):
    """Sessions list response with pagination"""

    items: list[SessionResponse]
    total: int
    limit: int
    offset: int


class CreateSessionRequest(BaseModel):
    """Create session request (owner_hash auto-set from auth)"""

    status: str = Field(default="new", pattern="^(Union[new, active, complete])$")
    thread_id: str | None = None


class UpdateSessionRequest(BaseModel):
    """Update session request (partial)"""

    status: str | None = Field(None, pattern="^(Union[new, active, complete])$")
    last_active: str | None = None
    interaction_count: int | None = Field(None, ge=0)


# ============================================================================
# FASTAPI ROUTER
# ============================================================================

router = APIRouter()


@router.get("", response_model=SessionsListResponse)
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    List sessions with pagination (TENANT ISOLATED).

    **Security:**
    - MANDATORY tenant isolation via current_user.id
    - Users can ONLY see their own sessions
    - No cross-tenant data leaks

    **Clean Code Architecture:**
    - SessionService handles session retrieval and filtering
    - Uses FastAPI Depends() for dependency injection

    Query params:
    - limit: Max sessions to return (1-100, default 50)
    - offset: Number of sessions to skip (default 0)

    Returns:
    - items: List of sessions (filtered by current_user)
    - total: Total count (with filters applied)
    - limit: Limit used
    - offset: Offset used
    """
    try:

        # CRITICAL: ALWAYS use current_user.id for tenant isolation
        # Never trust client-provided owner_hash
        sessions = session_service.list_sessions(user_id=current_user.id)

        # Log audit trail
        audit_service.log_action(
            action="sessions_listed",
            user_id=current_user.id,
            resource="sessions",
            result="success",
            details={"limit": limit, "tenant_isolated": True},
        )

        return SessionsListResponse(
            items=[SessionResponse(**s) for s in sessions],
            total=len(sessions),
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error("LIST_SESSIONS_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    Get single session by ID (OWNERSHIP VALIDATED).

    **Security:**
    - Validates that current_user owns the session
    - Returns 403 if user tries to access another user's session
    - Prevents unauthorized cross-tenant access

    **Clean Code Architecture:**
    - SessionService handles session retrieval
    - Uses FastAPI Depends() for dependency injection

    Path params:
    - session_id: Session ID (ULID)

    Returns:
    - Session object

    Raises:
    - 403: Access denied (not session owner)
    - 404: Session not found
    """
    try:

        # Delegate to service for retrieval
        # SessionService exposes `get_session_info`; use it here.
        session = await session_service.get_session_info(session_id)

        if not session:
            logger.warning("SESSION_NOT_FOUND", session_id=session_id)
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # CRITICAL: Validate ownership (tenant isolation)
        # Session owner_hash must match current_user.id
        session_owner = session.get("owner_hash") or session.get("id")  # Fallback to session_id if no owner_hash

        if session_owner != current_user.id:
            logger.warning(
                "SESSION_ACCESS_DENIED",
                session_id=session_id,
                requested_by=current_user.id,
                owner=session_owner,
            )
            # Log security incident
            audit_service.log_action(
                action="session_access_denied",
                user_id=current_user.id,
                resource=f"session:{session_id}",
                result="denied",
                details={"reason": "ownership_mismatch"},
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: You do not own this session"
            )

        # Log audit trail
        audit_service.log_action(
            action="session_retrieved",
            user_id=current_user.id,
            resource=f"session:{session_id}",
            result="success",
        )

        return SessionResponse(**session)

    except ValueError as e:
        logger.warning("GET_SESSION_NOT_FOUND", session_id=session_id, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("GET_SESSION_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    Create new session (OWNER AUTO-SET).

    **Security:**
    - owner_hash is AUTOMATICALLY set from current_user.id
    - Users can ONLY create sessions for themselves
    - Prevents session creation on behalf of other users

    **Clean Code Architecture:**
    - SessionService handles session creation with validation
    - Uses FastAPI Depends() for dependency injection
    - AuditService logs all session creations

    Body:
    - status: Initial status (default: "new")
    - thread_id: Optional thread identifier

    Returns:
    - Created session object
    """
    try:
        # Generate unique session ID and delegate to service for creation
        # CRITICAL: Use current_user.id as owner (NEVER trust client input)
        session_id = f"session_{uuid4().hex[:12]}"
        session = session_service.create_session(
            session_id=session_id,
            user_id=current_user.id,
        )

        # Log audit trail
        audit_service.log_action(
            action="session_created",
            user_id=current_user.id,
            resource=f"session:{session['session_id']}",
            result="success",
            details={
                "status": request.status,
            },
        )

        logger.info(
            "SESSION_CREATED", session_id=session["session_id"], user_id=current_user.id
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
            owner_hash=current_user.id,
            thread_id=request.thread_id,
        )

    except ValueError as e:
        logger.warning("SESSION_CREATION_VALIDATION_FAILED", error=str(e), user_id=current_user.id)
        audit_service.log_action(
            action="session_creation_failed",
            user_id=current_user.id,
            resource="session",
            result="failed",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("SESSION_CREATION_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    audit_service: AuditService = Depends(get_audit_service),
):
    """
    Update existing session (partial update, OWNERSHIP VALIDATED).

    **Security:**
    - Validates that current_user owns the session before updating
    - Returns 403 if user tries to modify another user's session
    - Prevents unauthorized cross-tenant modifications

    **Clean Code Architecture:**
    - SessionService handles session updates with validation
    - Uses FastAPI Depends() for dependency injection
    - AuditService logs all session updates

    Path params:
    - session_id: Session ID (ULID)

    Body (all optional):
    - status: New status (Union[new, active, complete])
    - last_active: New last_active timestamp (ISO 8601)
    - interaction_count: New interaction count

    Returns:
    - Updated session object

    Raises:
    - 403: Access denied (not session owner)
    - 404: Session not found
    """
    try:

        # CRITICAL: Validate ownership BEFORE allowing update
        try:
            existing_session = await session_service.get_session_info(session_id)
        except ValueError:
            # Session not found
            logger.warning("SESSION_NOT_FOUND_FOR_UPDATE", session_id=session_id)
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        session_owner = existing_session.get("owner_hash") or existing_session.get("id")

        if session_owner != current_user.id:
            logger.warning(
                "SESSION_UPDATE_DENIED",
                session_id=session_id,
                requested_by=current_user.id,
                owner=session_owner,
            )
            audit_service.log_action(
                action="session_update_denied",
                user_id=current_user.id,
                resource=f"session:{session_id}",
                result="denied",
                details={"reason": "ownership_mismatch"},
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: You do not own this session"
            )

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
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Retrieve updated session
        session = await session_service.get_session_info(session_id)

        # Log audit trail (already using AuditService - logger.info redundant removed)
        audit_service.log_action(
            action="session_updated",
            user_id=current_user.id,
            resource=f"session:{session_id}",
            result="success",
            details={
                "status": request.status,
                "interaction_count": request.interaction_count,
            },
        )

        return SessionResponse(**session)  # type: ignore[arg-type]

    except ValueError as e:
        logger.warning("SESSION_UPDATE_VALIDATION_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("SESSION_UPDATE_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update session")


# ============================================================================
# HEALTH CHECK (outside sessions prefix)
# ============================================================================

# Note: Health check is at /health not /api/sessions/health
# This should be registered at app level, not router level
# For now, tests access via /api/sessions/health which returns 404
# Fix: Move to app-level health endpoint or update test expectation
