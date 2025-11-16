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

from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
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
    status: str = Field(..., description="Union[pending, in_progress, completed] | failed")
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


# ============================================================================
# Session Finalization & Diarization Workflow
# ============================================================================


class TranscriptionSourcesModel(BaseModel):
    """3 separate transcription sources for diarization."""

    webspeech_final: list[str] = Field(
        default_factory=list, description="WebSpeech instant previews"
    )
    transcription_per_chunks: list[dict] = Field(
        default_factory=list, description="Whisper per-chunk transcripts"
    )
    full_transcription: str = Field(default="", description="Concatenated full text")


class FinalizeSessionRequest(BaseModel):
    """Request to finalize session and start diarization."""

    transcription_sources: TranscriptionSourcesModel = Field(
        default_factory=TranscriptionSourcesModel,
        description="3 separate transcription sources",
    )


class FinalizeSessionResponse(BaseModel):
    """Response for session finalization."""

    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="finalized")
    encrypted_at: str = Field(..., description="ISO timestamp")
    diarization_job_id: str = Field(..., description="Celery task ID for diarization")
    message: str = Field(..., description="Human-readable message")


@router.post(
    "/sessions/{session_id}/diarization",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["workflows-sessions"],
)
async def diarize_session_workflow(
    session_id: str,
) -> dict:
    """Dispatch diarization worker (PUBLIC orchestrator).

    Flow:
    1. Create DIARIZATION task in HDF5
    2. Dispatch diarization worker in ThreadPoolExecutor (fire-and-forget)
    3. Frontend polls /sessions/{session_id}/monitor for status

    PUBLIC layer: Pure orchestrator - dispatches background task

    Args:
        session_id: Session UUID

    Returns:
        dict with job_id and status (202 Accepted)

    Raises:
        404: Session not found or no TRANSCRIPTION task
        400: Transcription not completed yet
        500: Worker dispatch failed
    """
    from backend.logger import get_logger
    from backend.models.task_type import TaskType
    from backend.storage.task_repository import ensure_task_exists
    from backend.workers.executor_pool import spawn_worker
    from backend.workers.tasks.diarization_worker import diarize_session_worker

    logger = get_logger(__name__)

    try:
        logger.info(
            "DIARIZATION_WORKFLOW_STARTED",
            session_id=session_id,
        )

        # 1. Create DIARIZATION task BEFORE dispatching worker
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.DIARIZATION,
            allow_existing=True,
        )
        logger.info(
            "DIARIZATION_TASK_CREATED",
            session_id=session_id,
        )

        # 2. Dispatch worker using ThreadPoolExecutor (fire-and-forget)
        spawn_worker(diarize_session_worker, session_id=session_id)
        job_id = session_id  # Use session_id as job identifier

        logger.info(
            "DIARIZATION_DISPATCHED",
            session_id=session_id,
            job_id=job_id,
        )

        # 3. Return 202 Accepted
        return {
            "session_id": session_id,
            "job_id": job_id,
            "status": "dispatched",
            "message": f"Diarization running in background (job {job_id}). Poll /sessions/{session_id}/monitor for progress.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "DIARIZATION_WORKFLOW_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch diarization: {e!s}",
        ) from e


