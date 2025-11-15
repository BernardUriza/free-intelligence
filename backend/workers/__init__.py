"""Worker functions initialization.

DEPRECATED: Celery removed as of 2025-11-15.
All workers now run synchronously via ThreadPoolExecutor.

Warm-up singleton services when worker starts (NOT in each task).
This avoids re-initializing heavy models like Whisper on every fork.

Card: Migration from Celery to sync workers
Created: 2025-11-09
Updated: 2025-11-15 (Removed Celery, switched to sync workers)
"""

from __future__ import annotations

from backend.logger import get_logger

logger = get_logger(__name__)


def validate_worker_tasks() -> None:
    """
    DEPRECATED: Celery validation no longer needed.

    Validate all registered tasks at startup (placeholder).
    """
    logger.info("WORKER_TASK_VALIDATION_SKIPPED_NO_CELERY")


def warmup_worker_services() -> None:
    """
    DEPRECATED: Celery warmup no longer needed.

    Initialize heavy singleton services (placeholder for sync workers).
    """
    import os

    logger.info("WORKER_WARMUP_SKIPPED_NO_CELERY", worker_pid=os.getpid())
