"""Sessions API Router.

Session CRUD operations with tenant isolation.

Python 2026 patterns:
- Annotated[T, Depends(...)] for cleaner DI
- `|` union syntax for type hints
- ConfigDict for Pydantic v2
- match/case for status validation

Endpoints:
- GET  /sessions - List sessions (tenant isolated)
- GET  /sessions/{id} - Get single session
- POST /sessions - Create session
- PATCH /sessions/{id} - Update session

Security:
- All operations use current_user.id for tenant isolation
- Ownership validation on read/update operations

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/session/internal/sessions/router.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.api.audit.services.audit_service import AuditService
from backend.domain.session.dependencies import get_audit_service, get_session_service
from backend.domain.session.services.session_service import SessionService
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain import User
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

type SessionStatus = Literal["new", "active", "complete"]


class SessionResponse(BaseModel):
    """Session response schema."""

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
    status: SessionStatus
    is_persisted: bool
    owner_hash: str
    thread_id: str | None = None


class SessionsListResponse(BaseModel):
    """Sessions list response with pagination."""

    items: list[SessionResponse]
    total: int
    limit: int
    offset: int


class CreateSessionRequest(BaseModel):
    """Create session request (owner_hash auto-set from auth)."""

    status: SessionStatus = "new"
    thread_id: str | None = None


class UpdateSessionRequest(BaseModel):
    """Update session request (partial)."""

    status: SessionStatus | None = None
    last_active: str | None = None
    interaction_count: int | None = Field(None, ge=0)


@router.get("", response_model=SessionsListResponse)
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List sessions with pagination (TENANT ISOLATED).

    Security:
    - MANDATORY tenant isolation via current_user.id
    - Users can ONLY see their own sessions
    - No cross-tenant data leaks
    """
    try:
        sessions = session_service.list_sessions(user_id=current_user.id)

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
        audit_service.log_action(
            action="sessions_list_failed",
            user_id=current_user.id,
            resource="sessions",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
):
    """Get single session by ID (OWNERSHIP VALIDATED).

    Security:
    - Validates that current_user owns the session
    - Returns 403 if user tries to access another user's session
    """
    try:
        session = await session_service.get_session_info(session_id)

        if not session:
            logger.warning("SESSION_NOT_FOUND", session_id=session_id)
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        session_owner = session.get("owner_hash") or session.get("id")

        if session_owner != current_user.id:
            logger.warning(
                "SESSION_ACCESS_DENIED",
                session_id=session_id,
                requested_by=current_user.id,
                owner=session_owner,
            )
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

        audit_service.log_action(
            action="session_retrieved",
            user_id=current_user.id,
            resource=f"session:{session_id}",
            result="success",
        )

        return SessionResponse(**session)

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("GET_SESSION_NOT_FOUND", session_id=session_id, error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        audit_service.log_action(
            action="session_retrieve_failed",
            user_id=current_user.id,
            resource=f"session:{session_id}",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: CreateSessionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
):
    """Create new session (OWNER AUTO-SET).

    Security:
    - owner_hash is AUTOMATICALLY set from current_user.id
    - Users can ONLY create sessions for themselves
    """
    try:
        session_id = f"session_{uuid4().hex[:12]}"
        session = session_service.create_session(
            session_id=session_id,
            user_id=current_user.id,
        )

        audit_service.log_action(
            action="session_created",
            user_id=current_user.id,
            resource=f"session:{session['session_id']}",
            result="success",
            details={"status": request.status},
        )

        logger.info("SESSION_CREATED", session_id=session["session_id"], user_id=current_user.id)

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
        audit_service.log_action(
            action="session_creation_failed",
            user_id=current_user.id,
            resource="session",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
):
    """Update existing session (partial update, OWNERSHIP VALIDATED).

    Security:
    - Validates that current_user owns the session before updating
    - Returns 403 if user tries to modify another user's session
    """
    try:
        try:
            existing_session = await session_service.get_session_info(session_id)
        except ValueError:
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

        success = session_service.update_session(
            session_id=session_id,
            status=request.status,
            interaction_count=request.interaction_count,
        )

        if not success:
            logger.warning("SESSION_NOT_FOUND_FOR_UPDATE", session_id=session_id)
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        session = await session_service.get_session_info(session_id)

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

        return SessionResponse(**session)

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("SESSION_UPDATE_VALIDATION_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        audit_service.log_action(
            action="session_update_failed",
            user_id=current_user.id,
            resource=f"session:{session_id}",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to update session")