@router.post(
    "/sessions/{session_id}/finalize",
    response_model=FinalizeSessionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["workflows-sessions"],
)
async def finalize_session_workflow(
    session_id: str,
    request: FinalizeSessionRequest,
) -> FinalizeSessionResponse:
    """Finalize session: encrypt audio (PUBLIC orchestrator).

    NOTE: This endpoint should only be called AFTER SOAP generation is complete.

    Flow:
    1. Call the INTERNAL finalize function DIRECTLY (no HTTP call)
    2. Encrypt session audio
    3. Return finalized status

    PUBLIC layer: Pure orchestrator - calls internal function directly

    Args:
        session_id: Session UUID
        request: FinalizeSessionRequest with 3 transcription sources

    Returns:
        FinalizeSessionResponse with encrypted_at timestamp (202 Accepted)

    Raises:
        404: Session not found or no TRANSCRIPTION task
        400: Transcription not completed yet
        500: Encryption or storage failed
    """
    from backend.api.internal.sessions.finalize import (
        finalize_session as internal_finalize,
    )
    from backend.logger import get_logger

    logger = get_logger(__name__)

    try:
        logger.info(
            "FINALIZE_SESSION_WORKFLOW_STARTED",
            session_id=session_id,
            sources_count=len(request.transcription_sources.webspeech_final),
        )

        # Call internal finalize function DIRECTLY (no HTTP call - avoids middleware)
        result = await internal_finalize(session_id, request)

        logger.info(
            "FINALIZE_SESSION_WORKFLOW_SUCCESS",
            session_id=session_id,
        )

        # Convert Pydantic model to dict if needed
        if isinstance(result, dict):
            return FinalizeSessionResponse(**result)
        else:
            # Already a FinalizeSessionResponse
            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "FINALIZE_SESSION_WORKFLOW_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize session: {e!s}",
        ) from e


# ============================================================================
# Task Monitor (Real-time progress with colors)
# ============================================================================


