"""Workflow Completion Tracker - Detecta cuándo todos los tasks terminan.

Philosophy:
  - Fire-and-forget workers → no garantía de completion
  - Frontend polling → ineficiente, no sabe cuándo parar
  - WorkflowTracker → centraliza estado, detecta completion

Benefits:
  - Detecta cuándo workflow completa (todos los tasks done)
  - Identifica tasks fallidos para retry
  - Trigger automático de consolidación
  - Reduces frontend polling burden

Architecture:
  PUBLIC endpoint → Dispatches workers → Workers call tracker
  Tracker → Updates state → Emits completion events
  Frontend → Polls /monitor → Gets aggregated status

Created: 2025-12-03
Author: Claude Code (P1 Architectural Fix)
Pattern: State Machine + Event Emitter
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from backend.models.task_type import TaskStatus, TaskType
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkflowState(str, Enum):
    """Overall workflow state"""

    PENDING = "pending"  # No tasks started yet
    IN_PROGRESS = "in_progress"  # Some tasks running
    COMPLETED = "completed"  # All tasks succeeded
    FAILED = "failed"  # One or more tasks failed critically
    PARTIAL = "partial"  # Some succeeded, some failed (non-critical)


@dataclass
class TaskExecution:
    """Execution state for a single task"""

    task_type: str
    status: TaskStatus
    started_at: str | None = None
    completed_at: str | None = None
    failed_at: str | None = None
    error: str | None = None
    duration_seconds: float | None = None
    result: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStatus:
    """Complete workflow status"""

    session_id: str
    state: WorkflowState
    tasks: dict[str, TaskExecution]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    in_progress_tasks: int
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WORKFLOW TRACKER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class WorkflowTracker:
    """
    Tracks workflow execution state across multiple tasks.

    Thread-safe, in-memory state tracking with optional persistence.

    Usage:
        tracker = get_workflow_tracker()

        # Worker starts
        tracker.mark_task_started("session-123", TaskType.DIARIZATION)

        # Worker completes
        tracker.mark_task_completed("session-123", TaskType.DIARIZATION, result={...})

        # Worker fails
        tracker.mark_task_failed("session-123", TaskType.DIARIZATION, error="...")

        # Check if workflow done
        if tracker.is_workflow_complete("session-123", expected_tasks):
            trigger_consolidation("session-123")
    """

    def __init__(self, task_repository):
        """Initialize workflow tracker with dependencies.

        Args:
            task_repository: Task repository for session validation (required for DI)
        """
        self.logger = get_logger(__name__)
        self.task_repo = task_repository
        # session_id → {task_type → TaskExecution}
        self._workflows: dict[str, dict[str, TaskExecution]] = defaultdict(dict)
        self._lock = threading.RLock()

    def mark_task_started(
        self,
        session_id: str,
        task_type: TaskType | str,
    ) -> None:
        """Mark task as started.

        Args:
            session_id: Session identifier
            task_type: Task type (enum or string)
        """
        task_str = task_type.value if isinstance(task_type, TaskType) else task_type

        with self._lock:
            execution = TaskExecution(
                task_type=task_str,
                status=TaskStatus.IN_PROGRESS,
                started_at=datetime.now(UTC).isoformat(),
            )
            self._workflows[session_id][task_str] = execution

        self.logger.info(
            "WORKFLOW_TASK_STARTED",
            session_id=session_id,
            task_type=task_str,
        )

    def mark_task_completed(
        self,
        session_id: str,
        task_type: TaskType | str,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Mark task as completed.

        Args:
            session_id: Session identifier
            task_type: Task type
            result: Optional result data
        """
        task_str = task_type.value if isinstance(task_type, TaskType) else task_type

        with self._lock:
            if task_str not in self._workflows[session_id]:
                self.logger.warning(
                    "WORKFLOW_TASK_NOT_TRACKED",
                    session_id=session_id,
                    task_type=task_str,
                    hint="Task completed without being started",
                )
                # Create entry retroactively
                self._workflows[session_id][task_str] = TaskExecution(
                    task_type=task_str,
                    status=TaskStatus.COMPLETED,
                    started_at=datetime.now(UTC).isoformat(),
                    completed_at=datetime.now(UTC).isoformat(),
                    result=result or {},
                )
                return

            execution = self._workflows[session_id][task_str]
            execution.status = TaskStatus.COMPLETED
            execution.completed_at = datetime.now(UTC).isoformat()
            execution.result = result or {}

            # Calculate duration
            if execution.started_at:
                start = datetime.fromisoformat(execution.started_at)
                end = datetime.fromisoformat(execution.completed_at)
                execution.duration_seconds = (end - start).total_seconds()

        self.logger.info(
            "WORKFLOW_TASK_COMPLETED",
            session_id=session_id,
            task_type=task_str,
            duration_seconds=execution.duration_seconds,
        )

        # Check if workflow completed
        self._check_workflow_completion(session_id)

    def mark_task_failed(
        self,
        session_id: str,
        task_type: TaskType | str,
        error: str,
    ) -> None:
        """Mark task as failed.

        Args:
            session_id: Session identifier
            task_type: Task type
            error: Error message
        """
        task_str = task_type.value if isinstance(task_type, TaskType) else task_type

        with self._lock:
            if task_str not in self._workflows[session_id]:
                self._workflows[session_id][task_str] = TaskExecution(
                    task_type=task_str,
                    status=TaskStatus.FAILED,
                    started_at=datetime.now(UTC).isoformat(),
                    failed_at=datetime.now(UTC).isoformat(),
                    error=error,
                )
            else:
                execution = self._workflows[session_id][task_str]
                execution.status = TaskStatus.FAILED
                execution.failed_at = datetime.now(UTC).isoformat()
                execution.error = error

                # Calculate duration
                if execution.started_at:
                    start = datetime.fromisoformat(execution.started_at)
                    end = datetime.fromisoformat(execution.failed_at)
                    execution.duration_seconds = (end - start).total_seconds()

        self.logger.error(
            "WORKFLOW_TASK_FAILED",
            session_id=session_id,
            task_type=task_str,
            error=error,
        )

    def is_workflow_complete(
        self,
        session_id: str,
        expected_tasks: list[TaskType | str],
    ) -> bool:
        """Check if all expected tasks are completed.

        Args:
            session_id: Session identifier
            expected_tasks: List of tasks that should be completed

        Returns:
            True if all tasks are in COMPLETED state
        """
        with self._lock:
            if session_id not in self._workflows:
                return False

            workflow = self._workflows[session_id]
            for task in expected_tasks:
                task_str = task.value if isinstance(task, TaskType) else task
                if task_str not in workflow:
                    return False
                if workflow[task_str].status != TaskStatus.COMPLETED:
                    return False

            return True

    def get_workflow_status(self, session_id: str) -> WorkflowStatus:
        """Get complete workflow status.

        Args:
            session_id: Session identifier

        Returns:
            WorkflowStatus with aggregated state
        """
        with self._lock:
            if session_id not in self._workflows:
                return WorkflowStatus(
                    session_id=session_id,
                    state=WorkflowState.PENDING,
                    tasks={},
                    total_tasks=0,
                    completed_tasks=0,
                    failed_tasks=0,
                    in_progress_tasks=0,
                )

            tasks = self._workflows[session_id]
            completed = sum(1 for t in tasks.values() if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in tasks.values() if t.status == TaskStatus.FAILED)
            in_progress = sum(1 for t in tasks.values() if t.status == TaskStatus.IN_PROGRESS)

            # Determine overall state
            if completed == len(tasks) and len(tasks) > 0:
                state = WorkflowState.COMPLETED
            elif failed > 0 and completed == 0:
                state = WorkflowState.FAILED
            elif failed > 0 and completed > 0:
                state = WorkflowState.PARTIAL
            elif in_progress > 0:
                state = WorkflowState.IN_PROGRESS
            else:
                state = WorkflowState.PENDING

            # Calculate workflow duration
            started_at = None
            completed_at = None
            duration = None

            if tasks:
                start_times = [t.started_at for t in tasks.values() if t.started_at]
                if start_times:
                    started_at = min(start_times)

                end_times = [
                    t.completed_at or t.failed_at
                    for t in tasks.values()
                    if t.completed_at or t.failed_at
                ]
                if end_times and len(end_times) == len(tasks):
                    completed_at = max(end_times)

                if started_at and completed_at:
                    start = datetime.fromisoformat(started_at)
                    end = datetime.fromisoformat(completed_at)
                    duration = (end - start).total_seconds()

            return WorkflowStatus(
                session_id=session_id,
                state=state,
                tasks=tasks,
                total_tasks=len(tasks),
                completed_tasks=completed,
                failed_tasks=failed,
                in_progress_tasks=in_progress,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )

    def get_failed_tasks(self, session_id: str) -> list[TaskExecution]:
        """Get list of failed tasks for retry.

        Args:
            session_id: Session identifier

        Returns:
            List of failed task executions
        """
        with self._lock:
            if session_id not in self._workflows:
                return []

            return [
                task
                for task in self._workflows[session_id].values()
                if task.status == TaskStatus.FAILED
            ]

    def clear_workflow(self, session_id: str) -> None:
        """Clear workflow state (for cleanup/testing).

        Args:
            session_id: Session identifier
        """
        with self._lock:
            if session_id in self._workflows:
                del self._workflows[session_id]
                self.logger.debug("WORKFLOW_CLEARED", session_id=session_id)

    def _check_workflow_completion(self, session_id: str) -> None:
        """Internal: Check if workflow completed and emit event.

        Args:
            session_id: Session identifier
        """
        with self._lock:
            status = self.get_workflow_status(session_id)

            if status.state == WorkflowState.COMPLETED:
                self.logger.info(
                    "WORKFLOW_COMPLETED",
                    session_id=session_id,
                    total_tasks=status.total_tasks,
                    duration_seconds=status.duration_seconds,
                )

                # Trigger automatic consolidation (async to avoid blocking)
                self._trigger_consolidation_async(session_id)

            elif status.state == WorkflowState.FAILED:
                self.logger.error(
                    "WORKFLOW_FAILED",
                    session_id=session_id,
                    failed_tasks=status.failed_tasks,
                    total_tasks=status.total_tasks,
                )

    def _trigger_consolidation_async(self, session_id: str) -> None:
        """Trigger session consolidation in background thread.

        Consolidation moves session data from session-level HDF5 files
        into the main corpus.h5 for long-term storage.

        Args:
            session_id: Session identifier to consolidate
        """
        import threading

        def consolidate_in_background():
            """Background consolidation with error handling."""
            try:

                def consolidate_session_to_corpus(session_id, delete_after=False):
                    """Validate session exists in corpus.h5 (already consolidated in new architecture).

                    Old architecture: session data in storage/sessions/{id}.h5 → consolidate to corpus.h5
                    New architecture: session data written directly to corpus.h5 → no consolidation needed

                    This function validates the session exists and is ready for long-term storage.
                    """
                    # Use injected task_repo (from WorkflowTracker.__init__)
                    task_repo = self.task_repo

                    # Validate session has at least TRANSCRIPTION task
                    if not task_repo.task_exists(session_id, "TRANSCRIPTION"):
                        self.logger.warning(
                            "CONSOLIDATION_VALIDATION_FAILED",
                            session_id=session_id,
                            reason="TRANSCRIPTION task not found in corpus.h5",
                        )
                        return False

                    self.logger.info(
                        "CONSOLIDATION_VALIDATED",
                        session_id=session_id,
                        message="Session data already in corpus.h5 (new DI architecture)",
                    )
                    return True

                self.logger.info(
                    "CONSOLIDATION_STARTED",
                    session_id=session_id,
                    message="Starting automatic consolidation after workflow completion",
                )

                success = consolidate_session_to_corpus(session_id, delete_after=True)

                if success:
                    self.logger.info(
                        "CONSOLIDATION_COMPLETED",
                        session_id=session_id,
                        message="Session successfully consolidated to corpus",
                    )
                else:
                    self.logger.warning(
                        "CONSOLIDATION_FAILED",
                        session_id=session_id,
                        message="Consolidation returned False - session may need manual consolidation",
                    )

            except ImportError as e:
                self.logger.error(
                    "CONSOLIDATION_IMPORT_ERROR",
                    session_id=session_id,
                    error=str(e),
                    message="consolidate_session_to_corpus not available - session not consolidated",
                )
            except Exception as e:
                self.logger.error(
                    "CONSOLIDATION_ERROR",
                    session_id=session_id,
                    error=str(e),
                    message="Unexpected error during consolidation - session not consolidated",
                )

        # Run in background thread to avoid blocking workflow completion
        consolidation_thread = threading.Thread(
            target=consolidate_in_background,
            name=f"consolidate-{session_id}",
            daemon=True,
        )
        consolidation_thread.start()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GLOBAL TRACKER INSTANCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_tracker: WorkflowTracker | None = None
_tracker_lock = threading.Lock()


def get_workflow_tracker() -> WorkflowTracker:
    """Get or create global workflow tracker (singleton) - Phase 4B.

    Note:
        No longer uses service locator (get_container).
        Direct instantiation with HDF5TaskRepository for singleton initialization.
    """
    from pathlib import Path

    from backend.repositories.task_repository import HDF5TaskRepository

    global _tracker

    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                # Direct instantiation (Phase 4B) - one-time cost for singleton
                _corpus_path = Path(__file__).parent.parent.parent.parent / "storage" / "corpus.h5"
                _tracker = WorkflowTracker(
                    task_repository=HDF5TaskRepository(_corpus_path)
                )
                logger.info("WORKFLOW_TRACKER_INITIALIZED")

    return _tracker
