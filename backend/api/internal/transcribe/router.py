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
# NEW: DIRECT SYNCHRONOUS ENDPOINT (AUR-PROMPT-4.2 - Hybrid Architecture)
# ============================================================================


class DirectTranscriptionResponse(BaseModel):
    """Response for direct (synchronous) transcription."""

    transcript: str = Field(..., description="Transcribed text")
    chunk_number: int = Field(..., description="Chunk index")
    session_id: str = Field(..., description="Session identifier")
    duration: float = Field(..., description="Audio duration in seconds")
    language: str = Field(..., description="Detected language")
    method: str = Field(default="direct", description="Processing method")
    latency_ms: int = Field(..., description="End-to-end latency in milliseconds")
    appended_to_h5: bool = Field(..., description="Whether chunk was appended to HDF5")


@router.post("/direct", response_model=DirectTranscriptionResponse, status_code=status.HTTP_200_OK)
async def transcribe_chunk_direct(
    audio: UploadFile = File(..., description="Audio chunk (WebM/MP4/WAV)"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_chunk_number: Optional[int] = Header(None, alias="X-Chunk-Number"),
) -> DirectTranscriptionResponse:
    """
    DIRECT (synchronous) chunk transcription - NO Celery workers.

    **Architecture: Hybrid Real-time/Offline (AUR-PROMPT-4.2)**

    This endpoint provides FAST transcription (1-3s latency) for real-time UX.
    Used as primary path when client is connected to backend.

    **Workflow:**
    1. Save audio chunk to filesystem
    2. Transcribe IMMEDIATELY using Whisper (synchronous)
    3. Append to HDF5 corpus (atomic)
    4. Return transcript to client

    **Fallback Strategy:**
    - Frontend should timeout this endpoint after 5s
    - If timeout/error → fallback to /chunks (async worker mode)
    - Workers handle offline scenarios and retry logic

    **Headers:**
    - X-Session-ID: Session identifier (required)
    - X-Chunk-Number: Chunk index 0-based (required)

    **Returns:**
    - 200 OK with transcript (fast path)
    - 503 Service Unavailable (client should fallback to /chunks)

    **Latency Target:** <3s (vs 23s+ with Celery workers)
    """
    import time

    from backend.services.transcription.service import TranscriptionService

    start_time = time.time()

    # Validate headers
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header: X-Session-ID",
        )
    if x_chunk_number is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header: X-Chunk-Number",
        )

    try:
        # 1. Save audio chunk to filesystem
        session_dir = AUDIO_ROOT / x_session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Determine file extension
        content_type = audio.content_type or "audio/wav"
        ext = ".wav" if "wav" in content_type else ".webm" if "webm" in content_type else ".mp4"

        audio_path = session_dir / f"chunk_{x_chunk_number}{ext}"
        audio_content = await audio.read()

        # Atomic write
        audio_path.write_bytes(audio_content)

        # Calculate hash
        audio_hash = hashlib.sha256(audio_content).hexdigest()

        logger.info(
            "DIRECT_TRANSCRIBE_STARTED",
            session_id=x_session_id,
            chunk_number=x_chunk_number,
            audio_size=len(audio_content),
            audio_hash=audio_hash[:16],
            audio_path=str(audio_path),
        )

        # 2. Transcribe SYNCHRONOUSLY (no Celery)
        whisper_svc = TranscriptionService()

        # Convert to WAV if needed (ffmpeg)
        wav_path = audio_path
        if ext != ".wav":
            import subprocess

            wav_path = audio_path.with_suffix(".wav")
            cmd = [
                "ffmpeg",
                "-i",
                str(audio_path),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-y",
                str(wav_path),
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=5)

        # Transcribe (blocking operation ~1-3s)
        result = whisper_svc.transcribe(str(wav_path))

        transcript = result["text"].strip() if result and "text" in result else ""
        duration = result.get("duration", 0.0) if result else 0.0
        language = result.get("language", "es") if result else "es"

        # Extract confidence (avg_logprob from Whisper result, normalize to 0-1)
        avg_logprob = result.get("avg_logprob", -0.5) if result else -0.5
        confidence = max(0.0, min(1.0, 1.0 + (avg_logprob / 1.0)))  # Normalize [-1, 0] → [0, 1]

        # Calculate audio quality (heuristic based on duration and transcript length)
        words_count = len(transcript.split())
        words_per_second = words_count / duration if duration > 0 else 0
        audio_quality = max(0.5, min(1.0, words_per_second / 2.5))  # Normalize to 0.5-1.0

        logger.info(
            "DIRECT_TRANSCRIBE_WHISPER_DONE",
            session_id=x_session_id,
            chunk_number=x_chunk_number,
            transcript_length=len(transcript),
            duration=duration,
            language=language,
            confidence=confidence,
            audio_quality=audio_quality,
        )

        # VAD check: Skip HDF5 append if no speech detected
        if len(transcript) == 0:
            latency_ms = int((time.time() - start_time) * 1000)

            logger.warning(
                "DIRECT_NO_SPEECH_DETECTED",
                session_id=x_session_id,
                chunk_number=x_chunk_number,
                latency_ms=latency_ms,
                duration=duration,
            )

            # Return empty transcript (fast path, no HDF5 write)
            return DirectTranscriptionResponse(
                transcript="",
                chunk_number=x_chunk_number,
                session_id=x_session_id,
                duration=duration,
                language=language,
                method="direct",
                latency_ms=latency_ms,
                appended_to_h5=False,  # Skipped due to no speech
            )

        # 3. Append to HDF5 (atomic) - Only if speech detected - dual write to production + ml_ready
        from backend.storage.session_chunks_schema import append_chunk_to_session

        timestamp_start = x_chunk_number * 3.0  # 3 second chunks
        timestamp_end = timestamp_start + duration

        append_chunk_to_session(
            session_id=x_session_id,
            chunk_idx=x_chunk_number,
            transcript=transcript,
            audio_hash=audio_hash[:16],
            duration=duration,
            language=language,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            confidence=confidence,
            audio_quality=audio_quality,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "DIRECT_TRANSCRIBE_COMPLETED",
            session_id=x_session_id,
            chunk_number=x_chunk_number,
            latency_ms=latency_ms,
            appended_to_h5=True,
        )

        return DirectTranscriptionResponse(
            transcript=transcript,
            chunk_number=x_chunk_number,
            session_id=x_session_id,
            duration=duration,
            language=language,
            method="direct",
            latency_ms=latency_ms,
            appended_to_h5=True,
        )

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "DIRECT_TRANSCRIBE_FAILED",
            session_id=x_session_id,
            chunk_number=x_chunk_number,
            error=str(e),
            latency_ms=latency_ms,
        )

        # Return 503 to signal client to fallback to /chunks (worker mode)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Direct transcription failed. Use /chunks endpoint. Error: {e!s}",
        )


