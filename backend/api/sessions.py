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
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.sessions_store import SessionsStore

# ============================================================================
# PYDANTIC MODELS (API contracts)
# ============================================================================


class SessionResponse(BaseModel):
    """Session response schema"""

    id: str
    created_at: str
    updated_at: str
    last_active: str
    interaction_count: int
    status: str  # new|active|complete
    is_persisted: bool
    owner_hash: str
    thread_id: Optional[str] = None

    class Config:
        json_schema_extra = {
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

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Initialize store
store = SessionsStore()


@router.get("", response_model=SessionsListResponse)
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    owner_hash: Optional[str] = Query(None),
):
    """
    List sessions with pagination.

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
    sessions = store.list(limit=limit, offset=offset, owner_hash=owner_hash)
    total = store.count(owner_hash=owner_hash)

    return SessionsListResponse(
        items=[SessionResponse(**s.to_dict()) for s in sessions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Get single session by ID.

    Path params:
    - session_id: Session ID (ULID)

    Returns:
    - Session object

    Raises:
    - 404: Session not found
    """
    session = store.get(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionResponse(**session.to_dict())


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(request: CreateSessionRequest):
    """
    Create new session.

    Body:
    - owner_hash: SHA256 hash of owner (required)
    - status: Initial status (default: "new")
    - thread_id: Optional thread identifier

    Returns:
    - Created session object
    """
    session = store.create(
        owner_hash=request.owner_hash,
        status=request.status,
        thread_id=request.thread_id,
    )

    return SessionResponse(**session.to_dict())


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(session_id: str, request: UpdateSessionRequest):
    """
    Update existing session (partial update).

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
    # Auto-set last_active if not provided
    last_active = request.last_active
    if last_active is None and (
        request.status is not None or request.interaction_count is not None
    ):
        last_active = datetime.now(UTC).isoformat() + "Z"

    session = store.update(
        session_id=session_id,
        status=request.status,
        last_active=last_active,
        interaction_count=request.interaction_count,
    )

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionResponse(**session.to_dict())


# ============================================================================
# HEALTH CHECK (outside sessions prefix)
# ============================================================================

# Note: Health check is at /health not /api/sessions/health
# This should be registered at app level, not router level
# For now, tests access via /api/sessions/health which returns 404
# Fix: Move to app-level health endpoint or update test expectation
