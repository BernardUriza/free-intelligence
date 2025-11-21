"""Session Management Workflow Endpoints - SOLID Refactored.

PUBLIC layer endpoints for session lifecycle (REFACTORED):
- Uses WorkflowOrchestrator service for workflow dispatch
- Models extracted to models/session_models.py
- Business logic in services/ layer

SOLID Principles Applied:
- Single Responsibility: Each service has one job
- Dependency Inversion: Endpoints depend on abstractions (services), not implementations
- Open/Closed: Adding workflows doesn't require changing endpoint code

Architecture:
  PUBLIC (this file) → SERVICES → REPOSITORY → HDF5

Author: Bernard Uriza Orozco
Created: 2025-11-15 (Refactored from monolithic router)
SOLID Refactor: 2025-11-20
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from typing import Any, cast

import h5py
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from backend.api.public.workflows.models import (
    CheckpointRequest,
    CheckpointResponse,
    DiarizationStatusResponse,
    DoctorFeedbackRequest,
    DoctorFeedbackResponse,
    FinalizeSessionRequest,
    FinalizeSessionResponse,
    TranscriptionSourcesModel,
    UpdateSegmentRequest,
)
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


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

    SOLID Refactored: Uses WorkflowOrchestrator service (Single Responsibility).

    Flow:
    1. Delegate to WorkflowOrchestrator
    2. Return standardized response

    Args:
        session_id: Session UUID

    Returns:
        dict with job_id and status (202 Accepted)

    Raises:
        500: Worker dispatch failed
    """
    from backend.api.public.workflows.services import get_workflow_orchestrator

    try:
        orchestrator = get_workflow_orchestrator()
        return orchestrator.dispatch_diarization(session_id)

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

    SOLID Refactored: Uses WorkflowOrchestrator service (Single Responsibility).

    Args:
        session_id: Session UUID

    Returns:
        dict with job_id and status (202 Accepted)

    Raises:
        500: Worker dispatch failed
    """
    from backend.api.public.workflows.services import get_workflow_orchestrator

    try:
        orchestrator = get_workflow_orchestrator()
        return orchestrator.dispatch_soap_generation(session_id)

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

    SOLID Refactored: Uses WorkflowOrchestrator service (Single Responsibility).

    Args:
        session_id: Session UUID

    Returns:
        dict with job_id and status (202 Accepted)

    Raises:
        500: Worker dispatch failed
    """
    from backend.api.public.workflows.services import get_workflow_orchestrator

    try:
        orchestrator = get_workflow_orchestrator()
        return orchestrator.dispatch_emotion_analysis(session_id)

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
    "/sessions/{session_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_session_intelligent_workflow(
    session_id: str,
    audio_duration_seconds: float | None = None,
    language: str | None = None,
) -> dict:
    """Intelligent workflow orchestration using Two-Model Strategy (PUBLIC orchestrator).

    Uses cheap Haiku ($0.25/1M tokens) for routing decisions,
    expensive models (Sonnet/GPT-4) only for selected workflows.

    Cost savings: ~16% per query by skipping unnecessary tasks.

    Flow:
    1. Use WorkflowRouter to decide which tasks to execute
    2. Dispatch selected workflows in parallel (if independent)
    3. Frontend polls /sessions/{session_id}/monitor for progress

    Quick Win Benefits:
    - Single API call instead of 3+ separate calls
    - Automatic task dependency resolution
    - Skip redundant tasks (already completed)
    - Skip unnecessary tasks (audio too short for diarization)
    - Cost tracking (routing cost + savings from skipped tasks)

    PUBLIC layer: Intelligent orchestrator with cost optimization

    Args:
        session_id: Session UUID
        audio_duration_seconds: Optional audio duration (will detect if not provided)
        language: Optional language code (es, en, etc.)

    Returns:
        dict with:
            - workflows: List of workflows being executed
            - reasoning: Explanation of routing decision
            - job_ids: Dict of task -> job_id mappings
            - cost: Cost metrics (routing + savings)
            - status: "dispatched"

    Raises:
        404: Session not found
        500: Worker dispatch failed
    """
    from backend.models.task_type import TaskStatus, TaskType
    from backend.services.workflow_router import get_workflow_router
    from backend.storage.task_repository import (
        CORPUS_PATH,
        ensure_task_exists,
        get_task_metadata,
    )
    from backend.workers.executor_pool import spawn_worker

    try:
        logger.info(
            "INTELLIGENT_WORKFLOW_STARTED",
            session_id=session_id,
            audio_duration=audio_duration_seconds,
            language=language,
        )

        # Auto-detect audio duration if not provided
        if audio_duration_seconds is None:
            try:
                import h5py

                with h5py.File(CORPUS_PATH, "r") as f:
                    audio_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm"
                    if audio_path in f:
                        audio_bytes = len(f[audio_path][()])
                        # Rough estimate: WebM is ~12KB/s at 48kHz
                        audio_duration_seconds = audio_bytes / (12 * 1024)
                        logger.info(
                            "AUDIO_DURATION_DETECTED",
                            session_id=session_id,
                            duration_seconds=audio_duration_seconds,
                        )
            except Exception as e:
                logger.warning(
                    "AUDIO_DURATION_DETECTION_FAILED",
                    session_id=session_id,
                    error=str(e),
                    hint="Using default duration of 60s",
                )
                audio_duration_seconds = 60.0  # Default assumption

        # Get existing tasks
        existing_tasks = []
        try:
            import h5py

            with h5py.File(CORPUS_PATH, "r") as f:
                tasks_path = f"/sessions/{session_id}/tasks"
                if tasks_path in f:
                    for task_type in f[tasks_path]:
                        metadata = get_task_metadata(session_id, TaskType[task_type])
                        if metadata and metadata.get("status") == TaskStatus.COMPLETED.value:
                            existing_tasks.append(task_type)
        except Exception as e:
            logger.warning(
                "EXISTING_TASKS_DETECTION_FAILED",
                session_id=session_id,
                error=str(e),
            )

        # Use WorkflowRouter to decide which workflows to execute
        router = get_workflow_router()
        decision = router.route_workflows(
            session_id=session_id,
            audio_duration_seconds=audio_duration_seconds,
            language=language,
            existing_tasks=existing_tasks,
        )

        logger.info(
            "WORKFLOW_ROUTING_DECISION",
            session_id=session_id,
            workflows=decision["workflows"],
            reasoning=decision["reasoning"],
            cost_usd=decision["cost"].routing_cost_usd,
            savings_usd=decision["cost"].execution_cost_saved_usd,
        )

        # Dispatch selected workflows
        job_ids = {}
        for workflow in decision["workflows"]:
            task_type = TaskType[workflow]

            # Create task
            ensure_task_exists(
                session_id=session_id,
                task_type=task_type,
                allow_existing=True,
            )

            # Dispatch appropriate worker
            if task_type == TaskType.TRANSCRIPTION:
                # Transcription happens during streaming upload - skip here
                logger.info(
                    "TRANSCRIPTION_SKIPPED",
                    session_id=session_id,
                    hint="Transcription handled during upload",
                )
                continue

            elif task_type == TaskType.DIARIZATION:
                from backend.workers.tasks.diarization_worker import diarization_worker

                spawn_worker(diarization_worker, session_id=session_id)
                job_ids["DIARIZATION"] = session_id

            elif task_type == TaskType.SOAP_GENERATION:
                from backend.workers.tasks.soap_worker import generate_soap_worker

                spawn_worker(generate_soap_worker, session_id=session_id)
                job_ids["SOAP_GENERATION"] = session_id

            elif task_type == TaskType.EMOTION_ANALYSIS:
                from backend.workers.tasks.emotion_worker import analyze_emotion_worker

                spawn_worker(analyze_emotion_worker, session_id=session_id)
                job_ids["EMOTION_ANALYSIS"] = session_id

            logger.info(
                "WORKFLOW_DISPATCHED",
                session_id=session_id,
                task_type=workflow,
            )

        # Return 202 Accepted with routing decision
        return {
            "session_id": session_id,
            "status": "dispatched",
            "workflows": decision["workflows"],
            "reasoning": decision["reasoning"],
            "parallel": decision["parallel"],
            "job_ids": job_ids,
            "cost": {
                "routing_usd": decision["cost"].routing_cost_usd,
                "tokens_saved": decision["cost"].execution_tokens_saved,
                "savings_usd": decision["cost"].execution_cost_saved_usd,
                "net_savings_usd": (
                    decision["cost"].execution_cost_saved_usd - decision["cost"].routing_cost_usd
                ),
            },
            "message": f"Intelligent orchestration complete: {len(decision['workflows'])} workflows dispatched. Poll /sessions/{session_id}/monitor for progress.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "INTELLIGENT_WORKFLOW_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to orchestrate workflows: {e!s}",
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


# ============================================================================
# Medical Audit & Feedback Endpoints
# ============================================================================


@router.get("/sessions/{session_id}/audit")
async def get_session_audit(session_id: str) -> dict[str, Any]:
    """Get complete audit data for doctor review.

    Returns session metadata, SOAP notes, orchestration steps, diarization,
    and automatically detected flags for doctor attention.

    Args:
        session_id: Session identifier

    Returns:
        {
            "session_id": str,
            "patient": {...},
            "session_metadata": {...},
            "orchestration": {...},
            "soap_note": {...},
            "diarization": {...},
            "flags": [...],
            "doctor_feedback": {...} | null
        }
    """
    from backend.models.task_type import TaskType
    from backend.storage.task_repository import (
        get_diarization_segments,
        get_session_metadata,
        get_soap_data,
        get_task_metadata,
    )

    try:
        logger.info("SESSION_AUDIT_GET_START", session_id=session_id)

        # Get session metadata
        session_meta = get_session_metadata(session_id)
        if not session_meta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        # Get SOAP note
        soap_data = get_soap_data(session_id)

        # Get orchestration steps
        soap_task_meta = get_task_metadata(session_id, TaskType.SOAP_GENERATION)

        # Get diarization segments
        diarization_segments = get_diarization_segments(session_id)

        # Analyze for flags (low confidence, medication interactions, etc.)
        flags = _analyze_session_flags(soap_data, soap_task_meta)

        # Get existing doctor feedback (if any)
        doctor_feedback = session_meta.get("doctor_feedback")

        response = {
            "session_id": session_id,
            "patient": session_meta.get("patient", {}),
            "session_metadata": {
                "date": session_meta.get("created_at"),
                "duration_seconds": session_meta.get("duration_seconds"),
                "doctor": session_meta.get("doctor_name", "Unknown"),
                "status": session_meta.get("audit_status", "pending_review"),
            },
            "orchestration": {
                "strategy": soap_task_meta.get("orchestration_strategy", "UNKNOWN"),
                "personas_invoked": soap_task_meta.get("personas_invoked", []),
                "confidence_score": soap_task_meta.get("confidence_score", 0.0),
                "complexity_score": soap_task_meta.get("complexity_score", 0.0),
                "steps": soap_task_meta.get("intermediate_outputs", []),
            },
            "soap_note": soap_data or {},
            "diarization": {
                "segments": diarization_segments or [],
            },
            "flags": flags,
            "doctor_feedback": doctor_feedback,
        }

        logger.info(
            "SESSION_AUDIT_GET_SUCCESS",
            session_id=session_id,
            flags_count=len(flags),
            has_feedback=doctor_feedback is not None,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "SESSION_AUDIT_GET_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session audit: {e!s}",
        ) from e


def _analyze_session_flags(
    soap_data: dict[str, Any] | None,
    orchestration: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Analyze session for potential issues requiring doctor attention.

    Args:
        soap_data: SOAP note data
        orchestration: Orchestration metadata

    Returns:
        List of flags with type, severity, message, location
    """
    flags = []

    if not soap_data or not orchestration:
        return flags

    # Low confidence flag
    confidence = orchestration.get("confidence_score", 1.0)
    if confidence < 0.95:
        flags.append(
            {
                "type": "low_confidence",
                "severity": "warning",
                "message": f"Confidence score below 95% ({confidence:.0%})",
                "location": "overall",
            }
        )

    # Medication interaction detection (example heuristic)
    plan = soap_data.get("plan", {})
    medications = plan.get("medications", [])

    # Check for IECA combinations (enalapril + losartán)
    has_enalapril = any(
        "enalapril" in med.get("name", "").lower() for med in medications if isinstance(med, dict)
    )
    has_losartan = any(
        "losartán" in med.get("name", "").lower() or "losartan" in med.get("name", "").lower()
        for med in medications
        if isinstance(med, dict)
    )

    if has_enalapril and has_losartan:
        flags.append(
            {
                "type": "medication_interaction",
                "severity": "critical",
                "message": "Posible interacción: Enalapril + Losartán (ambos IECA)",
                "location": "plan.medications",
            }
        )

    # Missing objective data flag
    objective = soap_data.get("objective")
    if not objective or (isinstance(objective, str) and len(objective.strip()) < 10):
        flags.append(
            {
                "type": "missing_objective_data",
                "severity": "warning",
                "message": "No se registraron signos vitales ni exploración física",
                "location": "objective",
            }
        )

    # High complexity with low confidence
    complexity = orchestration.get("complexity_score", 0.0)
    if complexity >= 60 and confidence < 0.90:
        flags.append(
            {
                "type": "complex_low_confidence",
                "severity": "warning",
                "message": f"Caso complejo (score {complexity:.1f}) con confianza baja ({confidence:.0%})",
                "location": "overall",
            }
        )

    return flags


@router.post("/sessions/{session_id}/feedback")
async def submit_doctor_feedback(
    session_id: str,
    feedback: DoctorFeedbackRequest,
) -> DoctorFeedbackResponse:
    """Submit doctor's audit feedback for a session.

    Args:
        session_id: Session identifier
        feedback: Doctor's rating, comments, corrections, and decision

    Returns:
        DoctorFeedbackResponse with status and corrections count
    """
    from backend.models.task_type import TaskType
    from backend.storage.task_repository import (
        get_soap_data,
        save_soap_data,
        update_session_metadata,
    )

    try:
        logger.info(
            "DOCTOR_FEEDBACK_SUBMIT_START",
            session_id=session_id,
            decision=feedback.decision,
            rating=feedback.rating,
            corrections_count=len(feedback.corrections),
        )

        # Save feedback to session metadata
        feedback_data = {
            "rating": feedback.rating,
            "comments": feedback.comments,
            "corrections": [corr.dict() for corr in feedback.corrections],
            "decision": feedback.decision,
            "submitted_at": datetime.now(UTC).isoformat(),
            "submitted_by": "Dr. Uriza",  # TODO: Get from auth context
        }

        update_session_metadata(
            session_id,
            {
                "doctor_feedback": feedback_data,
                "audit_status": feedback.decision,
                "audit_rating": feedback.rating,
                "audited_at": datetime.now(UTC).isoformat(),
                "audited_by": "Dr. Uriza",  # TODO: Get from auth context
            },
        )

        # Apply corrections to SOAP note
        corrections_applied = 0
        if feedback.corrections:
            soap_data = get_soap_data(session_id)
            if soap_data:
                for correction in feedback.corrections:
                    section = correction.section
                    if section in soap_data:
                        # Replace original text with corrected text
                        if isinstance(soap_data[section], str):
                            soap_data[section] = soap_data[section].replace(
                                correction.original,
                                correction.corrected,
                            )
                            corrections_applied += 1
                        elif isinstance(soap_data[section], dict):
                            # For complex sections (like assessment, plan)
                            # Store correction metadata
                            if "corrections" not in soap_data[section]:
                                soap_data[section]["corrections"] = []
                            soap_data[section]["corrections"].append(correction.dict())
                            corrections_applied += 1

                # Save updated SOAP data
                save_soap_data(session_id, soap_data, TaskType.SOAP_GENERATION)

        logger.info(
            "DOCTOR_FEEDBACK_SUBMITTED",
            session_id=session_id,
            decision=feedback.decision,
            rating=feedback.rating,
            corrections_applied=corrections_applied,
        )

        return DoctorFeedbackResponse(
            status="feedback_saved",
            session_id=session_id,
            audit_status=feedback.decision,
            corrections_applied=corrections_applied,
        )

    except Exception as e:
        logger.error(
            "DOCTOR_FEEDBACK_SUBMIT_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit doctor feedback: {e!s}",
        ) from e