@router.get("/sessions/{session_id}/monitor", status_code=status.HTTP_200_OK)
async def monitor_session_progress(session_id: str, request: Request) -> dict:
    """Monitor session progress with colorized ASCII output OR JSON data.

    Content Negotiation:
    - Accept: application/json → Returns structured JSON data (for frontend polling)
    - Accept: text/plain (or default) → Returns colorized ASCII display (for curl/terminal)

    Args:
        session_id: Session UUID
        request: FastAPI Request (to check Accept header)

    Returns:
        dict with either JSON data or ASCII display based on Accept header
    """
    from backend.models.task_type import TaskType
    from backend.storage.task_repository import get_task_metadata

    # Check Accept header for content negotiation
    accept_header = request.headers.get("accept", "")
    wants_json = "application/json" in accept_header

    try:
        from datetime import datetime

        from backend.storage.task_repository import count_task_chunks

        # Collect structured data (used for both JSON and ASCII)
        transcription_data = {
            "status": "not_started",
            "progress": 0,
            "chunks_processed": 0,
            "chunks_total": 0,
        }
        diarization_data = {
            "status": "not_started",
            "progress": 0,
            "segment_count": 0,
            "provider": "unknown",
        }
        soap_data = {"status": "not_started"}

        # === TRANSCRIPTION ===
        try:
            transcription_meta = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}
            total, processed = count_task_chunks(session_id, TaskType.TRANSCRIPTION)
            progress = int((processed / total) * 100) if total > 0 else 0
            status_val = transcription_meta.get(
                "status", "in_progress" if processed > 0 else "pending"
            )
            if processed == total and total > 0:
                status_val = "completed"

            transcription_data = {
                "status": status_val,
                "progress": progress,
                "chunks_processed": processed,
                "chunks_total": total,
                "estimated_seconds_remaining": transcription_meta.get(
                    "estimated_seconds_remaining", 0
                ),
                "provider": transcription_meta.get("provider", "unknown"),
            }
        except ValueError:
            pass  # Keep default not_started

        # === DIARIZATION ===
        try:
            diarization_meta = get_task_metadata(session_id, TaskType.DIARIZATION) or {}
            status_val = diarization_meta.get("status", "pending")
            segment_count = diarization_meta.get("segment_count", 0)
            provider = diarization_meta.get("provider", "unknown")
            progress_percent = diarization_meta.get("progress_percent", 0)
            created_at = diarization_meta.get("created_at", "")
            updated_at = diarization_meta.get("updated_at", "")

            # Calculate elapsed time
            elapsed_seconds = 0
            if created_at and updated_at:
                try:
                    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    elapsed_seconds = (updated - created).total_seconds()
                except Exception:
                    pass

            # Fix: If completed, ensure progress is 100%
            if status_val == "completed" and progress_percent == 0:
                progress_percent = 100

            diarization_data = {
                "status": status_val,
                "progress": progress_percent,
                "segment_count": segment_count,
                "provider": provider,
                "elapsed_seconds": elapsed_seconds,
                "created_at": created_at,
            }
        except ValueError:
            pass  # Keep default not_started

        # === SOAP GENERATION ===
        try:
            soap_meta = get_task_metadata(session_id, TaskType.SOAP_GENERATION) or {}
            soap_data = {"status": soap_meta.get("status", "pending")}
        except ValueError:
            pass  # Keep default not_started

        # === RETURN JSON (for frontend polling) ===
        if wants_json:
            return {
                "session_id": session_id,
                "status": diarization_data["status"],  # Overall status = diarization status
                "progress": diarization_data["progress"],
                "segment_count": diarization_data["segment_count"],
                "error": None,
                "transcription_sources": None,  # Placeholder (frontend expects this)
                "transcription": transcription_data,
                "diarization": diarization_data,
                "soap": soap_data,
            }

        # === RETURN ASCII (for terminal/curl) ===
        RESET = "\033[0m"
        BOLD = "\033[1m"
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"
        CYAN = "\033[96m"
        RED = "\033[91m"

        output_lines = []
        output_lines.append(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
        output_lines.append(f"{BOLD}{CYAN}  Session Monitor: {session_id}{RESET}")
        output_lines.append(f"{BOLD}{CYAN}{'='*60}{RESET}\n")

        # TRANSCRIPTION ASCII
        status_val = transcription_data["status"]
        progress = transcription_data["progress"]
        processed = transcription_data["chunks_processed"]
        total = transcription_data["chunks_total"]

        if status_val == "not_started":
            output_lines.append(f"{BOLD}🎙️  TRANSCRIPTION:{RESET} {RED}NOT STARTED{RESET}\n")
        else:
            status_color = (
                GREEN
                if status_val == "completed"
                else YELLOW
                if status_val == "in_progress"
                else BLUE
            )
            bar_width = 30
            filled = int((progress / 100) * bar_width)
            bar = f"[{GREEN}{'█' * filled}{RESET}{'░' * (bar_width - filled)}]"

            output_lines.append(f"{BOLD}🎙️  TRANSCRIPTION:{RESET}")
            output_lines.append(f"   Status: {status_color}{status_val.upper()}{RESET}")
            output_lines.append(f"   Progress: {bar} {BOLD}{progress}%{RESET}")
            output_lines.append(f"   Chunks: {BOLD}{processed}/{total}{RESET} completed")
            output_lines.append("")

        # DIARIZATION ASCII
        status_val = diarization_data["status"]
        segment_count = diarization_data["segment_count"]
        provider = diarization_data["provider"]
        progress_percent = diarization_data["progress"]
        elapsed_seconds = diarization_data.get("elapsed_seconds", 0)

        if status_val == "not_started":
            output_lines.append(f"{BOLD}👥 DIARIZATION:{RESET} {RED}NOT STARTED{RESET}\n")
        else:
            status_color = (
                GREEN
                if status_val == "completed"
                else YELLOW
                if status_val == "in_progress"
                else BLUE
            )
            elapsed_str = (
                f"{elapsed_seconds / 60:.1f}m"
                if elapsed_seconds >= 60
                else f"{elapsed_seconds:.0f}s"
            )

            progress_bar = ""
            if status_val == "in_progress" and progress_percent > 0:
                bar_width = 20
                filled = int((progress_percent / 100) * bar_width)
                progress_bar = (
                    f" {GREEN}{'█' * filled}{RESET}{'░' * (bar_width - filled)} {progress_percent}%"
                )

            output_lines.append(f"{BOLD}👥 DIARIZATION:{RESET}")
            output_lines.append(
                f"   Status: {status_color}{status_val.upper()}{RESET}{progress_bar}"
            )
            output_lines.append(f"   Provider: {BOLD}{provider}{RESET}")
            output_lines.append(f"   Segments: {BOLD}{segment_count}{RESET}")
            if elapsed_seconds > 0:
                output_lines.append(f"   Duration: {BOLD}{elapsed_str}{RESET}")
            output_lines.append("")

        # SOAP ASCII
        status_val = soap_data["status"]
        if status_val == "not_started":
            output_lines.append(f"{BOLD}📋 SOAP GENERATION:{RESET} {RED}NOT STARTED{RESET}\n")
        else:
            status_color = (
                GREEN
                if status_val == "completed"
                else YELLOW
                if status_val == "in_progress"
                else BLUE
            )
            output_lines.append(f"{BOLD}📋 SOAP GENERATION:{RESET}")
            output_lines.append(f"   Status: {status_color}{status_val.upper()}{RESET}")
            output_lines.append("")

        output_lines.append(f"{BOLD}{CYAN}{'='*60}{RESET}\n")
        ascii_output = "\n".join(output_lines)

        return {
            "session_id": session_id,
            "ascii_display": ascii_output,
            "plain_text": ascii_output.replace(RESET, "")
            .replace(BOLD, "")
            .replace(GREEN, "")
            .replace(YELLOW, "")
            .replace(BLUE, "")
            .replace(CYAN, "")
            .replace(RED, ""),
        }

    except Exception as e:
        logger.error("MONITOR_SESSION_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to monitor session: {e!s}",
        ) from e


# ============================================================================
# Checkpoint (Incremental Audio Concatenation on PAUSE)
# ============================================================================


class CheckpointRequest(BaseModel):
    """Request for session checkpoint."""

    last_chunk_idx: int = Field(..., description="Last chunk index to include in checkpoint")


class CheckpointResponse(BaseModel):
    """Response for session checkpoint."""

    session_id: str = Field(..., description="Session identifier")
    checkpoint_at: str = Field(..., description="ISO timestamp")
    chunks_concatenated: int = Field(..., description="Number of chunks added")
    full_audio_size: int = Field(..., description="Total size of full_audio.webm in bytes")
    message: str = Field(..., description="Human-readable message")


@router.post(
    "/sessions/{session_id}/checkpoint",
    response_model=CheckpointResponse,
    status_code=status.HTTP_200_OK,
    tags=["workflows-sessions"],
)
async def checkpoint_session_workflow(
    session_id: str, request: CheckpointRequest
) -> CheckpointResponse:
    """Create checkpoint: incrementally concatenate audio chunks (PUBLIC orchestrator).

    Called by frontend on each PAUSE. Concatenates audio chunks since last
    checkpoint and appends to full_audio.webm (append-only).

    Flow:
    1. Get last checkpoint index from task metadata
    2. Concatenate chunks from last_checkpoint+1 to request.last_chunk_idx
    3. Append to existing full_audio.webm (or create if first checkpoint)
    4. Update task metadata with new checkpoint
    5. Launch full_transcription task
    6. Return status

    Benefits:
    - Incremental concatenation (not just at end)
    - Resilient (audio saved even if session interrupted)
    - Distributed workload (small batches per pause)

    Args:
        session_id: Session UUID
        request: CheckpointRequest with last_chunk_idx

    Returns:
        CheckpointResponse with concatenation status

    Raises:
        404: Session/task not found
        400: Invalid checkpoint index
        500: Concatenation failed
    """
    from backend.api.internal.sessions.checkpoint import (
        checkpoint_session as internal_checkpoint,
    )

    try:
        logger.info(
            "CHECKPOINT_WORKFLOW_STARTED",
            session_id=session_id,
            last_chunk_idx=request.last_chunk_idx,
        )

        # Call internal checkpoint function DIRECTLY (no HTTP call - avoids middleware)
        result = await internal_checkpoint(session_id, request)

        logger.info(
            "CHECKPOINT_WORKFLOW_SUCCESS",
            session_id=session_id,
            chunks_concatenated=result.chunks_concatenated
            if hasattr(result, "chunks_concatenated")
            else result.get("chunks_concatenated"),
        )

        # Convert Pydantic model to dict if needed
        if isinstance(result, dict):
            return CheckpointResponse(**result)
        else:
            # Already a CheckpointResponse
            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "CHECKPOINT_WORKFLOW_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to checkpoint session: {e!s}",
        ) from e


