"""Transcription Workflow Endpoints - Stream, Jobs, Chunks.

PUBLIC layer endpoints for audio transcription:
- POST /stream → Upload audio chunk
- GET /jobs/{session_id} → Get transcription status
- GET /sessions/{session_id}/chunks → Get all chunks
- POST /end-session → Save full audio + webspeech transcripts

Architecture:
  PUBLIC (this file) → SERVICE → REPOSITORY → HDF5

Author: Bernard Uriza Orozco
Created: 2025-11-15 (Refactored from monolithic router)
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.dependencies import get_transcription_service
from backend.logger import get_logger
from backend.services.transcription_service import TranscriptionService

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
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
    status: str = Field(..., description="Union[pending, in_progress, completed] | failed")
    total_chunks: int
    processed_chunks: int
    progress_percent: int
    chunks: list[dict] = Field(..., description="List of chunk metadata")


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/stream", response_model=StreamChunkResponse, status_code=status.HTTP_202_ACCEPTED)
async def stream_chunk(
    session_id: str = Form(...),
    chunk_number: int = Form(...),
    audio: UploadFile = File(...),  # noqa: B008
    mode: str = Form("medical"),  # NEW: "medical" | "chat" (default: medical for backward compat)
    timestamp_start: float | None = Form(None),
    timestamp_end: float | None = Form(None),
    patient_name: str | None = Form(None),
    patient_age: str | None = Form(None),
    patient_id: str | None = Form(None),
    chief_complaint: str | None = Form(None),
    service: TranscriptionService = Depends(get_transcription_service),
) -> StreamChunkResponse:
    """Upload audio chunk for transcription (mode-agnostic with Strategy Pattern).

    REFACTORED (2025-11-20): Uses ChunkHandler abstraction for medical/chat workflows.

    PUBLIC layer: Uses ChunkHandler + TranscriptionService for business logic

    Args:
        session_id: Session UUID (medical) or user-scoped ID (chat)
        chunk_number: Sequential chunk (0, 1, 2, ...)
        audio: Audio blob (WebM/WAV/MP3)
        mode: Workflow mode - "medical" (default) | "chat"
        timestamp_start: Optional chunk start time (medical only)
        timestamp_end: Optional chunk end time (medical only)
        patient_name: Patient name (medical only, first chunk)
        patient_age: Patient age (medical only, first chunk)
        patient_id: Patient ID (medical only, first chunk)
        chief_complaint: Chief complaint (medical only, first chunk)
        service: Injected TranscriptionService

    Returns:
        StreamChunkResponse with session_id for polling

    Medical workflow:
        ```typescript
        const session_id = uuidv4()  // Create once
        await POST('/stream', {session_id, chunk_number: 0, audio, mode: 'medical'})
        await pollUntilComplete(session_id)
        ```

    Chat workflow:
        ```typescript
        const session_id = `chat_${user.sub}`  // User-scoped
        await POST('/stream', {session_id, chunk_number: 0, audio, mode: 'chat'})
        // Transcript available immediately (no polling)
        ```
    """
    try:
        # 1. Get handler based on mode (Strategy Pattern)
        from backend.services.chunk_handler_factory import get_chunk_handler

        handler = get_chunk_handler(mode)

        # 2. Initialize session (first chunk only)
        if chunk_number == 0:
            metadata = {}
            if patient_name:
                metadata["patient_name"] = patient_name
            if patient_age:
                metadata["patient_age"] = patient_age
            if patient_id:
                metadata["patient_id"] = patient_id
            if chief_complaint:
                metadata["chief_complaint"] = chief_complaint

            await handler.initialize_session(session_id, metadata if metadata else None)

        # 3. Transcribe audio (SHARED LOGIC - STT load balancer)
        audio_bytes = await audio.read()
        transcript_result = await service.transcribe_audio(audio_bytes)

        # 4. Save chunk (strategy-specific: HDF5 vs in-memory)
        await handler.save_chunk(
            session_id=session_id,
            chunk_number=chunk_number,
            audio_bytes=audio_bytes,
            transcript=transcript_result.get("text", ""),
            metadata={
                "provider": transcript_result.get("provider", "unknown"),
                "confidence": transcript_result.get("confidence", 0.0),
                "timestamp": timestamp_start or 0.0,
                "timestamp_start": timestamp_start or 0.0,
                "timestamp_end": timestamp_end or 0.0,
                "duration": transcript_result.get("duration", 0.0),
                "language": transcript_result.get("language", "es-MX"),
            },
        )

        # 5. Get status for response
        status_dict = await handler.get_session_status(session_id)

        return StreamChunkResponse(
            session_id=session_id,
            chunk_number=chunk_number,
            status=status_dict["status"],
            total_chunks=status_dict["total_chunks"],
            processed_chunks=status_dict["processed_chunks"],
        )

    except ValueError as e:
        logger.error("VALIDATION_ERROR", session_id=session_id, mode=mode, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("CHUNK_UPLOAD_FAILED", session_id=session_id, mode=mode, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chunk: {e!s}",
        ) from e


@router.get("/jobs/{session_id}", response_model=JobStatusResponse)
async def get_job_status(
    session_id: str,
    service: TranscriptionService = Depends(get_transcription_service),
) -> JobStatusResponse:
    """Poll transcription job status (mode-agnostic with Strategy Pattern).

    REFACTORED (2025-11-20): Uses ChunkHandler abstraction for medical/chat workflows.

    PUBLIC layer: Uses ChunkHandler for business logic

    Args:
        session_id: Session UUID (medical) or user-scoped ID (chat)
        service: Injected TranscriptionService (unused - kept for backward compat)

    Returns:
        JobStatusResponse with all chunks

    Mode detection:
        - session_id starts with "chat_" → chat mode
        - otherwise → medical mode

    Frontend Polling:
        ```typescript
        // Medical (needs polling for worker completion)
        async function pollMedicalJob(session_id: string, maxTime = 30000) {
          const start = Date.now()
          while (Date.now() - start < maxTime) {
            const {status, chunks} = await get(`/jobs/${session_id}`)
            if (status === 'completed') return chunks
            if (status === 'failed') throw new Error('Job failed')
            await sleep(500)  // Poll every 500ms
          }
        }

        // Chat (immediate completion, no polling needed)
        const {status, chunks} = await get(`/jobs/chat_user_123`)
        // status is always 'completed'
        ```
    """
    try:
        # Detect mode from session_id prefix
        mode = "chat" if session_id.startswith("chat_") else "medical"

        # Get handler and delegate
        from backend.services.chunk_handler_factory import get_chunk_handler

        handler = get_chunk_handler(mode)
        status_dict = await handler.get_session_status(session_id)

        return JobStatusResponse(**status_dict)

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
    webspeech_final: str | None = Form(None),  # JSON string of webspeech transcripts
) -> dict:
    """End session and save full audio file + webspeech transcripts.

    Saves full audio to storage/audio/{session_id}/full.{ext}
    Saves webspeech_final to HDF5 TRANSCRIPTION task (Triple Vision source)
    Updates HDF5 metadata with audio path.

    Args:
        session_id: Session UUID
        full_audio: Complete audio file (WebM/WAV/MP3)
        webspeech_final: Optional JSON string of webspeech transcripts (for Triple Vision)

    Returns:
        dict with audio_path, chunks_count, duration
    """
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

        # 4. Save webspeech_final to HDF5 (Triple Vision source)
        if webspeech_final:
            from backend.models.task_type import TaskType
            from backend.storage.task_repository import CORPUS_PATH

            try:
                webspeech_list = json.loads(webspeech_final)
                logger.info(
                    "WEBSPEECH_RECEIVED",
                    session_id=session_id,
                    count=len(webspeech_list),
                )

                # Save to TRANSCRIPTION task
                with h5py.File(CORPUS_PATH, "a") as f:
                    webspeech_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}/webspeech_final"

                    # Delete if exists (overwrite)
                    if webspeech_path in f:
                        del f[webspeech_path]

                    # Save as JSON string
                    webspeech_json = json.dumps(webspeech_list)
                    f.create_dataset(webspeech_path, data=webspeech_json.encode("utf-8"))

                logger.info(
                    "WEBSPEECH_SAVED",
                    session_id=session_id,
                    count=len(webspeech_list),
                )
            except json.JSONDecodeError as e:
                logger.warning(
                    "WEBSPEECH_PARSE_FAILED",
                    session_id=session_id,
                    error=str(e),
                )
            except Exception as e:
                logger.error(
                    "WEBSPEECH_SAVE_FAILED",
                    session_id=session_id,
                    error=str(e),
                )

        logger.info(
            "SESSION_ENDED",
            session_id=session_id,
            total_chunks=total_chunks,
            total_duration=total_duration,
            webspeech_count=len(json.loads(webspeech_final)) if webspeech_final else 0,
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
