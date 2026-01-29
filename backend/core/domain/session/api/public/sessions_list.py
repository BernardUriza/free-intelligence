"""Lightweight Sessions List Endpoint - Direct HDF5 Read.

Simple, fast endpoint to list sessions without Timeline API overhead.
Reads directly from task-based HDF5 schema.

Author: Claude Code
Created: 2025-11-16
"""

from __future__ import annotations

from backend.core.domain.session.dependencies import get_corpus_repository
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
    corpus_repo: ICorpusRepository = Depends(get_corpus_repository),
) -> SessionsListResponse:
    """List sessions from HDF5 (lightweight, fast).

    Direct read from /sessions/{id}/tasks/ structure.
    Much faster than Timeline API for simple listing.

    Args:
        limit: Maximum number of sessions to return (default 20)
        offset: Number of sessions to skip (default 0)

    Returns:
        SessionsListResponse with session list
    """
    try:
        logger.info("SESSIONS_LIST_STARTED", limit=limit, offset=offset)

        # Get all sessions with metadata via repository (injected)
        sessions_data, total = corpus_repo.list_all_sessions_with_metadata(limit, offset)

        # Convert dicts to Pydantic models
        sessions_list = [SessionListItem(**session) for session in sessions_data]

        logger.info(
            "SESSIONS_LIST_SUCCESS",
            total=total,
            returned=len(sessions_list),
        )

        return SessionsListResponse(sessions=sessions_list, total=total)

    except Exception as e:
        logger.error("SESSIONS_LIST_FAILED", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {e!s}",
        ) from e
