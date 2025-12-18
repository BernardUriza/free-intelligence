from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, status

from backend.logger import get_logger
from backend.validators import validate_session_id

if TYPE_CHECKING:
    from backend.api.public.workflows.models import (
        CheckpointRequest,
        CheckpointResponse,
        FinalizeSessionRequest,
        FinalizeSessionResponse,
    )

logger = get_logger(__name__)
router = APIRouter()


@router.post("/sessions/{session_id}/diarization", status_code=status.HTTP_202_ACCEPTED)
async def diarize_session_workflow(session_id: str) -> dict:
    validate_session_id(session_id)
    from backend.api.public.workflows.services import get_workflow_orchestrator

    try:
        orchestrator = get_workflow_orchestrator()
        return orchestrator.dispatch_diarization(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "DIARIZATION_WORKFLOW_FAILED", session_id=session_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch diarization: {e!s}",
        ) from e


@router.post("/sessions/{session_id}/soap", status_code=status.HTTP_202_ACCEPTED)
async def generate_soap_workflow(session_id: str) -> dict:
    validate_session_id(session_id)
    from backend.api.public.workflows.services import get_workflow_orchestrator

    try:
        orchestrator = get_workflow_orchestrator()
        return orchestrator.dispatch_soap_generation(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("SOAP_WORKFLOW_FAILED", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch SOAP generation: {e!s}",
        ) from e


@router.post("/sessions/{session_id}/emotion", status_code=status.HTTP_202_ACCEPTED)
async def analyze_emotion_workflow(session_id: str) -> dict:
    from backend.api.public.workflows.services import get_workflow_orchestrator

    try:
        orchestrator = get_workflow_orchestrator()
        return orchestrator.dispatch_emotion_analysis(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("EMOTION_WORKFLOW_FAILED", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch emotion analysis: {e!s}",
        ) from e


@router.post("/sessions/{session_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_session_intelligent_workflow(
    session_id: str,
    audio_duration_seconds: float | None = None,
    language: str | None = None,
) -> dict:
    import h5py

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

        if audio_duration_seconds is None:
            try:
                with h5py.File(CORPUS_PATH, "r") as f:
                    audio_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm"
                    if audio_path in f:
                        audio_bytes = len(f[audio_path][()])
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
                audio_duration_seconds = 60.0

        existing_tasks: list[str] = []
        try:
            with h5py.File(CORPUS_PATH, "r") as f:
                tasks_path = f"/sessions/{session_id}/tasks"
                if tasks_path in f:
                    for task_type in f[tasks_path]:
                        constructed_task = TaskType(task_type)
                        metadata = get_task_metadata(session_id, constructed_task)
                        status_val = metadata.get("status") if metadata else None
                        is_completed = (
                            status_val == "completed"
                            or status_val == TaskStatus.COMPLETED.name.lower()
                            or status_val == TaskStatus.COMPLETED
                        )
                        if metadata and is_completed:
                            existing_tasks.append(task_type)
        except Exception as e:
            logger.warning("EXISTING_TASKS_DETECTION_FAILED", session_id=session_id, error=str(e))

        router_svc = get_workflow_router()
        decision = router_svc.route_workflows(
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

        job_ids: dict[str, str] = {}
        for workflow in decision["workflows"]:
            task_type = TaskType(workflow)

            ensure_task_exists(session_id=session_id, task_type=task_type, allow_existing=True)

            if task_type == TaskType.TRANSCRIPTION:
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

            logger.info("WORKFLOW_DISPATCHED", session_id=session_id, task_type=workflow)

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
            "INTELLIGENT_WORKFLOW_FAILED", session_id=session_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to orchestrate workflows: {e!s}",
        ) from e


@router.post("/sessions/{session_id}/finalize", status_code=status.HTTP_202_ACCEPTED)
async def finalize_session_workflow(
    session_id: str, request: FinalizeSessionRequest
) -> FinalizeSessionResponse:
    from backend.api.internal.sessions.finalize import (
        finalize_session as internal_finalize,
    )

    try:
        logger.info(
            "FINALIZE_SESSION_WORKFLOW_STARTED",
            session_id=session_id,
            sources_count=len(request.transcription_sources.webspeech_final),
        )
        result = await internal_finalize(session_id, request)
        logger.info("FINALIZE_SESSION_WORKFLOW_SUCCESS", session_id=session_id)
        if isinstance(result, dict):
            result_dict: dict[str, Any] = result  # type: ignore[name-defined]
        else:
            result_dict = result.model_dump()
        from backend.api.public.workflows.models import FinalizeSessionResponse

        return FinalizeSessionResponse(**result_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "FINALIZE_SESSION_WORKFLOW_FAILED", session_id=session_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize session: {e!s}",
        ) from e


@router.post("/sessions/{session_id}/checkpoint", status_code=status.HTTP_200_OK)
async def checkpoint_session_workflow(
    session_id: str, request: CheckpointRequest
) -> CheckpointResponse:
    from backend.api.internal.sessions.checkpoint import (
        checkpoint_session as internal_checkpoint,
    )

    try:
        logger.info(
            "CHECKPOINT_WORKFLOW_STARTED",
            session_id=session_id,
            last_chunk_idx=request.last_chunk_idx,
        )
        result = await internal_checkpoint(session_id, request)
        logger.info(
            "CHECKPOINT_WORKFLOW_SUCCESS",
            session_id=session_id,
            chunks_concatenated=(
                result.chunks_concatenated
                if hasattr(result, "chunks_concatenated")
                else result.get("chunks_concatenated")
            ),
        )
        if isinstance(result, dict):
            result_dict: dict[str, Any] = result  # type: ignore[name-defined]
        else:
            result_dict = result.model_dump()
        from backend.api.public.workflows.models import CheckpointResponse

        return CheckpointResponse(**result_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "CHECKPOINT_WORKFLOW_FAILED", session_id=session_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to checkpoint session: {e!s}",
        ) from e
