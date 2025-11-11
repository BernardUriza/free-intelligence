"""Aurity Chunk Streaming - Clean Implementation.

Simple polling-based chunk transcription:
- POST /stream → Returns job_id immediately (202)
- Background thread processes Whisper + HDF5
- GET /jobs/{job_id} → Poll for status/transcript

Architecture:
- Frontend sends chunks → Gets job_id
- Frontend polls until completed/timeout
- Timeout chunks → Workers process with full MP3 later

File: backend/api/public/workflows/router_clean.py
Created: 2025-11-10 (cleanup - removed hybrid complexity)
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows/aurity", tags=["workflows-aurity"])

# In-memory job store (replace with Redis in production)
_job_store: dict[str, dict[str, Any]] = {}
_job_store_lock = threading.Lock()


class StreamChunkResponse(BaseModel):
    """Response for chunk upload."""

    job_id: str = Field(..., description="Job ID for polling")
    session_id: str = Field(..., description="Session identifier")
    chunk_number: int = Field(..., description="Chunk number")
    status: str = Field(..., description="Job status: pending")


class JobStatusResponse(BaseModel):
    """Response for job status polling."""

    job_id: str
    session_id: str
    chunk_number: int
    status: str = Field(..., description="pending | processing | completed | failed")
    transcript: Optional[str] = Field(None, description="Transcript (if completed)")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    language: Optional[str] = Field(None, description="Detected language")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    latency_ms: Optional[int] = Field(None, description="Processing time in ms")


def _process_chunk_background(
    job_id: str,
    session_id: str,
    chunk_number: int,
    audio_bytes: bytes,
) -> None:
    """
    Background thread: Whisper transcription + HDF5 append.

    Updates job store with status: pending → processing → completed/failed
    """
    import hashlib
    import subprocess
    import tempfile
    from pathlib import Path

    start_time = time.time()

    try:
        # Update status: processing
        with _job_store_lock:
            _job_store[job_id]["status"] = "processing"

        logger.info(
            "CHUNK_PROCESSING_STARTED",
            job_id=job_id,
            session_id=session_id,
            chunk_number=chunk_number,
        )

        # 1. Save audio to temp file
        audio_hash = hashlib.sha256(audio_bytes).hexdigest()[:16]
        temp_dir = Path(tempfile.gettempdir()) / "fi_chunks"
        temp_dir.mkdir(exist_ok=True)

        audio_path = temp_dir / f"{job_id}.webm"
        audio_path.write_bytes(audio_bytes)

        # 2. Convert to WAV for Whisper
        wav_path = temp_dir / f"{job_id}.wav"
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav_path),
        ]
        subprocess.run(ffmpeg_cmd, check=True, timeout=30)

        logger.info("CHUNK_WAV_CONVERTED", job_id=job_id, wav_size=wav_path.stat().st_size)

        # 3. Whisper transcription
        from backend.services.transcription.whisper import transcribe_audio

        result = transcribe_audio(str(wav_path), language=None, vad_filter=True)

        transcript = result.get("text", "").strip()
        duration = result.get("duration", 0.0)
        language = result.get("language", "unknown")

        logger.info(
            "CHUNK_WHISPER_DONE",
            job_id=job_id,
            transcript_length=len(transcript),
            duration=duration,
            language=language,
        )

        # 4. Append to HDF5 (if transcript not empty)
        if len(transcript) > 0:
            from backend.storage.session_chunks_schema import append_chunk_to_session

            timestamp_start = chunk_number * 3.0
            timestamp_end = timestamp_start + duration

            append_chunk_to_session(
                session_id=session_id,
                chunk_idx=chunk_number,
                transcript=transcript,
                audio_hash=audio_hash,
                duration=duration,
                language=language,
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
            )

            logger.info(
                "CHUNK_HDF5_APPENDED",
                job_id=job_id,
                session_id=session_id,
                chunk_number=chunk_number,
            )

        # 5. Update job: completed
        latency_ms = int((time.time() - start_time) * 1000)

        with _job_store_lock:
            _job_store[job_id].update(
                {
                    "status": "completed",
                    "transcript": transcript,
                    "duration": duration,
                    "language": language,
                    "latency_ms": latency_ms,
                }
            )

        logger.info(
            "CHUNK_PROCESSING_COMPLETED",
            job_id=job_id,
            latency_ms=latency_ms,
        )

        # Cleanup
        audio_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "CHUNK_PROCESSING_FAILED",
            job_id=job_id,
            error=str(e),
            latency_ms=latency_ms,
        )

        with _job_store_lock:
            _job_store[job_id].update(
                {
                    "status": "failed",
                    "error": str(e),
                    "latency_ms": latency_ms,
                }
            )


@router.post("/stream", response_model=StreamChunkResponse, status_code=status.HTTP_202_ACCEPTED)
async def stream_chunk(
    session_id: str = Form(...),
    chunk_number: int = Form(...),
    audio: UploadFile = File(...),  # noqa: B008
) -> StreamChunkResponse:
    """
    Upload audio chunk for transcription.

    **Flow:**
    1. Receive chunk → Generate job_id
    2. Launch background thread (Whisper + HDF5)
    3. Return 202 with job_id immediately

    **Args:**
    - session_id: Session UUID
    - chunk_number: Sequential chunk (0, 1, 2, ...)
    - audio: Audio blob from RecordRTC

    **Returns:**
    - job_id: Poll with GET /jobs/{job_id}
    - status: "pending" (will become "completed" or "failed")

    **Frontend:**
    ```typescript
    const {job_id} = await post('/stream', chunk)
    const transcript = await pollUntilComplete(job_id, {maxTime: 30000})
    if (timeout) cancel(job_id) // Let workers handle
    ```
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Read audio bytes
        audio_bytes = await audio.read()

        logger.info(
            "CHUNK_RECEIVED",
            job_id=job_id,
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=len(audio_bytes),
        )

        # Store job metadata
        with _job_store_lock:
            _job_store[job_id] = {
                "job_id": job_id,
                "session_id": session_id,
                "chunk_number": chunk_number,
                "status": "pending",
                "transcript": None,
                "duration": None,
                "language": None,
                "error": None,
                "latency_ms": None,
                "created_at": time.time(),
            }

        # Launch background processing
        thread = threading.Thread(
            target=_process_chunk_background,
            args=(job_id, session_id, chunk_number, audio_bytes),
            daemon=True,
        )
        thread.start()

        logger.info("CHUNK_JOB_CREATED", job_id=job_id, thread_id=thread.ident)

        return StreamChunkResponse(
            job_id=job_id,
            session_id=session_id,
            chunk_number=chunk_number,
            status="pending",
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
            detail=f"Failed to create chunk job: {e!s}",
        ) from e


@router.get("/jobs/{job_id}", response_model=JobStatusResponse, status_code=status.HTTP_200_OK)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Poll job status (for frontend polling loop).

    **Args:**
    - job_id: Job ID from POST /stream

    **Returns:**
    - status: "pending" | "processing" | "completed" | "failed"
    - transcript: Transcript text (if completed)
    - duration: Audio duration (if completed)
    - latency_ms: Processing time (if completed/failed)

    **Frontend Polling:**
    ```typescript
    async function pollJob(job_id: string, maxTime = 30000) {
      const start = Date.now()
      while (Date.now() - start < maxTime) {
        const {status, transcript} = await get(`/jobs/${job_id}`)
        if (status === 'completed') return transcript
        if (status === 'failed') throw new Error('Job failed')
        await sleep(500) // Poll every 500ms
      }
      throw new Error('Timeout')
    }
    ```
    """
    with _job_store_lock:
        job = _job_store.get(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return JobStatusResponse(**job)
