"""Workflow Orchestrator Service - Centralized workflow dispatch logic (REFACTORED with DI).

REFACTORED: Uses constructor injection instead of get_container().

SOLID Principles Applied:
- Single Responsibility: ONLY orchestrates workflow execution
- Dependency Inversion: Depends on abstract worker interfaces, not concrete implementations
- Open/Closed: Adding new workflows doesn't require changing existing code

File: backend/api/public/workflows/services/workflow_orchestrator.py
Created: 2025-11-20
Refactored: 2026-01-28 (Phase 2.3 - DI pattern)
Pattern: Service Layer + Command Pattern
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.infrastructure.workers.executor_pool import spawn_worker
from backend.models.task_type import TaskType
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class WorkflowOrchestrator:
    """
    Centralized service for workflow orchestration (REFACTORED with DI).

    Responsibilities:
    - Dispatch workers for different task types
    - Create tasks in HDF5 before dispatching
    - Return consistent job responses
    - Log orchestration events

    Does NOT:
    - Access HDF5 directly (uses task_repository)
    - Contain business logic (just orchestration)
    - Handle HTTP concerns (that's the router's job)

    Dependencies eliminated from get_container():
    - ITaskRepository (4 calls) → Constructor injected
    """

    def __init__(
        self,
        task_repository: ITaskRepository,
        logger: ILogger | None = None,
    ) -> None:
        """Initialize workflow orchestrator with dependencies.

        Args:
            task_repository: Task repository for task creation/checking
            logger: Logger instance (defaults to module logger)
        """
        self.task_repo = task_repository
        self.logger = logger or get_logger(__name__)

    def dispatch_diarization(self, session_id: str) -> dict[str, Any]:
        """
        Dispatch diarization worker for a session.

        Args:
            session_id: Session identifier

        Returns:
            Job dispatch response with job_id and status
        """
        from backend.infrastructure.workers.tasks.diarization_worker import diarize_session_worker

        self.logger.info(
            "ORCHESTRATOR_DISPATCH_DIARIZATION",
            session_id=session_id,
        )

        # 1. Create task
        self.task_repo.task_exists(
            session_id=session_id,
            task_type=TaskType.DIARIZATION,
            allow_existing=True,
        )

        # 2. Dispatch worker
        spawn_worker(diarize_session_worker, session_id=session_id, task_repo=self.task_repo)
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
        from backend.infrastructure.workers.tasks.soap_worker import generate_soap_worker

        self.logger.info(
            "ORCHESTRATOR_DISPATCH_SOAP",
            session_id=session_id,
        )

        # 1. Create task
        self.task_repo.task_exists(
            session_id=session_id,
            task_type=TaskType.SOAP_GENERATION,
            allow_existing=True,
        )

        # 2. Dispatch worker
        spawn_worker(generate_soap_worker, session_id=session_id, task_repo=self.task_repo)
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
        from backend.infrastructure.workers.tasks.emotion_worker import analyze_emotion_worker

        self.logger.info(
            "ORCHESTRATOR_DISPATCH_EMOTION",
            session_id=session_id,
        )

        # 1. Create task
        self.task_repo.task_exists(
            session_id=session_id,
            task_type=TaskType.EMOTION_ANALYSIS,
            allow_existing=True,
        )

        # 2. Dispatch worker
        spawn_worker(analyze_emotion_worker, session_id=session_id, task_repo=self.task_repo)
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
        from backend.infrastructure.workers.tasks.encryption_worker import encrypt_session_worker

        self.logger.info(
            "ORCHESTRATOR_DISPATCH_ENCRYPTION",
            session_id=session_id,
        )

        # 1. Create task
        self.task_repo.task_exists(
            session_id=session_id,
            task_type=TaskType.ENCRYPTION,
            allow_existing=True,
        )

        # 2. Dispatch worker
        from pathlib import Path
        h5_path = str(Path("storage/corpus.h5"))
        spawn_worker(encrypt_session_worker, session_id=session_id, h5_path=h5_path, task_repo=self.task_repo)
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
        # Normalize workflow keying: use lowercase enum names for consistency
        workflow_map = {
            TaskType.DIARIZATION.name.lower(): self.dispatch_diarization,
            TaskType.SOAP_GENERATION.name.lower(): self.dispatch_soap_generation,
            TaskType.EMOTION_ANALYSIS.name.lower(): self.dispatch_emotion_analysis,
            TaskType.ENCRYPTION.name.lower(): self.dispatch_encryption,
        }

        key = workflow.lower()
        if key not in workflow_map:
            raise ValueError(f"Unknown workflow type: {workflow}")

        return workflow_map[key](session_id)
