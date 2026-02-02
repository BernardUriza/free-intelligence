"""Session workflow endpoints (thin controllers with dependency injection).

Business logic extracted to IntelligentOrchestrationService (PR #1).
Endpoints use FastAPI Depends() for service injection (PR #2).

Architecture:
- Controllers: Thin (10-20 lines), no business logic
- Services: Business logic (orchestration, routing, state tracking)
- Dependencies: FastAPI Depends() resolves services

Benefits:
- Type-safe dependency injection
- Testable via app.dependency_overrides
- Clear dependency graph
- SOLID compliance (Single Responsibility, Dependency Inversion)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.api.audit.dependencies import DIAuditService
from backend.services.workflow.dependencies import (
    IntelligentOrchestrationDep,
    WorkflowOrchestratorDep,
)
from backend.utils.common.logging.logger import get_logger
from backend.validators import validate_session_id
from fastapi import APIRouter, HTTPException, status

if TYPE_CHECKING:
    from backend.infrastructure.common.api.public.models import (
        CheckpointRequest,
        CheckpointResponse,
        FinalizeSessionRequest,
        FinalizeSessionResponse,
    )

logger = get_logger(__name__)
router = APIRouter()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SIMPLE WORKFLOW ENDPOINTS (delegate to orchestrator)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/sessions/{session_id}/diarization", status_code=status.HTTP_202_ACCEPTED)
async def diarize_session_workflow(
    session_id: str,
    orchestrator: WorkflowOrchestratorDep,
    audit_service: DIAuditService,
) -> dict:
    """
    Dispatch speaker diarization workflow.

    Uses WorkflowOrchestrator (injected via Depends).
    Business logic in WorkflowOrchestrator.dispatch_diarization().

    Args:
        session_id: Session identifier
        orchestrator: Injected WorkflowOrchestrator instance
        audit_service: Injected audit service

    Returns:
        dict with task_id, status, estimated_duration_seconds

    Raises:
        HTTPException(404): Audio file not found
        HTTPException(500): Dispatch failed
    """
    validate_session_id(session_id)

    try:
        result = await orchestrator.dispatch_diarization(
            session_id=session_id,
            audio_file_path=f"storage/{session_id}/audio.webm",
            language="es",
        )
        return result
    except FileNotFoundError as e:
        audit_service.log_action(
            action="workflow_dispatch_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"workflow": "diarization", "error": "audio_file_not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found for session {session_id}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="workflow_dispatch_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"workflow": "diarization", "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch diarization: {e!s}",
        ) from e


@router.post("/sessions/{session_id}/soap", status_code=status.HTTP_202_ACCEPTED)
async def generate_soap_workflow(
    session_id: str,
    orchestrator: WorkflowOrchestratorDep,
    audit_service: DIAuditService,
) -> dict:
    """
    Dispatch SOAP note generation workflow.

    Uses WorkflowOrchestrator (injected via Depends).
    Business logic in WorkflowOrchestrator.dispatch_soap_generation().

    Args:
        session_id: Session identifier
        orchestrator: Injected WorkflowOrchestrator instance
        audit_service: Injected audit service

    Returns:
        dict with task_id, status, estimated_duration_seconds

    Raises:
        HTTPException(400): Transcription not completed yet
        HTTPException(500): Dispatch failed
    """
    validate_session_id(session_id)

    try:
        result = await orchestrator.dispatch_soap_generation(
            session_id=session_id,
            language="es",
        )
        return result
    except ValueError as e:
        audit_service.log_action(
            action="workflow_dispatch_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"workflow": "soap", "error": "transcription_not_completed"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate SOAP note: {e!s}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="workflow_dispatch_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"workflow": "soap", "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch SOAP generation: {e!s}",
        ) from e


@router.post("/sessions/{session_id}/emotion", status_code=status.HTTP_202_ACCEPTED)
async def analyze_emotion_workflow(
    session_id: str,
    orchestrator: WorkflowOrchestratorDep,
    audit_service: DIAuditService,
) -> dict:
    """
    Dispatch emotional analysis workflow.

    Uses WorkflowOrchestrator (injected via Depends).
    Business logic in WorkflowOrchestrator.dispatch_emotion_analysis().

    Args:
        session_id: Session identifier
        orchestrator: Injected WorkflowOrchestrator instance
        audit_service: Injected audit service

    Returns:
        dict with task_id, status, model_used, estimated_duration_seconds

    Raises:
        HTTPException(400): Transcription not completed yet
        HTTPException(500): Dispatch failed
    """
    validate_session_id(session_id)

    try:
        result = await orchestrator.dispatch_emotion_analysis(
            session_id=session_id,
            language="es",
        )
        return result
    except ValueError as e:
        audit_service.log_action(
            action="workflow_dispatch_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"workflow": "emotion", "error": "transcription_not_completed"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot analyze emotion: {e!s}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="workflow_dispatch_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"workflow": "emotion", "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch emotion analysis: {e!s}",
        ) from e


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTELLIGENT WORKFLOW ENDPOINT (main orchestration)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/sessions/{session_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_session_intelligent_workflow(
    session_id: str,
    orchestration_service: IntelligentOrchestrationDep,
    audit_service: DIAuditService,
    language: str = "es",
    user_intent: str | None = None,
) -> dict:
    """
    Intelligently orchestrate workflow execution for a session.

    Uses IntelligentOrchestrationService (injected via Depends).
    Business logic in IntelligentOrchestrationService.orchestrate_intelligent_workflow().

    Algorithm (in service layer):
    1. Detect audio duration from file metadata
    2. Query existing tasks to avoid duplicates
    3. Route workflows using intelligent router
    4. Dispatch workflows in optimal order
    5. Return unified response

    Args:
        session_id: Session identifier
        orchestration_service: Injected IntelligentOrchestrationService instance
        audit_service: Injected audit service
        language: Session language code (default: "es")
        user_intent: Optional user-provided intent (e.g., "quick consult")

    Returns:
        dict with:
        - session_id: Session identifier
        - workflows_dispatched: List of dispatched workflow types
        - task_ids: Dict mapping workflow_type → task_id
        - routing_decision: Router's decision metadata
        - audio_duration_seconds: Detected audio duration
        - existing_tasks_skipped: List of skipped workflows
        - status: "dispatched"
        - cost: Cost metrics (routing, savings)
        - message: Human-readable summary

    Raises:
        HTTPException(404): Audio file not found
        HTTPException(500): Orchestration failed
    """
    validate_session_id(session_id)

    try:
        logger.info(
            "INTELLIGENT_WORKFLOW_STARTED",
            session_id=session_id,
            language=language,
            user_intent=user_intent,
        )

        # Delegate ALL business logic to IntelligentOrchestrationService
        result = await orchestration_service.orchestrate_intelligent_workflow(
            session_id=session_id,
            audio_file_path=f"storage/{session_id}/audio.webm",
            language=language,
            user_intent=user_intent,
        )

        logger.info(
            "INTELLIGENT_WORKFLOW_SUCCESS",
            session_id=session_id,
            workflows_dispatched=result["workflows_dispatched"],
            cost_usd=result["cost"]["routing_usd"],
        )

        return result

    except FileNotFoundError as e:
        audit_service.log_action(
            action="workflow_orchestration_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"workflow": "intelligent", "error": "audio_file_not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found for session {session_id}",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="workflow_orchestration_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"workflow": "intelligent", "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to orchestrate workflows: {e!s}",
        ) from e


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSION LIFECYCLE ENDPOINTS (delegate to internal functions)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.post("/sessions/{session_id}/finalize", status_code=status.HTTP_202_ACCEPTED)
async def finalize_session_workflow(
    session_id: str,
    request: FinalizeSessionRequest,
    audit_service: DIAuditService,
) -> FinalizeSessionResponse:
    """
    Finalize session workflow (merge transcription sources).

    Delegates to internal finalize_session function.
    No DI refactor needed (already uses internal function).

    Args:
        session_id: Session identifier
        request: Finalize request with transcription sources
        audit_service: Injected audit service

    Returns:
        FinalizeSessionResponse with merge results

    Raises:
        HTTPException(500): Finalization failed
    """
    from backend.api.routers.session.internal.sessions.finalize import (
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

        # Convert result to dict if needed
        if isinstance(result, dict):
            result_dict: dict[str, Any] = result
        else:
            result_dict = result.model_dump()

        from backend.infrastructure.common.api.public.models import FinalizeSessionResponse

        return FinalizeSessionResponse(**result_dict)

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="session_finalization_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize session: {e!s}",
        ) from e


@router.post("/sessions/{session_id}/checkpoint", status_code=status.HTTP_200_OK)
async def checkpoint_session_workflow(
    session_id: str,
    request: CheckpointRequest,
    audit_service: DIAuditService,
) -> CheckpointResponse:
    """
    Checkpoint session workflow (save partial progress).

    Delegates to internal checkpoint_session function.
    No DI refactor needed (already uses internal function).

    Args:
        session_id: Session identifier
        request: Checkpoint request with last chunk index
        audit_service: Injected audit service

    Returns:
        CheckpointResponse with concatenation results

    Raises:
        HTTPException(500): Checkpoint failed
    """
    from backend.api.routers.session.internal.sessions.checkpoint import (
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

        # Convert result to dict if needed
        if isinstance(result, dict):
            result_dict: dict[str, Any] = result
        else:
            result_dict = result.model_dump()

        from backend.infrastructure.common.api.public.models import CheckpointResponse

        return CheckpointResponse(**result_dict)

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="session_checkpoint_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"error": str(e), "last_chunk_idx": request.last_chunk_idx},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to checkpoint session: {e!s}",
        ) from e