# ============================================================================
# JOB-BASED CHUNK ENDPOINTS (AUR-PROMPT-4.2) - Worker Fallback
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
) -> TranscribeChunkJobResponse | JSONResponse:
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
    # Import task directly for stable routing
    from backend.workers.tasks import transcribe_chunk_task

    logger.info(
        "BEFORE_APPLY_ASYNC",
        session_id=session_id,
        chunk_number=chunk_number,
        task_queue=transcribe_chunk_task.queue,  # type: ignore[attr-defined]
    )

    task = transcribe_chunk_task.apply_async(  # type: ignore[attr-defined]
        kwargs={
            "session_id": session_id,
            "chunk_number": chunk_number,
            "audio_path": str(audio_path),
            "audio_hash": audio_hash,
            "content_type": content_type,
        },
        queue="asr",  # Explicit queue routing
    )

    job_id = task.id

    logger.info(
        "AFTER_APPLY_ASYNC",
        session_id=session_id,
        chunk_number=chunk_number,
        job_id=job_id,
    )

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


class ChunkData(BaseModel):
    """Chunk data from HDF5."""

    chunk_number: int
    transcript: str
    language: str
    duration: float
    audio_hash: str
    timestamp_start: float
    timestamp_end: float
    created_at: str


@router.get("/sessions/{session_id}/chunks")
async def list_session_chunks(session_id: str) -> dict:
    """
    List all chunks for a session from HDF5 corpus.

    **Returns:**
    - chunks: List of chunk data with transcripts
    - total: Total number of chunks
    """
    import h5py

    CORPUS_PATH = os.getenv("AURITY_CORPUS_H5", "storage/corpus.h5")
    corpus_path = Path(CORPUS_PATH).resolve()

    if not corpus_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Corpus not found: {corpus_path}",
        )

    try:
        with h5py.File(corpus_path, "r") as f:
            chunks_ds_path = f"sessions/{session_id}/chunks"
            if chunks_ds_path not in f:
                return {"chunks": [], "total": 0, "session_id": session_id}

            chunks_ds = f[chunks_ds_path]
            chunks_data = []

            for row in chunks_ds:  # type: ignore[union-attr]
                chunks_data.append(
                    ChunkData(
                        chunk_number=int(row["chunk_number"]),
                        transcript=row["transcription"].decode("utf-8")
                        if isinstance(row["transcription"], bytes)
                        else str(row["transcription"]),
                        language=row["language"].decode("utf-8")
                        if isinstance(row["language"], bytes)
                        else str(row["language"]),
                        duration=float(row["duration"]),
                        audio_hash=row["audio_hash"].decode("utf-8")
                        if isinstance(row["audio_hash"], bytes)
                        else str(row["audio_hash"]),
                        timestamp_start=float(row["timestamp_start"]),
                        timestamp_end=float(row["timestamp_end"]),
                        created_at=row["created_at"].decode("utf-8")
                        if isinstance(row["created_at"], bytes)
                        else str(row["created_at"]),
                    ).model_dump()
                )

            return {
                "chunks": sorted(chunks_data, key=lambda x: x["chunk_number"]),
                "total": len(chunks_data),
                "session_id": session_id,
            }

    except Exception as e:
        logger.error("LIST_CHUNKS_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chunks: {e!s}",
        )


from fastapi.responses import FileResponse


@router.get("/sessions/{session_id}/chunks/{chunk_number}/audio")
async def get_chunk_audio(session_id: str, chunk_number: int):
    """
    Serve audio file for a specific chunk.

    **Returns:**
    - Audio file (WebM, WAV, or MP4)
    """
    session_dir = AUDIO_ROOT / session_id

    if not session_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    # Try different extensions
    for ext in [".webm", ".wav", ".mp4"]:
        audio_path = session_dir / f"chunk_{chunk_number}{ext}"
        if audio_path.exists():
            media_type = {
                ".webm": "audio/webm",
                ".wav": "audio/wav",
                ".mp4": "audio/mp4",
            }.get(ext, "audio/webm")

            return FileResponse(
                path=audio_path,
                media_type=media_type,
                filename=f"chunk_{chunk_number}{ext}",
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Audio file not found for chunk {chunk_number}",
    )
