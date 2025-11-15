"""Aurity Workflow Orchestrator - PUBLIC layer (Clean Architecture).

PUBLIC layer (orchestrator):
- Uses Service layer for business logic
- NO direct HDF5 access (uses Repository via Service)
- Clean separation: Router → Service → Repository
- Returns job metadata immediately

Architecture:
  PUBLIC (this file) → SERVICE → REPOSITORY → HDF5
                          ↓
                       WORKER (Celery)

Best Practices 2024-2025:
- Dependency Injection for services
- Route handlers < 20 lines
- Business logic in Service layer
- Async/await without blocking

Endpoints:
- POST /stream → Upload audio chunk
- GET /jobs/{session_id} → Get transcription status

Author: Bernard Uriza Orozco
Created: 2025-11-10
Refactored: 2025-11-14 (Clean Architecture with Service Layer)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.dependencies import get_transcription_service
from backend.logger import get_logger
from backend.services.transcription_service import TranscriptionService

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows/aurity", tags=["workflows-aurity"])


# ============================================================================
# Response Models (for PUBLIC API)
# ============================================================================


class StreamChunkResponse(BaseModel):
    """Response for chunk upload."""

    session_id: str = Field(..., description="Session UUID (also job_id)")
    chunk_number: int = Field(..., description="Chunk number")
    status: str = Field(..., description="Status: pending")
    total_chunks: int = Field(..., description="Total chunks in session")
    processed_chunks: int = Field(..., description="Chunks completed")


class JobStatusResponse(BaseModel):
    """Response for job status polling."""

    session_id: str
    status: str = Field(..., description="pending | in_progress | completed | failed")
    total_chunks: int
    processed_chunks: int
    progress_percent: int
    chunks: list[dict] = Field(..., description="List of chunk metadata")


# ============================================================================
# Endpoints (Pure Orchestrators - use Service layer)
# ============================================================================


@router.post("/stream", response_model=StreamChunkResponse, status_code=status.HTTP_202_ACCEPTED)
async def stream_chunk(
    session_id: str = Form(...),
    chunk_number: int = Form(...),
    audio: UploadFile = File(...),  # noqa: B008
    timestamp_start: Optional[float] = Form(None),
    timestamp_end: Optional[float] = Form(None),
    service: TranscriptionService = Depends(get_transcription_service),
) -> StreamChunkResponse:
    """Upload audio chunk for transcription (orchestrator).

    PUBLIC layer: Uses Service layer for business logic

    Args:
        session_id: Session UUID
        chunk_number: Sequential chunk (0, 1, 2, ...)
        audio: Audio blob (WebM/WAV/MP3)
        timestamp_start: Optional chunk start time
        timestamp_end: Optional chunk end time
        service: Injected TranscriptionService

    Returns:
        StreamChunkResponse with session_id for polling

    Frontend:
        ```typescript
        const session_id = uuidv4()  // Create once
        await POST('/stream', {session_id, chunk_number: 0, audio})
        await pollUntilComplete(session_id)  // Session-based
        ```
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

        return StreamChunkResponse(
            session_id=result.session_id,
            chunk_number=result.chunk_number,
            status=result.status,
            total_chunks=result.total_chunks,
            processed_chunks=result.processed_chunks,
        )

    except ValueError as e:
        logger.error("VALIDATION_ERROR", session_id=session_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("CHUNK_UPLOAD_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chunk: {e!s}",
        ) from e


@router.get("/jobs/{session_id}", response_model=JobStatusResponse)
async def get_job_status(
    session_id: str,
    service: TranscriptionService = Depends(get_transcription_service),
) -> JobStatusResponse:
    """Poll transcription job status (orchestrator).

    PUBLIC layer: Uses Service layer for business logic

    Args:
        session_id: Session UUID
        service: Injected TranscriptionService

    Returns:
        JobStatusResponse with all chunks

    Frontend Polling:
        ```typescript
        async function pollJob(session_id: string, maxTime = 30000) {
          const start = Date.now()
          while (Date.now() - start < maxTime) {
            const {status, chunks} = await get(`/jobs/${session_id}`)
            if (status === 'completed') return chunks
            if (status === 'failed') throw new Error('Job failed')
            await sleep(500)  // Poll every 500ms
          }
        }
        ```
    """
    try:
        result = await service.get_transcription_status(session_id)
        return JobStatusResponse(**result)

    except ValueError as e:
        logger.error("SESSION_NOT_FOUND", session_id=session_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error("GET_JOB_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {e!s}",
        ) from e


@router.post("/end-session", status_code=status.HTTP_200_OK)
async def end_session(
    session_id: str = Form(...),
    full_audio: UploadFile = File(...),  # noqa: B008
) -> dict:
    """End session and save full audio file.

    Saves full audio to storage/audio/{session_id}/full.{ext}
    Updates HDF5 metadata with audio path.

    Args:
        session_id: Session UUID
        full_audio: Complete audio file (WebM/WAV/MP3)

    Returns:
        dict with audio_path, chunks_count, duration
    """
    from pathlib import Path

    try:
        # 1. Save audio to storage/audio/{session_id}/full.{ext}
        audio_dir = Path("storage/audio") / session_id
        audio_dir.mkdir(parents=True, exist_ok=True)

        mime = full_audio.content_type or "audio/webm"
        ext = (
            ".webm"
            if "webm" in mime
            else ".wav"
            if "wav" in mime
            else ".mp3"
            if "mp3" in mime
            else ".bin"
        )

        audio_path = audio_dir / f"full{ext}"
        audio_bytes = await full_audio.read()
        audio_path.write_bytes(audio_bytes)

        logger.info(
            "FULL_AUDIO_SAVED",
            session_id=session_id,
            path=str(audio_path),
            size_bytes=len(audio_bytes),
        )

        # 2. Get session info from HDF5
        from backend.storage.session_chunks_schema import (
            get_session_chunks,
            save_full_audio_metadata,
        )

        chunks = get_session_chunks(session_id)
        total_duration = sum(c["duration"] for c in chunks)
        total_chunks = len(chunks)

        # 3. Save metadata to HDF5
        relative_audio_path = f"storage/audio/{session_id}/full{ext}"
        save_full_audio_metadata(
            session_id=session_id,
            audio_path=relative_audio_path,
            total_duration=total_duration,
            total_chunks=total_chunks,
        )

        logger.info(
            "SESSION_ENDED",
            session_id=session_id,
            total_chunks=total_chunks,
            total_duration=total_duration,
        )

        return {
            "success": True,
            "session_id": session_id,
            "audio_path": f"/api/workflows/aurity/sessions/{session_id}/audio",
            "chunks_count": total_chunks,
            "duration": total_duration,
        }

    except Exception as e:
        logger.error("SESSION_END_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {e!s}",
        ) from e


@router.get("/sessions/{session_id}/audio", status_code=status.HTTP_200_OK)
async def get_session_audio(session_id: str):
    """Get full audio file for playback.

    Args:
        session_id: Session UUID

    Returns:
        Audio file (WebM/WAV/MP3)
    """
    from pathlib import Path

    import h5py

    try:
        metadata_path = f"/sessions/{session_id}/ml_ready/metadata/recording"
        corpus_path = Path("storage/corpus.h5")

        with h5py.File(corpus_path, "r") as f:
            if metadata_path not in f:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found",
                )

            metadata = f[metadata_path]
            if "full_audio_path" not in metadata:  # type: ignore[operator]
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} has no audio",
                )

            audio_path_str = metadata["full_audio_path"][()].decode("utf-8")

        audio_path = Path(audio_path_str)

        if not audio_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audio file not found: {audio_path}",
            )

        ext = audio_path.suffix.lower()
        media_type = (
            "audio/webm" if ext == ".webm" else "audio/wav" if ext == ".wav" else "audio/mpeg"
        )

        logger.info("SESSION_AUDIO_SERVED", session_id=session_id, path=str(audio_path))

        return FileResponse(
            path=str(audio_path),
            media_type=media_type,
            filename=f"session_{session_id}{ext}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("SESSION_AUDIO_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audio: {e!s}",
        ) from e


@router.get("/sessions/{session_id}/chunks", status_code=status.HTTP_200_OK)
async def get_session_chunks_api(
    session_id: str,
    service: TranscriptionService = Depends(get_transcription_service),
) -> dict:
    """Get all chunks for a session (orchestrator).

    Uses Service layer to get TranscriptionJob with all chunks.

    Args:
        session_id: Session UUID
        service: Injected TranscriptionService

    Returns:
        dict with chunks, total_duration, total_chunks
    """
    try:
        result = await service.get_transcription_status(session_id)
        chunks = result.get("chunks", [])
        total_duration = sum(c.get("duration", 0.0) for c in chunks if c.get("duration"))

        return {
            "session_id": session_id,
            "chunks": chunks,
            "total_duration": total_duration,
            "total_chunks": len(chunks),
        }

    except ValueError:
        # Session not found - return empty
        return {
            "session_id": session_id,
            "chunks": [],
            "total_duration": 0.0,
            "total_chunks": 0,
        }
    except Exception as e:
        logger.error("GET_CHUNKS_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chunks: {e!s}",
        ) from e