# ============================================================================
# Diarization Job Status Polling
# ============================================================================


class DiarizationStatusResponse(BaseModel):
    """Diarization job status for frontend polling."""

    job_id: str = Field(..., description="Celery task ID")
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="pending, processing, completed, failed")
    progress: int = Field(default=0, description="Progress percentage (0-100)")
    segment_count: int = Field(default=0, description="Number of diarized segments")
    transcription_sources: Optional[dict[str, Any]] = Field(
        default=None, description="Triple vision transcription sources"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")


@router.get(
    "/diarization/jobs/{job_id}",
    response_model=DiarizationStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["workflows-diarization"],
)
async def get_diarization_status_workflow(job_id: str) -> DiarizationStatusResponse:
    """Poll diarization job status (PUBLIC orchestrator).

    Frontend polls this every 2 seconds to update the diarization progress modal.

    Flow:
    1. Calls INTERNAL diarization status function directly (backend-to-backend)
    2. Returns combined HDF5 + task metadata status

    Args:
        job_id: Session ID (used as job identifier since we removed Celery)

    Returns:
        DiarizationStatusResponse with current status and progress
    """
    from backend.api.internal.diarization.status import get_diarization_status

    try:
        # Call internal function directly (no HTTP overhead, no middleware bypass)
        result = await get_diarization_status(job_id)

        logger.info(
            "DIARIZATION_STATUS_POLLED",
            job_id=job_id,
            status=result.status,
            progress=result.progress,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "DIARIZATION_STATUS_WORKFLOW_FAILED",
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diarization status: {e!s}",
        ) from e


# ============================================================================
# Diarization Segments (PUBLIC - Get results)
# ============================================================================


@router.get(
    "/sessions/{session_id}/diarization/segments",
    status_code=status.HTTP_200_OK,
    tags=["workflows-diarization"],
)
async def get_diarization_segments_workflow(session_id: str) -> dict:
    """Get diarization segments (PUBLIC orchestrator).

    Returns the speaker-separated segments from completed diarization task.

    Flow:
    1. Check DIARIZATION task status (must be completed)
    2. Load segments from HDF5
    3. Return segments with speaker labels, text, timestamps

    Args:
        session_id: Session UUID

    Returns:
        dict with session_id, segments list, metadata

    Raises:
        404: Session not found or diarization not completed
        500: Failed to load segments
    """
    from backend.models.task_type import TaskType
    from backend.storage.task_repository import (
        get_diarization_segments,
        get_task_metadata,
    )

    try:
        logger.info(
            "DIARIZATION_SEGMENTS_GET_STARTED",
            session_id=session_id,
        )

        # Check diarization task status
        metadata = get_task_metadata(session_id, TaskType.DIARIZATION)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diarization task not found for session {session_id}",
            )

        task_status = metadata.get("status", "pending")
        if task_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Diarization not completed yet (status: {task_status})",
            )

        # Load segments from HDF5
        segments = get_diarization_segments(session_id)

        logger.info(
            "DIARIZATION_SEGMENTS_GET_SUCCESS",
            session_id=session_id,
            segment_count=len(segments),
        )

        return {
            "session_id": session_id,
            "segments": segments,
            "segment_count": len(segments),
            "provider": metadata.get("provider", "unknown"),
            "completed_at": metadata.get("completed_at", ""),
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(
            "DIARIZATION_SEGMENTS_NOT_FOUND",
            session_id=session_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "DIARIZATION_SEGMENTS_GET_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diarization segments: {e!s}",
        ) from e
