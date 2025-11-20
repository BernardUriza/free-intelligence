"""Session Management Workflow Endpoints - Diarization, Finalization, Checkpoint, Monitoring.

PUBLIC layer endpoints for session lifecycle:
- POST /sessions/{session_id}/diarization → Dispatch diarization worker
- POST /sessions/{session_id}/soap → Dispatch SOAP generation worker
- POST /sessions/{session_id}/finalize → Finalize and encrypt session
- POST /sessions/{session_id}/checkpoint → Incremental audio concatenation
- GET /sessions/{session_id}/monitor → Real-time progress monitor
- GET /diarization/jobs/{job_id} → Poll diarization status
- GET /sessions/{session_id}/diarization/segments → Get diarization results
- PATCH /sessions/{session_id}/diarization/segments/{idx} → Update segment text
- GET /sessions/{session_id}/audio → Serve full audio file

Architecture:
  PUBLIC (this file) → SERVICE/INTERNAL → REPOSITORY → HDF5

Author: Bernard Uriza Orozco
Created: 2025-11-15 (Refactored from monolithic router)
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from typing import Any, cast

import h5py
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
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
    """Response for session finalization (202 Accepted).

    Returns immediately with encryption queued asynchronously.
    """

    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="ACCEPTED (session finalized, encryption queued)")
    finalized_at: str = Field(..., description="ISO timestamp of finalization")
    encryption_status: str = Field(..., description="PENDING | QUEUED | ENQUEUE_FAILED")
    encryption_task_id: str | None = Field(
        None, description="ENCRYPTION task idempotency key (for tracking)"
    )
    diarization_job_id: str | None = Field(
        None, description="Deprecated - use /diarization endpoint instead"
    )
    message: str = Field(..., description="Human-readable message")


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


class DiarizationStatusResponse(BaseModel):
    """Diarization job status for frontend polling."""

    job_id: str = Field(..., description="Celery task ID")
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="pending, processing, completed, failed")
    progress: int = Field(default=0, description="Progress percentage (0-100)")
    segment_count: int = Field(default=0, description="Number of diarized segments")
    transcription_sources: dict[str, Any] | None = Field(
        default=None, description="Triple vision transcription sources"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class UpdateSegmentRequest(BaseModel):
    """Request body for updating segment text."""

    text: str = Field(..., min_length=1, description="New text content for the segment")


# ============================================================================
# Workflow Endpoints
# ============================================================================


@router.post(
    "/sessions/{session_id}/diarization",
    status_code=status.HTTP_202_ACCEPTED,
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
    from backend.models.task_type import TaskType
    from backend.storage.task_repository import ensure_task_exists
    from backend.workers.executor_pool import spawn_worker
    from backend.workers.tasks.diarization_worker import diarize_session_worker

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
    "/sessions/{session_id}/soap",
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_soap_workflow(
    session_id: str,
) -> dict:
    """Dispatch SOAP generation worker (PUBLIC orchestrator).

    Flow:
    1. Create SOAP_GENERATION task in HDF5
    2. Dispatch SOAP worker in ThreadPoolExecutor (fire-and-forget)
    3. Frontend polls /sessions/{session_id}/monitor for status

    PUBLIC layer: Pure orchestrator - dispatches background task

    Args:
        session_id: Session UUID

    Returns:
        dict with job_id and status (202 Accepted)

    Raises:
        404: Session not found or no DIARIZATION task
        400: Diarization not completed yet
        500: Worker dispatch failed
    """
    from backend.models.task_type import TaskType
    from backend.storage.task_repository import ensure_task_exists
    from backend.workers.executor_pool import spawn_worker
    from backend.workers.tasks.soap_worker import generate_soap_worker

    try:
        logger.info(
            "SOAP_WORKFLOW_STARTED",
            session_id=session_id,
        )

        # 1. Create SOAP_GENERATION task BEFORE dispatching worker
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.SOAP_GENERATION,
            allow_existing=True,
        )
        logger.info(
            "SOAP_TASK_CREATED",
            session_id=session_id,
        )

        # 2. Dispatch worker using ThreadPoolExecutor (fire-and-forget)
        spawn_worker(generate_soap_worker, session_id=session_id)
        job_id = session_id  # Use session_id as job identifier

        logger.info(
            "SOAP_DISPATCHED",
            session_id=session_id,
            job_id=job_id,
        )

        # 3. Return 202 Accepted
        return {
            "session_id": session_id,
            "job_id": job_id,
            "status": "dispatched",
            "message": f"SOAP generation running in background (job {job_id}). Poll /sessions/{session_id}/monitor for progress.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "SOAP_WORKFLOW_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch SOAP generation: {e!s}",
        ) from e


@router.post(
    "/sessions/{session_id}/emotion",
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_emotion_workflow(
    session_id: str,
) -> dict:
    """Dispatch emotion analysis worker (PUBLIC orchestrator).

    Flow:
    1. Create EMOTION_ANALYSIS task in HDF5
    2. Dispatch emotion worker in ThreadPoolExecutor (fire-and-forget)
    3. Frontend polls /sessions/{session_id}/monitor for status

    PUBLIC layer: Pure orchestrator - dispatches background task

    Args:
        session_id: Session UUID

    Returns:
        dict with job_id and status (202 Accepted)

    Raises:
        404: Session not found or no DIARIZATION task
        400: Diarization not completed yet
        500: Worker dispatch failed
    """
    from backend.models.task_type import TaskType
    from backend.storage.task_repository import ensure_task_exists
    from backend.workers.executor_pool import spawn_worker
    from backend.workers.tasks.emotion_worker import analyze_emotion_worker

    try:
        logger.info(
            "EMOTION_WORKFLOW_STARTED",
            session_id=session_id,
        )

        # 1. Create EMOTION_ANALYSIS task BEFORE dispatching worker
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.EMOTION_ANALYSIS,
            allow_existing=True,
        )
        logger.info(
            "EMOTION_TASK_CREATED",
            session_id=session_id,
        )

        # 2. Dispatch worker using ThreadPoolExecutor (fire-and-forget)
        spawn_worker(analyze_emotion_worker, session_id=session_id)
        job_id = session_id  # Use session_id as job identifier

        logger.info(
            "EMOTION_DISPATCHED",
            session_id=session_id,
            job_id=job_id,
        )

        # 3. Return 202 Accepted
        return {
            "session_id": session_id,
            "job_id": job_id,
            "status": "dispatched",
            "message": f"Emotion analysis running in background (job {job_id}). Poll /sessions/{session_id}/monitor for progress.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "EMOTION_WORKFLOW_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch emotion analysis: {e!s}",
        ) from e


@router.post(
    "/sessions/{session_id}/finalize",
    response_model=FinalizeSessionResponse,
    status_code=status.HTTP_202_ACCEPTED,
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

        # Convert internal response to public response model (clean architecture)
        if isinstance(result, dict):
            result_dict: dict[str, Any] = result
        else:
            # Convert Pydantic model to dict
            result_dict = result.model_dump()

        return FinalizeSessionResponse(**result_dict)

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


@router.post(
    "/sessions/{session_id}/checkpoint",
    response_model=CheckpointResponse,
    status_code=status.HTTP_200_OK,
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

        # Convert internal response to public response model (clean architecture)
        if isinstance(result, dict):
            result_dict: dict[str, Any] = result
        else:
            # Convert Pydantic model to dict
            result_dict = result.model_dump()

        return CheckpointResponse(**result_dict)

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
    from backend.storage.task_repository import count_task_chunks, get_task_metadata

    # Check Accept header for content negotiation
    accept_header = request.headers.get("accept", "")
    wants_json = "application/json" in accept_header

    try:
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

        # === ENCRYPTION ===
        encryption_data = {"status": "not_started", "progress": 0}
        try:
            encryption_meta = get_task_metadata(session_id, TaskType.ENCRYPTION) or {}
            encryption_status = encryption_meta.get("status", "pending")
            encryption_progress = encryption_meta.get("progress_percent", 0)
            encryption_data = {
                "status": encryption_status,
                "progress": encryption_progress,
                "queued_at": encryption_meta.get("queued_at", ""),
            }
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
                "encryption": encryption_data,
            }

        # === RETURN ASCII (for terminal/curl) ===
        reset = "\033[0m"
        bold = "\033[1m"
        green = "\033[92m"
        yellow = "\033[93m"
        blue = "\033[94m"
        cyan = "\033[96m"
        red = "\033[91m"

        output_lines = []
        output_lines.append(f"\n{bold}{cyan}{'=' * 60}{reset}")
        output_lines.append(f"{bold}{cyan}  Session Monitor: {session_id}{reset}")
        output_lines.append(f"{bold}{cyan}{'=' * 60}{reset}\n")

        # TRANSCRIPTION ASCII
        status_val = transcription_data["status"]
        progress = cast(int, transcription_data["progress"])
        processed = cast(int, transcription_data["chunks_processed"])
        total = cast(int, transcription_data["chunks_total"])

        if status_val == "not_started":
            output_lines.append(f"{bold}🎙️  TRANSCRIPTION:{reset} {red}NOT STARTED{reset}\n")
        else:
            status_color = (
                green
                if status_val == "completed"
                else yellow
                if status_val == "in_progress"
                else blue
            )
            bar_width = 30
            filled = int((progress / 100) * bar_width)
            bar = f"[{green}{'█' * filled}{reset}{'░' * (bar_width - filled)}]"

            output_lines.append(f"{bold}🎙️  TRANSCRIPTION:{reset}")
            output_lines.append(f"   Status: {status_color}{status_val.upper()}{reset}")
            output_lines.append(f"   Progress: {bar} {bold}{progress}%{reset}")
            output_lines.append(f"   Chunks: {bold}{processed}/{total}{reset} completed")
            output_lines.append("")

        # DIARIZATION ASCII
        status_val = diarization_data["status"]
        segment_count = cast(int, diarization_data["segment_count"])
        provider = diarization_data["provider"]
        progress_percent = cast(int, diarization_data["progress"])
        elapsed_seconds = cast(int, diarization_data.get("elapsed_seconds", 0))

        if status_val == "not_started":
            output_lines.append(f"{bold}👥 DIARIZATION:{reset} {red}NOT STARTED{reset}\n")
        else:
            status_color = (
                green
                if status_val == "completed"
                else yellow
                if status_val == "in_progress"
                else blue
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
                    f" {green}{'█' * filled}{reset}{'░' * (bar_width - filled)} {progress_percent}%"
                )

            output_lines.append(f"{bold}👥 DIARIZATION:{reset}")
            output_lines.append(
                f"   Status: {status_color}{status_val.upper()}{reset}{progress_bar}"
            )
            output_lines.append(f"   Provider: {bold}{provider}{reset}")
            output_lines.append(f"   Segments: {bold}{segment_count}{reset}")
            if elapsed_seconds > 0:
                output_lines.append(f"   Duration: {bold}{elapsed_str}{reset}")
            output_lines.append("")

        # SOAP ASCII
        status_val = soap_data["status"]
        if status_val == "not_started":
            output_lines.append(f"{bold}📋 SOAP GENERATION:{reset} {red}NOT STARTED{reset}\n")
        else:
            status_color = (
                green
                if status_val == "completed"
                else yellow
                if status_val == "in_progress"
                else blue
            )
            output_lines.append(f"{bold}📋 SOAP GENERATION:{reset}")
            output_lines.append(f"   Status: {status_color}{status_val.upper()}{reset}")
            output_lines.append("")

        # ENCRYPTION ASCII
        status_val = encryption_data["status"]
        if status_val == "not_started":
            output_lines.append(f"{bold}🔐 ENCRYPTION:{reset} {red}NOT STARTED{reset}\n")
        else:
            status_color = (
                green
                if status_val == "completed"
                else yellow
                if status_val == "in_progress"
                else blue
            )
            progress_val = cast(int, encryption_data["progress"])
            output_lines.append(f"{bold}🔐 ENCRYPTION:{reset}")
            output_lines.append(f"   Status: {status_color}{status_val.upper()}{reset}")
            if progress_val > 0:
                output_lines.append(f"   Progress: {bold}{progress_val}%{reset}")
            output_lines.append("")

        output_lines.append(f"{bold}{cyan}{'=' * 60}{reset}\n")
        ascii_output = "\n".join(output_lines)

        return {
            "session_id": session_id,
            "ascii_display": ascii_output,
            "plain_text": ascii_output.replace(reset, "")
            .replace(bold, "")
            .replace(green, "")
            .replace(yellow, "")
            .replace(blue, "")
            .replace(cyan, "")
            .replace(red, ""),
        }

    except Exception as e:
        logger.error("MONITOR_SESSION_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to monitor session: {e!s}",
        ) from e


@router.get(
    "/diarization/jobs/{job_id}",
    response_model=DiarizationStatusResponse,
    status_code=status.HTTP_200_OK,
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

        # Convert internal response to public response model (clean architecture)
        if isinstance(result, dict):
            result_dict: dict[str, Any] = result
        else:
            # Convert Pydantic model to dict
            result_dict = result.model_dump()

        return DiarizationStatusResponse(**result_dict)

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


@router.get(
    "/sessions/{session_id}/diarization/segments",
    status_code=status.HTTP_200_OK,
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

        # Include transcription sources (Triple Vision)
        transcription_sources = metadata.get("transcription_sources", {})

        return {
            "session_id": session_id,
            "segments": segments,
            "segment_count": len(segments),
            "provider": metadata.get("provider", "unknown"),
            "completed_at": metadata.get("completed_at", ""),
            "transcription_sources": transcription_sources,  # NEW: Include Triple Vision sources
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


@router.patch(
    "/sessions/{session_id}/diarization/segments/{segment_index}",
    status_code=status.HTTP_200_OK,
)
async def update_diarization_segment_workflow(
    session_id: str,
    segment_index: int,
    request: UpdateSegmentRequest,
) -> dict:
    """Update text of a diarization segment (PUBLIC orchestrator).

    Allows editing of transcribed text in diarization segments.

    Args:
        session_id: Session UUID
        segment_index: Index of segment to update (0-based)
        request: Request body with new text

    Returns:
        Updated segment with new text

    Raises:
        404: Session, task, or segment not found
        400: Invalid segment index
        500: Failed to update segment
    """
    from backend.storage.task_repository import update_diarization_segment_text

    try:
        logger.info(
            "DIARIZATION_SEGMENT_UPDATE_STARTED",
            session_id=session_id,
            segment_index=segment_index,
        )

        # Validate segment_index
        if segment_index < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="segment_index must be >= 0",
            )

        # Update segment in HDF5
        updated_segment = update_diarization_segment_text(
            session_id=session_id,
            segment_index=segment_index,
            new_text=request.text,
        )

        logger.info(
            "DIARIZATION_SEGMENT_UPDATE_SUCCESS",
            session_id=session_id,
            segment_index=segment_index,
        )

        return {
            "session_id": session_id,
            "segment_index": segment_index,
            "segment": updated_segment,
            "updated_at": str(datetime.now(UTC).isoformat()),
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(
            "DIARIZATION_SEGMENT_UPDATE_NOT_FOUND",
            session_id=session_id,
            segment_index=segment_index,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "DIARIZATION_SEGMENT_UPDATE_FAILED",
            session_id=session_id,
            segment_index=segment_index,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update segment: {e!s}",
        ) from e


@router.get(
    "/sessions/{session_id}/transcription-sources",
    response_model=TranscriptionSourcesModel,
    status_code=status.HTTP_200_OK,
)
async def get_transcription_sources_workflow(session_id: str) -> TranscriptionSourcesModel:
    """Get all 3 transcription sources for a saved session (PUBLIC endpoint).

    Reconstructs Triple Vision transcription sources from HDF5:
    1. webspeech_final: Browser WebSpeech API instant previews
    2. transcription_per_chunks: Per-chunk transcripts (Deepgram/Azure Whisper)
    3. full_transcription: Concatenated full text

    Used when opening a saved session to populate "Fuentes de Transcripción" UI.

    Args:
        session_id: Session UUID

    Returns:
        TranscriptionSourcesModel with all 3 sources

    Raises:
        404: Session not found or no transcription data
        500: Failed to load transcription sources
    """
    import json

    from backend.models.task_type import TaskType
    from backend.storage.task_repository import CORPUS_PATH, get_task_chunks

    try:
        logger.info(
            "TRANSCRIPTION_SOURCES_GET_STARTED",
            session_id=session_id,
        )

        webspeech_final: list[str] = []
        transcription_per_chunks: list[dict] = []
        full_transcription: str = ""

        # 1. Load webspeech_final from HDF5 (if exists)
        with h5py.File(CORPUS_PATH, "r") as f:
            webspeech_path = (
                f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}/webspeech_final"
            )
            if webspeech_path in f:
                webspeech_data = f[webspeech_path][()]
                webspeech_json = bytes(webspeech_data).decode("utf-8")
                webspeech_final = json.loads(webspeech_json)
                logger.info(
                    "WEBSPEECH_LOADED",
                    session_id=session_id,
                    count=len(webspeech_final),
                )
            else:
                logger.warning(
                    "WEBSPEECH_NOT_FOUND",
                    session_id=session_id,
                    hint="Session may not have webspeech data (normal for old sessions)",
                )

        # 2. Load chunks and build transcription_per_chunks + full_transcription
        try:
            chunks = get_task_chunks(session_id=session_id, task_type=TaskType.TRANSCRIPTION)

            transcripts_list = []
            for chunk in chunks:
                chunk_dict = {
                    "chunk_number": chunk.get("chunk_number", 0),
                    "transcript": chunk.get("transcript", ""),
                    "timestamp_start": chunk.get("timestamp_start", 0.0),
                    "timestamp_end": chunk.get("timestamp_end", 0.0),
                    "duration": chunk.get("duration", 0.0),
                    "provider": chunk.get("provider", "unknown"),
                    "confidence": chunk.get("confidence", 0.0),
                    # Metrics (available in new sessions)
                    "resolution_time_seconds": chunk.get("resolution_time_seconds", 0.0),
                    "retry_attempts": chunk.get("retry_attempts", 0),
                    "polling_attempts": chunk.get("polling_attempts", 0),
                }
                transcription_per_chunks.append(chunk_dict)

                # Build full_transcription (concatenate all transcripts)
                transcript = chunk.get("transcript", "")
                if transcript:
                    transcripts_list.append(transcript)

            full_transcription = " ".join(transcripts_list)

            logger.info(
                "CHUNKS_LOADED",
                session_id=session_id,
                chunk_count=len(chunks),
                full_text_length=len(full_transcription),
            )

        except ValueError as e:
            logger.warning(
                "NO_TRANSCRIPTION_CHUNKS",
                session_id=session_id,
                error=str(e),
            )
            # Empty chunks is OK (session may be in progress)

        logger.info(
            "TRANSCRIPTION_SOURCES_GET_SUCCESS",
            session_id=session_id,
            webspeech_count=len(webspeech_final),
            chunks_count=len(transcription_per_chunks),
            full_length=len(full_transcription),
        )

        return TranscriptionSourcesModel(
            webspeech_final=webspeech_final,
            transcription_per_chunks=transcription_per_chunks,
            full_transcription=full_transcription,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "TRANSCRIPTION_SOURCES_GET_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transcription sources: {e!s}",
        ) from e


@router.get(
    "/sessions/{session_id}/audio",
    status_code=status.HTTP_200_OK,
)
async def get_session_audio_workflow(session_id: str) -> FileResponse:
    """Serve full audio file from completed session (PUBLIC endpoint).

    Returns the concatenated full_audio.webm file stored in HDF5.
    Allows doctors to re-listen to the consultation after completion.

    Flow:
    1. Load full_audio.webm from HDF5 TRANSCRIPTION task
    2. Write to temporary file
    3. Return as FileResponse with proper Content-Type

    Args:
        session_id: Session UUID

    Returns:
        FileResponse with audio/webm content

    Raises:
        404: Session not found or audio not available
        500: Failed to load audio
    """

    from backend.storage.task_repository import CORPUS_PATH

    try:
        logger.info(
            "SESSION_AUDIO_GET_STARTED",
            session_id=session_id,
        )

        # Load audio from HDF5
        with h5py.File(CORPUS_PATH, "r") as f:
            full_audio_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm"

            if full_audio_path not in f:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Audio not found for session {session_id}. Session may not have been checkpointed yet.",
                )

            audio_data = f[full_audio_path][()]

            # Convert numpy array to bytes properly
            if hasattr(audio_data, "tobytes"):
                audio_bytes = audio_data.tobytes()
            elif isinstance(audio_data, bytes):
                audio_bytes = audio_data
            else:
                audio_bytes = bytes(audio_data)

            if len(audio_bytes) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Audio file is empty for session {session_id}",
                )

        # Write to temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=".webm", prefix=f"session_{session_id}_"
        )
        temp_file.write(audio_bytes)
        temp_file.close()

        logger.info(
            "SESSION_AUDIO_GET_SUCCESS",
            session_id=session_id,
            audio_size_bytes=len(audio_bytes),
            temp_file_path=temp_file.name,
        )

        # Return as FileResponse with CORS headers
        return FileResponse(
            path=temp_file.name,
            media_type="audio/webm",
            filename=f"session_{session_id}.webm",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
            # Note: Temporary file will be cleaned up by OS after response is sent
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "SESSION_AUDIO_GET_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session audio: {e!s}",
        ) from e
