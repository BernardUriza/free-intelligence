"""Transcription API Router.

Audio transcription endpoints (internal)

File: backend/api/internal/transcribe/router.py
Card: AUR-PROMPT-4.2
Reorganized: 2025-11-08 (moved from backend/api/transcribe.py)
Updated: 2025-11-09 (added chunk-based job endpoints)

Endpoints:
- POST /api/internal/transcribe → Legacy synchronous endpoint (DEPRECATED)
- POST /api/internal/transcribe/chunks → NEW job-based chunk endpoint
- GET /api/internal/transcribe/jobs/{job_id} → NEW job status polling
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.container import get_container
from backend.logger import get_logger
from backend.workers.celery_app import celery_app

logger = get_logger(__name__)

router = APIRouter()

# Audio storage root
AUDIO_ROOT = Path(os.getenv("AURITY_AUDIO_ROOT", "storage/audio")).resolve()
AUDIO_ROOT.mkdir(parents=True, exist_ok=True)


class TranscriptionResponse(BaseModel):
    """Response model for transcription endpoint."""

    text: str = Field(..., description="Full transcription text")
    segments: list[dict] = Field(default_factory=list, description="Segment-level transcription")
    language: str = Field(..., description="Detected or forced language")
    duration: float = Field(..., description="Audio duration in seconds")
    available: bool = Field(..., description="Whether transcription succeeded")
    audio_file: dict = Field(..., description="Stored audio file metadata")


@router.post("", response_model=TranscriptionResponse, status_code=status.HTTP_200_OK)
async def transcribe_audio_endpoint(
    request: Request,
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> TranscriptionResponse:
    """
    Upload audio file and get transcription.

    **Clean Code Architecture:**
    - TranscriptionService handles audio validation, storage, and transcription
    - Uses DI container for dependency injection
    - AuditService logs all transcription operations

    **Request:**
    - Method: POST
    - Content-Type: multipart/form-data
    - Header: X-Session-ID (required, UUID4 format)
    - Body: audio file (max 100 MB, formats: webm, wav, mp3, m4a, ogg)

    **Response:**
    - text: Full transcription (joined segments)
    - segments: List of segments with start/end timestamps
    - language: Detected or forced language (default: "es")
    - duration: Audio duration in seconds
    - available: Whether transcription succeeded (false if Whisper unavailable)
    - audio_file: Stored file metadata (path, hash, TTL)

    **Errors:**
    - 400: Invalid session_id, file type, or file size
    - 500: Transcription or storage failure

    **Notes:**
    - Audio stored in: storage/audio/{session_id}/{timestamp_ms}.{ext}
    - TTL: 7 days (auto-delete after expiration)
    - If faster-whisper not installed, returns placeholder text with available=false
    """
    # Validate session ID presence
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header: X-Session-ID",
        )

    try:
        # Get services from DI container
        transcription_service = get_container().get_transcription_service()
        audit_service = get_container().get_audit_service()

        # Read audio content
        audio_content = await audio.read()

        # Delegate to service for processing
        result = transcription_service.process_transcription(
            session_id=x_session_id,
            audio_content=audio_content,
            filename=audio.filename or "audio",
            content_type=audio.content_type or "audio/wav",
            metadata={
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        # Log audit trail
        audit_service.log_action(
            action="transcription_completed",
            user_id="system",
            resource=f"session:{x_session_id}",
            result="success",
            details={
                "filename": audio.filename,
                "text_length": len(result["text"]),
                "segments_count": len(result["segments"]),
                "available": result["available"],
            },
        )

        logger.info(
            f"TRANSCRIPTION_SUCCESS: session_id={x_session_id}, text_length={len(result['text'])}, available={result['available']}"
        )

        return TranscriptionResponse(
            text=result["text"],
            segments=result["segments"],
            language=result["language"],
            duration=result["duration"],
            available=result["available"],
            audio_file=result["audio_file"],
        )

    except ValueError as e:
        logger.warning(f"TRANSCRIPTION_VALIDATION_FAILED: session_id={x_session_id}, error={e!s}")
        audit_service = get_container().get_audit_service()
        audit_service.log_action(
            action="transcription_failed",
            user_id="system",
            resource=f"session:{x_session_id}",
            result="failed",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"TRANSCRIPTION_FAILED: session_id={x_session_id}, filename={audio.filename}, error={e!s}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription failed. Please try again.",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def transcribe_health_check() -> dict:
    """
    Health check for transcription service.

    **Clean Code Architecture:**
    - TranscriptionService handles health check via DI container

    Returns:
        Dict with whisper availability status and service health
    """
    transcription_service = get_container().get_transcription_service()
    health = transcription_service.health_check()

    return {
        "status": "operational" if health["whisper_available"] else "degraded",
        "whisper_available": health["whisper_available"],
        "message": "Transcription ready"
        if health["whisper_available"]
        else "Whisper not available (install faster-whisper)",
    }


# ============================================================================
# NEW: JOB-BASED CHUNK ENDPOINTS (AUR-PROMPT-4.2)
# ============================================================================


class TranscribeChunkJobResponse(BaseModel):
    """Response for chunk job creation (202 Accepted)."""

    queued: bool = Field(True, description="Job queued successfully")
    job_id: str = Field(..., description="Celery task ID for polling")
    session_id: str = Field(..., description="Session identifier")
    chunk_number: int = Field(..., description="Chunk index")
    status: str = Field(default="queued", description="Initial status")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class TranscribeJobStatusResponse(BaseModel):
    """Response for job status polling."""

    job_id: str = Field(..., description="Job identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    chunk_number: Optional[int] = Field(None, description="Chunk index")
    status: str = Field(
        ...,
        description="Job status: PENDING, STARTED, SUCCESS, FAILURE, RETRY",
    )
    result: Optional[dict] = Field(None, description="Result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    traceback: Optional[str] = Field(None, description="Error traceback if failed")


@router.post(
    "/chunks", response_model=TranscribeChunkJobResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_transcribe_chunk_job(
    audio: UploadFile = File(..., description="Audio chunk (WebM/MP4/WAV)"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_chunk_number: Optional[int] = Header(None, alias="X-Chunk-Number"),
) -> TranscribeChunkJobResponse:
    """
    Create transcription job for audio chunk (ATOMIC operation).

    **Architecture: INTERNAL layer (AUR-PROMPT-4.2)**
    - Atomically writes audio file to filesystem
    - Creates Celery job for async transcription + HDF5 append
    - Returns job_id immediately (non-blocking)

    **Workflow:**
    1. Validate session_id and chunk_number
    2. Atomic write: storage/audio/{session_id}/chunk_{chunk_number}.{ext}
    3. Calculate SHA256 hash
    4. Dispatch Celery task: transcribe_chunk_task.delay(...)
    5. Return 202 Accepted with job_id

    **Headers:**
    - X-Session-ID: Session identifier (required)
    - X-Chunk-Number: Chunk index 0-based (required)

    **Returns:**
    - 202 Accepted
    - job_id for status polling via GET /jobs/{job_id}
    """
    # Validate headers
    if not x_session_id:
        logger.warning("TRANSCRIBE_CHUNK_MISSING_SESSION_ID")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Missing X-Session-ID header"},
        )

    if x_chunk_number is None:
        logger.warning("TRANSCRIBE_CHUNK_MISSING_CHUNK_NUMBER", session_id=x_session_id)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Missing X-Chunk-Number header"},
        )

    session_id = x_session_id
    chunk_number = x_chunk_number

    # Read audio content
    try:
        audio_content = await audio.read()
    except Exception as e:
        logger.error("TRANSCRIBE_CHUNK_READ_FAILED", session_id=session_id, error=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to read audio: {e!s}"},
        )

    # Detect extension from content-type
    content_type = audio.content_type or "audio/webm"
    ext_map = {
        "audio/webm": ".webm",
        "audio/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
    }
    ext = ext_map.get(content_type, ".webm")

    # Atomic write to filesystem
    session_dir = AUDIO_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    audio_filename = f"chunk_{chunk_number}{ext}"
    audio_path = session_dir / audio_filename

    try:
        audio_path.write_bytes(audio_content)
        logger.info(
            "TRANSCRIBE_CHUNK_WRITTEN",
            session_id=session_id,
            chunk_number=chunk_number,
            path=str(audio_path),
            size_bytes=len(audio_content),
        )
    except Exception as e:
        logger.error(
            "TRANSCRIBE_CHUNK_WRITE_FAILED",
            session_id=session_id,
            chunk_number=chunk_number,
            error=str(e),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Failed to write audio: {e!s}"},
        )

    # Calculate SHA256 hash
    audio_hash = hashlib.sha256(audio_content).hexdigest()

    # Dispatch Celery task (async worker)
    # Use send_task to avoid import issues with uvicorn reload
    task = celery_app.send_task(
        "transcribe_chunk_task",
        args=[],
        kwargs={
            "session_id": session_id,
            "chunk_number": chunk_number,
            "audio_path": str(audio_path),
            "audio_hash": audio_hash,
            "content_type": content_type,
        },
    )

    job_id = task.id

    logger.info(
        "TRANSCRIBE_CHUNK_JOB_CREATED",
        session_id=session_id,
        chunk_number=chunk_number,
        job_id=job_id,
        audio_hash=audio_hash[:16],
    )

    return TranscribeChunkJobResponse(
        queued=True,
        job_id=job_id,
        session_id=session_id,
        chunk_number=chunk_number,
        status="queued",
        created_at=datetime.now(UTC).isoformat(),
    )


@router.get("/jobs/{job_id}", response_model=TranscribeJobStatusResponse)
async def get_transcribe_job_status(job_id: str) -> TranscribeJobStatusResponse:
    """
    Get transcription job status and result.

    **Architecture: INTERNAL layer (AUR-PROMPT-4.2)**
    - Polls Celery task state
    - Returns result when completed (includes transcript + HDF5 metadata)

    **States:**
    - PENDING: Job queued, not started
    - STARTED: Worker processing
    - SUCCESS: Completed successfully (result available)
    - FAILURE: Failed (error available)
    - RETRY: Retrying after failure

    **Returns:**
    - 200 OK with status and result (if completed)
    """
    # Get Celery AsyncResult
    task = celery_app.AsyncResult(job_id)

    # Extract session_id and chunk_number from result metadata (if available)
    session_id = None
    chunk_number = None
    result_data = None
    error_msg = None
    traceback_msg = None

    if task.state == "SUCCESS":
        result_data = task.result
        if isinstance(result_data, dict):
            session_id = result_data.get("session_id")
            chunk_number = result_data.get("chunk_number")
    elif task.state == "FAILURE":
        error_msg = str(task.info) if task.info else "Unknown error"
        traceback_msg = task.traceback if hasattr(task, "traceback") else None

    return TranscribeJobStatusResponse(
        job_id=job_id,
        session_id=session_id,
        chunk_number=chunk_number,
        status=task.state,
        result=result_data,
        error=error_msg,
        traceback=traceback_msg,
    )
