"""Workflow state tracking interface for thread-safe task monitoring.

This interface abstracts state management, enabling in-memory or distributed (Redis)
tracking without changing orchestration code.
"""

from abc import ABC, abstractmethod
from typing import Any


class IWorkflowTracker(ABC):
    """
    Interface for thread-safe workflow state tracking.

    Responsibilities:
    - Track task lifecycle (started, completed, failed)
    - Detect workflow completion (all tasks done)
    - Provide workflow status snapshots
    - Prevent duplicate task execution

    Decouples:
    - Orchestration logic from state storage mechanism
    - Business logic from implementation (in-memory vs Redis)

    Clean Architecture Benefits:
    - Easy to swap in-memory → Redis for distributed systems
    - Thread-safe by contract (implementations must guarantee)
    - Testable via mocks (no real storage needed)

    Implementation Options:
    - In-memory: Dict with locks (good for single-server)
    - Redis: Distributed state (good for multi-server)
    - PostgreSQL: Persistent state with audit trail
    """

    @abstractmethod
    def mark_task_started(
        self,
        session_id: str,
        task_type: str,
    ) -> None:
        """
        Mark a task as started (in-progress state).

        Thread-safe: Multiple workers can call simultaneously.

        Args:
            session_id: Unique session identifier
            task_type: Task type (e.g., "diarization", "soap_generation")

        Side Effects:
            - Updates in-memory/Redis state
            - Prevents duplicate execution (idempotent)
        """
        ...

    @abstractmethod
    def mark_task_completed(
        self,
        session_id: str,
        task_type: str,
    ) -> None:
        """
        Mark a task as successfully completed.

        Thread-safe: Multiple workers can call simultaneously.

        Args:
            session_id: Unique session identifier
            task_type: Task type (e.g., "diarization", "soap_generation")

        Side Effects:
            - Updates in-memory/Redis state
            - Triggers workflow completion check (if all tasks done)
        """
        ...

    @abstractmethod
    def mark_task_failed(
        self,
        session_id: str,
        task_type: str,
        error: str,
    ) -> None:
        """
        Mark a task as failed with error message.

        Thread-safe: Multiple workers can call simultaneously.

        Args:
            session_id: Unique session identifier
            task_type: Task type (e.g., "diarization", "soap_generation")
            error: Error message or exception string

        Side Effects:
            - Updates in-memory/Redis state
            - May trigger retry logic (implementation-specific)
            - Logs error for debugging
        """
        ...

    @abstractmethod
    def is_workflow_complete(
        self,
        session_id: str,
        expected_tasks: list[str],
    ) -> bool:
        """
        Check if all expected tasks are completed.

        Thread-safe: Multiple workers can call simultaneously.

        Args:
            session_id: Unique session identifier
            expected_tasks: List of task types that must complete
                           (e.g., ["diarization", "transcription", "soap_generation"])

        Returns:
            True if ALL expected tasks are in "completed" state, False otherwise

        Example:
            tracker.is_workflow_complete(
                "session-123",
                ["diarization", "soap_generation"]
            )
            # Returns True if both tasks completed, False if any pending/failed
        """
        ...

    @abstractmethod
    def get_workflow_status(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Get current status snapshot for all tasks in workflow.

        Thread-safe: Multiple workers can call simultaneously.

        Args:
            session_id: Unique session identifier

        Returns:
            dict with keys:
            - session_id: Session identifier
            - tasks: Dict[task_type, status] mapping
                    (e.g., {"diarization": "completed", "soap": "in_progress"})
            - started_at: Workflow start timestamp (ISO 8601)
            - completed_at: Workflow completion timestamp (ISO 8601, None if incomplete)
            - failed_tasks: List of tasks that failed
            - pending_tasks: List of tasks not yet started

        Example:
            {
                "session_id": "session-123",
                "tasks": {
                    "diarization": "completed",
                    "transcription": "in_progress",
                    "soap_generation": "pending",
                },
                "started_at": "2026-01-31T10:00:00Z",
                "completed_at": None,
                "failed_tasks": [],
                "pending_tasks": ["soap_generation"],
            }
        """
        ...

    @abstractmethod
    def clear_workflow(
        self,
        session_id: str,
    ) -> None:
        """
        Clear all workflow state for session (cleanup after completion).

        Thread-safe: Multiple workers can call simultaneously (idempotent).

        Args:
            session_id: Unique session identifier

        Side Effects:
            - Removes in-memory/Redis state
            - Frees resources (memory, connections)
            - Does NOT delete task results (those persist in storage)

        Use Cases:
            - After workflow completion (cleanup)
            - On session deletion (garbage collection)
            - After workflow cancellation
        """
        ...
