"""Internal transcription API - REFACTORED with Dependency Injection.

THIN ROUTER: All business logic delegated to DITranscriptionService.

Python 2026 patterns:
- Annotated[T, Depends(...)] for cleaner DI
- `|` union syntax for type hints
- Literal types for status values

INTERNAL layer:
- Creates/updates TranscriptionJob (1 per session)
- Dispatches synchronous workers for audio processing
- Returns immediately (202 Accepted)

Architecture:
  PUBLIC -> INTERNAL -> WORKER (sync)

Storage:
  /sessions/{session_id}/tasks/TRANSCRIPTION/  (Task-based HDF5)

Endpoints:
- POST /chunks - Upload audio chunk
- GET /jobs/{session_id} - Get job status
- GET /jobs/{session_id}/chunks/{chunk_number} - Get chunk status

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/transcription/internal/transcribe/router.py
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.services.transcription.dependencies import get_transcription_service
from backend.services.transcription.services.di_transcription_service import DITranscriptionService
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["internal-transcribe"])

type JobStatus = Literal["pending", "in_progress", "completed", "failed"]


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
    status: JobStatus
    total_chunks: int
    processed_chunks: int
    progress_percent: int
    chunks: list[dict] = Field(..., description="List of chunk metadata")
    created_at: str
    updated_at: str


@router.post("/chunks", response_model=ChunkUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_chunk(
    service: Annotated[DITranscriptionService, Depends(get_transcription_service)],
    session_id: str = Form(...),
    chunk_number: int = Form(...),
    audio: UploadFile = File(...),
    timestamp_start: float | None = Form(None),
    timestamp_end: float | None = Form(None),
) -> ChunkUploadResponse:
    """Upload audio chunk for transcription (THIN router - delegates to service).

    Args:
        service: Transcription service (injected)
        session_id: Session UUID (also used as job_id)
        chunk_number: Sequential chunk index (0, 1, 2, ...)
        audio: Audio file (WebM/WAV/MP3)
        timestamp_start: Optional chunk start time
        timestamp_end: Optional chunk end time

    Returns:
        ChunkUploadResponse with job status (202 Accepted)

    Raises:
        HTTPException: 400 if validation fails, 500 if processing fails
    """
    try:
        audio_bytes = await audio.read()

        result = await service.process_chunk(
            session_id=session_id,
            chunk_number=chunk_number,
            audio_bytes=audio_bytes,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

        return ChunkUploadResponse(
            session_id=result.session_id,
            job_id=result.task_id,
            chunk_number=result.chunk_number,
            status=result.status,
            total_chunks=result.total_chunks,
            processed_chunks=result.processed_chunks,
        )

    except ValueError as e:
        logger.warning("CHUNK_VALIDATION_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except Exception as e:
        logger.error("CHUNK_UPLOAD_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload chunk: {e!s}",
        ) from e


@router.get("/jobs/{session_id}", response_model=TranscriptionJobResponse)
async def get_transcription_job(
    session_id: str,
    service: Annotated[DITranscriptionService, Depends(get_transcription_service)],
) -> TranscriptionJobResponse:
    """Get transcription job status (THIN router - delegates to service).

    Args:
        session_id: Session UUID
        service: Transcription service (injected)

    Returns:
        TranscriptionJobResponse with status and chunks

    Raises:
        HTTPException: 404 if job not found, 500 if read fails
    """
    try:
        result = await service.get_transcription_status(session_id=session_id)

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
        logger.warning("TRANSCRIPTION_JOB_NOT_FOUND", session_id=session_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    except Exception as e:
        logger.error("GET_TRANSCRIPTION_JOB_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {e!s}",
        ) from e


@router.get("/jobs/{session_id}/chunks/{chunk_number}")
async def get_chunk_status(
    session_id: str,
    chunk_number: int,
    service: Annotated[DITranscriptionService, Depends(get_transcription_service)],
) -> dict:
    """Get status of a specific chunk (THIN router - delegates to service).

    Args:
        session_id: Session UUID
        chunk_number: Chunk index
        service: Transcription service (injected)

    Returns:
        Chunk metadata dict

    Raises:
        HTTPException: 404 if chunk not found, 500 if read fails
    """
    try:
        status_result = await service.get_transcription_status(session_id=session_id)
        chunks = status_result["chunks"]

        chunk = next((c for c in chunks if c.get("chunk_number") == chunk_number), None)

        if not chunk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk {chunk_number} not found for session {session_id}",
            )

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
        raise

    except ValueError as e:
        logger.warning("SESSION_NOT_FOUND", session_id=session_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    except Exception as e:
        logger.error("GET_CHUNK_STATUS_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chunk: {e!s}",
        ) from e
