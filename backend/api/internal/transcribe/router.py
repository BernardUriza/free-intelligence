"""Internal transcription API - Session-based chunk processing.

INTERNAL layer:
- Creates/updates TranscriptionJob (1 per session)
- Dispatches Celery workers for heavy processing
- Returns immediately (202 Accepted)

Architecture:
  PUBLIC → INTERNAL → WORKER

Storage:
  /sessions/{session_id}/jobs/transcription/{job_id}.json  (Job metadata)
  /sessions/{session_id}/production/chunks/chunk_{N}/      (Transcripts)
  /sessions/{session_id}/ml_ready/text/chunks/chunk_{N}/   (ML data)

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Architecture unification
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType
from backend.storage.task_repository import (
    ensure_task_exists,
    get_task_chunks,
    get_task_metadata,
    task_exists,
    update_task_metadata,
)

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
# Endpoints
# ============================================================================


@router.post("/chunks", response_model=ChunkUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_chunk(
    session_id: str = Form(...),
    chunk_number: int = Form(...),
    audio: UploadFile = File(...),
    timestamp_start: Optional[float] = Form(None),
    timestamp_end: Optional[float] = Form(None),
) -> ChunkUploadResponse:
    """Upload audio chunk for transcription.

    Creates or updates TranscriptionJob and dispatches Celery worker.

    Args:
        session_id: Session UUID (also used as job_id)
        chunk_number: Sequential chunk index (0, 1, 2, ...)
        audio: Audio file (WebM/WAV/MP3)
        timestamp_start: Optional chunk start time
        timestamp_end: Optional chunk end time

    Returns:
        ChunkUploadResponse with job status

    Flow:
        1. Load or create TranscriptionJob
        2. Add ChunkMetadata (status="pending")
        3. Save to HDF5 (JobRepository)
        4. Dispatch Celery task
        5. Return 202 Accepted
    """
    try:
        audio_bytes = await audio.read()
        audio_size = len(audio_bytes)

        logger.info(
            "CHUNK_UPLOAD_RECEIVED",
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=audio_size,
        )

        # 1. Ensure TRANSCRIPTION task exists (allow existing)
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            allow_existing=True,
        )

        # 2. Get current metadata
        metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)
        if not metadata:
            metadata = {
                "job_id": session_id,
                "status": TaskStatus.PENDING.value,
                "total_chunks": 0,
                "processed_chunks": 0,
                "progress_percent": 0,
            }

        # 3. Update chunk count if this is a new chunk
        existing_chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)
        chunk_numbers = [c.get("chunk_number", -1) for c in existing_chunks]

        if chunk_number not in chunk_numbers:
            metadata["total_chunks"] = metadata.get("total_chunks", 0) + 1
            update_task_metadata(session_id, TaskType.TRANSCRIPTION, metadata)

        logger.info(
            "TASK_READY_FOR_PROCESSING",
            session_id=session_id,
            chunk_number=chunk_number,
            total_chunks=metadata["total_chunks"],
        )

        # 4. Dispatch Celery task (worker will write to HDF5)
        from backend.workers.transcription_tasks import transcribe_chunk_task

        task = transcribe_chunk_task.delay(  # type: ignore[attr-defined]
            session_id=session_id,
            chunk_number=chunk_number,
            audio_bytes=audio_bytes,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

        logger.info(
            "CELERY_TASK_DISPATCHED",
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=task.id,
        )

        # 5. Return 202 Accepted
        return ChunkUploadResponse(
            session_id=session_id,
            job_id=session_id,
            chunk_number=chunk_number,
            status="pending",
            total_chunks=metadata["total_chunks"],
            processed_chunks=metadata.get("processed_chunks", 0),
        )

    except Exception as e:
        logger.error(
            "CHUNK_UPLOAD_FAILED",
            session_id=session_id,
            chunk_number=chunk_number,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload chunk: {e!s}",
        ) from e


@router.get("/jobs/{session_id}", response_model=TranscriptionJobResponse)
async def get_transcription_job(session_id: str) -> TranscriptionJobResponse:
    """Get transcription job status with all chunks (task-based)."""
    try:
        # 1. Check if task exists
        if not task_exists(session_id, TaskType.TRANSCRIPTION):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcription job not found for session {session_id}",
            )

        # 2. Get task metadata
        metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)
        if not metadata:
            metadata = {}

        # Ensure job_id is set
        if "job_id" not in metadata or metadata["job_id"] is None:
            metadata["job_id"] = session_id

        # 3. Get all chunks
        chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)

        # 4. Calculate stats from chunks
        total_chunks = len(chunks)
        processed_chunks = sum(1 for c in chunks if c.get("status") == "completed")
        progress_percent = int(processed_chunks / total_chunks * 100) if total_chunks > 0 else 0

        # Determine overall status
        if processed_chunks == 0:
            job_status = TaskStatus.PENDING.value
        elif processed_chunks < total_chunks:
            job_status = TaskStatus.IN_PROGRESS.value
        else:
            job_status = TaskStatus.COMPLETED.value

        # Update metadata with current stats
        metadata.update(
            {
                "total_chunks": total_chunks,
                "processed_chunks": processed_chunks,
                "progress_percent": progress_percent,
                "status": job_status,
            }
        )

        return TranscriptionJobResponse(
            session_id=session_id,
            job_id=metadata.get("job_id", session_id),
            status=job_status,
            total_chunks=total_chunks,
            processed_chunks=processed_chunks,
            progress_percent=progress_percent,
            chunks=chunks,  # type: ignore[arg-type]
            created_at=metadata.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=metadata.get("updated_at", datetime.now(UTC).isoformat()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("GET_TRANSCRIPTION_JOB_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {e!s}",
        ) from e


@router.get("/jobs/{session_id}/chunks/{chunk_number}")
async def get_chunk_status(session_id: str, chunk_number: int) -> dict:
    """Get status of a specific chunk (task-based)."""
    try:
        # Get all chunks
        chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)

        # Find the specific chunk
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
    except Exception as e:
        logger.error("GET_CHUNK_STATUS_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chunk: {e!s}",
        ) from e
