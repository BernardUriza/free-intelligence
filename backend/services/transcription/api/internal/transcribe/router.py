"""Internal transcription API - REFACTORED with Dependency Injection.

THIN ROUTER: All business logic delegated to DITranscriptionService.

INTERNAL layer:
- Creates/updates TranscriptionJob (1 per session)
- Dispatches synchronous workers for audio processing
- Returns immediately (202 Accepted)

Architecture:
  PUBLIC → INTERNAL → WORKER (sync)

Storage:
  /sessions/{session_id}/tasks/TRANSCRIPTION/  (Task-based HDF5)

Author: Bernard Uriza Orozco, Claude Code (refactored)
Created: 2025-11-14
Refactored: 2026-01-28 (Phase 2.3 - DI pattern)
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from __future__ import annotations

from backend.services.transcription.dependencies import get_transcription_service
from backend.services.transcription.services.di_transcription_service import (
    DITranscriptionService,
)
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

logger = get_logger(__name__)

router = APIRouter(tags=["internal-transcribe"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ChunkUploadResponse(BaseModel):
    """Response for chunk upload."""

    session_id: str = Field(..., description="Session identifier")
    job_id: str = Field(..., description="Job ID (same as session_id)")
    chunk_number: int = Field(..., description="Chunk number")
    status: str = Field(..., description="Job status: pending")
    total_chunks: int = Field(..., description="Total chunks in job")
    processed_chunks: int = Field(..., description="Chunks completed")


class TranscriptionJobResponse(BaseModel):
    """Response for job status."""

    session_id: str
    job_id: str
    status: str = Field(..., description="Union[pending, in_progress, completed] | failed")
    total_chunks: int
    processed_chunks: int
    progress_percent: int
    chunks: list[dict] = Field(..., description="List of chunk metadata")
    created_at: str
    updated_at: str


# ============================================================================
# Endpoints (THIN - business logic in DITranscriptionService)
# ============================================================================


@router.post("/chunks", response_model=ChunkUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_chunk(
    session_id: str = Form(...),
    chunk_number: int = Form(...),
    audio: UploadFile = File(...),
    timestamp_start: float | None = Form(None),
    timestamp_end: float | None = Form(None),
    service: DITranscriptionService = Depends(get_transcription_service),
) -> ChunkUploadResponse:
    """Upload audio chunk for transcription (THIN router - delegates to service).

    Args:
        session_id: Session UUID (also used as job_id)
        chunk_number: Sequential chunk index (0, 1, 2, ...)
        audio: Audio file (WebM/WAV/MP3)
        timestamp_start: Optional chunk start time
        timestamp_end: Optional chunk end time
        service: Transcription service (injected by FastAPI Depends)

    Returns:
        ChunkUploadResponse with job status (202 Accepted)

    Raises:
        HTTPException: 400 if validation fails, 500 if processing fails
    """
    try:
        # Read audio bytes
        audio_bytes = await audio.read()

        # Delegate to service (all business logic)
        result = await service.process_chunk(
            session_id=session_id,
            chunk_number=chunk_number,
            audio_bytes=audio_bytes,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

        # Map service result to API response
        return ChunkUploadResponse(
            session_id=result.session_id,
            job_id=result.task_id,
            chunk_number=result.chunk_number,
            status=result.status,
            total_chunks=result.total_chunks,
            processed_chunks=result.processed_chunks,
        )

    except ValueError as e:
        # Business validation error (400)
        logger.warning("CHUNK_VALIDATION_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except Exception as e:
        # Unexpected error (500)
        logger.error("CHUNK_UPLOAD_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload chunk: {e!s}",
        ) from e


@router.get("/jobs/{session_id}", response_model=TranscriptionJobResponse)
async def get_transcription_job(
    session_id: str,
    service: DITranscriptionService = Depends(get_transcription_service),
) -> TranscriptionJobResponse:
    """Get transcription job status (THIN router - delegates to service).

    Args:
        session_id: Session UUID
        service: Transcription service (injected by FastAPI Depends)

    Returns:
        TranscriptionJobResponse with status and chunks

    Raises:
        HTTPException: 404 if job not found, 500 if read fails
    """
    try:
        # Delegate to service (all business logic)
        result = await service.get_transcription_status(session_id=session_id)

        # Map service result to API response
        return TranscriptionJobResponse(
            session_id=result["session_id"],
            job_id=result["job_id"],
            status=result["status"],
            total_chunks=result["total_chunks"],
            processed_chunks=result["processed_chunks"],
            progress_percent=result["progress_percent"],
            chunks=result["chunks"],
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )

    except ValueError as e:
        # Job not found (404)
        logger.warning("TRANSCRIPTION_JOB_NOT_FOUND", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    except Exception as e:
        # Unexpected error (500)
        logger.error("GET_TRANSCRIPTION_JOB_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {e!s}",
        ) from e


@router.get("/jobs/{session_id}/chunks/{chunk_number}")
async def get_chunk_status(
    session_id: str,
    chunk_number: int,
    service: DITranscriptionService = Depends(get_transcription_service),
) -> dict:
    """Get status of a specific chunk (THIN router - delegates to service).

    Args:
        session_id: Session UUID
        chunk_number: Chunk index
        service: Transcription service (injected by FastAPI Depends)

    Returns:
        Chunk metadata dict

    Raises:
        HTTPException: 404 if chunk not found, 500 if read fails
    """
    try:
        # Get all chunks from service
        status_result = await service.get_transcription_status(session_id=session_id)
        chunks = status_result["chunks"]

        # Find specific chunk
        chunk = next((c for c in chunks if c.get("chunk_number") == chunk_number), None)

        if not chunk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk {chunk_number} not found for session {session_id}",
            )

        # Return chunk metadata
        return {
            "session_id": session_id,
            "chunk_number": chunk.get("chunk_number"),
            "status": chunk.get("status", "unknown"),
            "transcript": chunk.get("transcript"),
            "duration": chunk.get("duration"),
            "language": chunk.get("language"),
            "confidence": chunk.get("confidence"),
            "audio_quality": chunk.get("audio_quality"),
            "error_message": chunk.get("error_message"),
        }

    except HTTPException:
        # Re-raise HTTP exceptions (404)
        raise

    except ValueError as e:
        # Session not found (404)
        logger.warning("SESSION_NOT_FOUND", session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    except Exception as e:
        # Unexpected error (500)
        logger.error("GET_CHUNK_STATUS_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chunk: {e!s}",
        ) from e
