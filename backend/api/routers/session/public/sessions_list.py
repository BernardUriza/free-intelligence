"""Lightweight Sessions List Endpoint - Direct HDF5 Read.

Simple, fast endpoint to list sessions without Timeline API overhead.
Reads directly from task-based HDF5 schema.

Author: Claude Code
Created: 2025-11-16
"""

from __future__ import annotations

from backend.api.audit.dependencies import get_audit_service
from backend.domain.session.dependencies import get_corpus_repository
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User, UserRole
from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class SessionListItem(BaseModel):
    """Lightweight session list item."""

    session_id: str = Field(..., description="Session UUID")
    created_at: str = Field(..., description="ISO timestamp")
    has_transcription: bool = Field(default=False)
    has_diarization: bool = Field(default=False)
    has_soap: bool = Field(default=False)
    chunk_count: int = Field(default=0, description="Number of transcription chunks")
    duration_seconds: float = Field(default=0.0, description="Total duration")
    preview: str = Field(default="", description="First chunk preview (max 200 chars)")
    patient_name: str = Field(
        default="Paciente", description="Patient name (extracted from dialogue or default)"
    )
    doctor_name: str = Field(default="", description="Doctor name (extracted from dialogue)")


class SessionsListResponse(BaseModel):
    """Response for sessions list."""

    sessions: list[SessionListItem] = Field(default_factory=list, description="List of sessions")
    total: int = Field(..., description="Total number of sessions")


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/sessions",
    response_model=SessionsListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    corpus_repo: ICorpusRepository = Depends(get_corpus_repository),
    audit_service=Depends(get_audit_service),
) -> SessionsListResponse:
    """List sessions from HDF5 (lightweight, fast) - FILTERED BY CLINIC_ID.

    Direct read from /sessions/{id}/tasks/ structure.
    Much faster than Timeline API for simple listing.

    Security:
    - Returns ONLY sessions from user's clinic (multi-tenancy isolation)
    - SUPERADMIN can see sessions from all clinics

    Args:
        limit: Maximum number of sessions to return (default 20)
        offset: Number of sessions to skip (default 0)
        current_user: Authenticated user from Auth0 JWT

    Returns:
        SessionsListResponse with session list (filtered by clinic_id)
    """
    try:
        # Multi-tenancy: Require clinic_id for non-SUPERADMIN users
        if UserRole.SUPERADMIN not in current_user.roles:
            if not current_user.clinic_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User has no clinic assigned. Cannot list sessions."
                )

        logger.info(
            "SESSIONS_LIST_STARTED",
            limit=limit,
            offset=offset,
            clinic_id=current_user.clinic_id,
            is_superadmin=UserRole.SUPERADMIN in current_user.roles,
        )

        # Get sessions filtered by clinic_id (or all if SUPERADMIN)
        filter_clinic_id = None if UserRole.SUPERADMIN in current_user.roles else current_user.clinic_id
        sessions_data, total = corpus_repo.list_all_sessions_with_metadata(
            limit, offset, clinic_id=filter_clinic_id
        )

        # Convert dicts to Pydantic models
        sessions_list = [SessionListItem(**session) for session in sessions_data]

        logger.info(
            "SESSIONS_LIST_SUCCESS",
            total=total,
            returned=len(sessions_list),
        )

        return SessionsListResponse(sessions=sessions_list, total=total)

    except Exception as e:
        # Audit failure for compliance tracking
        audit_service.log_action(
            action="sessions_listed",
            user_id=current_user.id,
            resource="list",
            result="failure",
            clinic_id=current_user.clinic_id,
            details={"error": str(e), "error_type": type(e).__name__, "limit": limit, "offset": offset},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {e!s}",
        ) from e
