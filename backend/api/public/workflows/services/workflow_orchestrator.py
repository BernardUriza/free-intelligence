"""Workflow Orchestrator Service - Centralized workflow dispatch logic.

SOLID Principles Applied:
- Single Responsibility: ONLY orchestrates workflow execution
- Dependency Inversion: Depends on abstract worker interfaces, not concrete implementations
- Open/Closed: Adding new workflows doesn't require changing existing code

File: backend/api/public/workflows/services/workflow_orchestrator.py
Created: 2025-11-20
Pattern: Service Layer + Command Pattern
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import ensure_task_exists
from backend.workers.executor_pool import spawn_worker

logger = get_logger(__name__)


class WorkflowOrchestrator:
    """
    Centralized service for workflow orchestration.

    Responsibilities:
    - Dispatch workers for different task types
    - Create tasks in HDF5 before dispatching
    - Return consistent job responses
    - Log orchestration events

    Does NOT:
    - Access HDF5 directly (uses task_repository)
    - Contain business logic (just orchestration)
    - Handle HTTP concerns (that's the router's job)
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def dispatch_diarization(self, session_id: str) -> dict[str, Any]:
        """
        Dispatch diarization worker for a session.

        Args:
            session_id: Session identifier

        Returns:
            Job dispatch response with job_id and status
        """
        from backend.workers.tasks.diarization_worker import diarization_worker

        self.logger.info(
            "ORCHESTRATOR_DISPATCH_DIARIZATION",
            session_id=session_id,
        )

        # 1. Create task
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.DIARIZATION,
            allow_existing=True,
        )

        # 2. Dispatch worker
        spawn_worker(diarization_worker, session_id=session_id)
        job_id = session_id

        self.logger.info(
            "ORCHESTRATOR_DIARIZATION_DISPATCHED",
            session_id=session_id,
            job_id=job_id,
        )

        return {
            "session_id": session_id,
            "job_id": job_id,
            "status": "dispatched",
            "message": f"Diarization running in background (job {job_id}). Poll /sessions/{session_id}/monitor for progress.",
        }

    def dispatch_soap_generation(self, session_id: str) -> dict[str, Any]:
        """
        Dispatch SOAP generation worker for a session.

        Args:
            session_id: Session identifier

        Returns:
            Job dispatch response with job_id and status
        """
        from backend.workers.tasks.soap_worker import generate_soap_worker

        self.logger.info(
            "ORCHESTRATOR_DISPATCH_SOAP",
            session_id=session_id,
        )

        # 1. Create task
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.SOAP_GENERATION,
            allow_existing=True,
        )

        # 2. Dispatch worker
        spawn_worker(generate_soap_worker, session_id=session_id)
        job_id = session_id

        self.logger.info(
            "ORCHESTRATOR_SOAP_DISPATCHED",
            session_id=session_id,
            job_id=job_id,
        )

        return {
            "session_id": session_id,
            "job_id": job_id,
            "status": "dispatched",
            "message": f"SOAP generation running in background (job {job_id}). Poll /sessions/{session_id}/monitor for progress.",
        }

    def dispatch_emotion_analysis(self, session_id: str) -> dict[str, Any]:
        """
        Dispatch emotion analysis worker for a session.

        Args:
            session_id: Session identifier

        Returns:
            Job dispatch response with job_id and status
        """
        from backend.workers.tasks.emotion_worker import analyze_emotion_worker

        self.logger.info(
            "ORCHESTRATOR_DISPATCH_EMOTION",
            session_id=session_id,
        )

        # 1. Create task
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.EMOTION_ANALYSIS,
            allow_existing=True,
        )

        # 2. Dispatch worker
        spawn_worker(analyze_emotion_worker, session_id=session_id)
        job_id = session_id

        self.logger.info(
            "ORCHESTRATOR_EMOTION_DISPATCHED",
            session_id=session_id,
            job_id=job_id,
        )

        return {
            "session_id": session_id,
            "job_id": job_id,
            "status": "dispatched",
            "message": f"Emotion analysis running in background (job {job_id}). Poll /sessions/{session_id}/monitor for progress.",
        }

    def dispatch_encryption(self, session_id: str) -> dict[str, Any]:
        """
        Dispatch encryption worker for a session.

        Args:
            session_id: Session identifier

        Returns:
            Encryption dispatch response
        """
        from backend.workers.tasks.encryption_worker import encrypt_session_worker

        self.logger.info(
            "ORCHESTRATOR_DISPATCH_ENCRYPTION",
            session_id=session_id,
        )

        # 1. Create task
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.ENCRYPTION,
            allow_existing=True,
        )

        # 2. Dispatch worker
        spawn_worker(encrypt_session_worker, session_id=session_id)
        encryption_task_id = f"{session_id}_encryption"

        self.logger.info(
            "ORCHESTRATOR_ENCRYPTION_DISPATCHED",
            session_id=session_id,
            encryption_task_id=encryption_task_id,
        )

        return {
            "encryption_status": "QUEUED",
            "encryption_task_id": encryption_task_id,
            "finalized_at": datetime.now(UTC).isoformat(),
        }

    def dispatch_workflow(self, workflow: str, session_id: str) -> dict[str, Any]:
        """
        Generic workflow dispatch method.

        Args:
            workflow: Workflow type (DIARIZATION, SOAP_GENERATION, etc.)
            session_id: Session identifier

        Returns:
            Job dispatch response

        Raises:
            ValueError: If workflow type is unknown
        """
        workflow_map = {
            TaskType.DIARIZATION.value: self.dispatch_diarization,
            TaskType.SOAP_GENERATION.value: self.dispatch_soap_generation,
            TaskType.EMOTION_ANALYSIS.value: self.dispatch_emotion_analysis,
            TaskType.ENCRYPTION.value: self.dispatch_encryption,
        }

        if workflow not in workflow_map:
            raise ValueError(f"Unknown workflow type: {workflow}")

        return workflow_map[workflow](session_id)


# ============================================================================
# GLOBAL ORCHESTRATOR INSTANCE (Singleton)
# ============================================================================

_orchestrator: WorkflowOrchestrator | None = None


def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """Get or create global workflow orchestrator instance."""
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = WorkflowOrchestrator()

    return _orchestrator
