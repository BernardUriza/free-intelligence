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

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.models import ChunkMetadata, JobType, TranscriptionJob
from backend.repositories import job_repository

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
    status: str = Field(..., description="pending | in_progress | completed | failed")
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

        # 1. Load or create TranscriptionJob (session_id = job_id)
        job = job_repository.load(
            job_id=session_id,
            session_id=session_id,
            job_type=JobType.TRANSCRIPTION,
            job_class=TranscriptionJob,
        )

        if not job:
            job = TranscriptionJob.create_for_session(
                job_id=session_id,
                session_id=session_id,
                total_chunks=0,
            )
            logger.info("TRANSCRIPTION_JOB_CREATED", session_id=session_id)

        # 2. Add chunk metadata (pending)
        chunk_meta = ChunkMetadata(
            chunk_number=chunk_number,
            status="pending",
            audio_size_bytes=audio_size,
        )
        job.add_chunk(chunk_meta)

        # 3. Save to HDF5
        job_repository.save(job)

        logger.info(
            "CHUNK_METADATA_SAVED",
            session_id=session_id,
            chunk_number=chunk_number,
            total_chunks=job.total_chunks,
        )

        # 4. Dispatch Celery task
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
            total_chunks=job.total_chunks,
            processed_chunks=job.processed_chunks,
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
    """Get transcription job status with all chunks."""
    try:
        job = job_repository.load(
            job_id=session_id,
            session_id=session_id,
            job_type=JobType.TRANSCRIPTION,
            job_class=TranscriptionJob,
        )

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcription job not found for session {session_id}",
            )

        chunks_dict = [
            {
                "chunk_number": c.chunk_number,
                "status": c.status,
                "audio_size_bytes": c.audio_size_bytes,
                "audio_hash": c.audio_hash,
                "transcript": c.transcript,
                "duration": c.duration,
                "language": c.language,
                "confidence": c.confidence,
                "audio_quality": c.audio_quality,
                "timestamp_start": c.timestamp_start,
                "timestamp_end": c.timestamp_end,
                "created_at": c.created_at,
                "error_message": c.error_message,
            }
            for c in job.chunks
        ]

        return TranscriptionJobResponse(
            session_id=job.session_id,
            job_id=job.job_id,
            status=job.status.value,
            total_chunks=job.total_chunks,
            processed_chunks=job.processed_chunks,
            progress_percent=job.progress_percent,
            chunks=chunks_dict,
            created_at=job.created_at,
            updated_at=job.updated_at,
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
    """Get status of a specific chunk."""
    try:
        job = job_repository.load(
            job_id=session_id,
            session_id=session_id,
            job_type=JobType.TRANSCRIPTION,
            job_class=TranscriptionJob,
        )

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found for session {session_id}",
            )

        chunk = job.get_chunk(chunk_number)
        if not chunk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk {chunk_number} not found",
            )

        return {
            "session_id": session_id,
            "chunk_number": chunk.chunk_number,
            "status": chunk.status,
            "transcript": chunk.transcript,
            "duration": chunk.duration,
            "language": chunk.language,
            "confidence": chunk.confidence,
            "audio_quality": chunk.audio_quality,
            "error_message": chunk.error_message,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("GET_CHUNK_STATUS_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chunk: {e!s}",
        ) from e
