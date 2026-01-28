"""Worker pool interface.

Manages background task execution (transcription, diarization, etc.).
Decouples services from ThreadPoolExecutor implementation.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from abc import ABC, abstractmethod
from typing import Any, Callable


class IWorkerPool(ABC):
    """Background task execution abstraction.

    Responsibilities:
    - Execute CPU-bound tasks in thread pool
    - Execute I/O-bound tasks in async pool
    - Monitor worker health and queue depth
    - Handle worker failures and retries

    Worker Types:
    - transcription: Audio-to-text processing (10-15s per chunk)
    - diarization: Speaker separation (5-10s per chunk)
    - soap_generation: Clinical note generation (2-5s)
    - export: Data export operations (variable duration)

    Clean Architecture Benefits:
    - Services don't know about ThreadPoolExecutor internals
    - Easy to test with synchronous mock
    - Can swap to Celery/RQ without changing services
    """

    @abstractmethod
    def submit_task(
        self,
        worker_func: Callable[..., Any],
        *args: Any,
        task_name: str | None = None,
        priority: int = 0,
        **kwargs: Any,
    ) -> str:
        """Submit task to worker pool.

        Args:
            worker_func: Callable to execute (must be picklable if using process pool)
            *args: Positional arguments for worker_func
            task_name: Optional human-readable task name (for logging)
            priority: Task priority (higher = more important, default 0)
            **kwargs: Keyword arguments for worker_func

        Returns:
            Task ID (UUID)

        Raises:
            ValueError: If worker_func is not callable
            RuntimeError: If pool is shut down
        """
        pass

    @abstractmethod
    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Get task execution status.

        Args:
            task_id: Task UUID

        Returns:
            Dict with keys:
                - task_id: str
                - status: str (pending, running, completed, failed)
                - submitted_at: str (ISO 8601)
                - started_at: str | None (ISO 8601)
                - completed_at: str | None (ISO 8601)
                - result: Any (if completed)
                - error: str | None (if failed)

        Raises:
            ValueError: If task_id doesn't exist
        """
        pass

    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        """Cancel pending or running task.

        Args:
            task_id: Task UUID

        Returns:
            True if cancellation successful, False if task not found or already completed

        Note:
            Running tasks may not be immediately cancelled (depends on worker implementation)
        """
        pass

    @abstractmethod
    def get_pool_stats(self) -> dict[str, Any]:
        """Get worker pool statistics.

        Returns:
            Dict with keys:
                - active_workers: int (currently executing tasks)
                - pending_tasks: int (queued tasks)
                - completed_tasks: int (total completed since start)
                - failed_tasks: int (total failed since start)
                - pool_size: int (max workers)
                - uptime_seconds: float (pool uptime)
        """
        pass

    @abstractmethod
    def shutdown(self, wait: bool = True, timeout: float | None = None) -> None:
        """Shutdown worker pool.

        Args:
            wait: If True, wait for pending tasks to complete
            timeout: Maximum time to wait (None = wait forever)

        Raises:
            TimeoutError: If shutdown exceeds timeout
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if worker pool is healthy.

        Returns:
            True if pool is operational and accepting tasks

        Health checks:
        - Pool not shut down
        - Workers responsive (no deadlocks)
        - Queue depth within limits
        """
        pass
