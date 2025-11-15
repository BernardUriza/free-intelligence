"""Celery workers initialization.

Warm-up singleton services when worker starts (NOT in each task).
This avoids re-initializing heavy models like Whisper on every fork.

Card: AUR-PROMPT-3.4
Created: 2025-11-09
"""

from __future__ import annotations

from backend.logger import get_logger

# Import all task modules for Celery autodiscovery
from backend.workers import (  # noqa: F401  # type: ignore[reportUnusedImport]
    diarization_tasks,
    transcription_tasks,
)

logger = get_logger(__name__)


def validate_worker_tasks() -> None:
    """
    Validate all registered tasks at worker startup.

    Ensures:
    - All task registrations are valid
    - No broken imports or orphaned references
    - Fails LOUDLY if there are issues (not silently!)

    This prevents the silent failures that plagued the old system.
    """
    logger.info("WORKER_TASK_VALIDATION_STARTING")

    try:
        from backend.workers.task_validator import validate_worker_startup
        from backend.workers.celery_app import celery_app

        validate_worker_startup(celery_app)
        logger.info("WORKER_TASK_VALIDATION_PASSED")
    except Exception as e:
        logger.error(
            "WORKER_TASK_VALIDATION_FAILED",
            error=str(e),
            exc_info=True,
        )
        raise


def warmup_worker_services() -> None:
    """
    Initialize heavy singleton services once when worker starts.

    Called by Celery worker signal (worker_process_init) to pre-load:
    - Task validation (ensure no orphaned tasks)
    - Whisper model (cached singleton)
    - Any other ML models

    This ensures workers don't deadlock trying to init models in forked processes,
    and validates that all tasks are properly registered.
    """
    import os

    logger.info("WORKER_WARMUP_STARTED", worker_pid=os.getpid())

    try:
        # 0. Validate worker tasks FIRST (fail early if there are issues)
        validate_worker_tasks()

        # 1. Warm-up Whisper model (singleton cached instance)
        from backend.services.transcription.whisper import (
            get_whisper_model,
            is_whisper_available,
        )

        if is_whisper_available():
            logger.info("WORKER_LOADING_WHISPER")
            model = get_whisper_model()
            if model:
                logger.info(
                    "WORKER_WHISPER_READY",
                    model_size=os.getenv("WHISPER_MODEL_SIZE", "small"),
                )
            else:
                logger.warning("WORKER_WHISPER_FAILED", reason="Model returned None")
        else:
            logger.warning("WORKER_WHISPER_UNAVAILABLE", reason="faster-whisper not installed")

    except Exception as e:
        logger.error("WORKER_WARMUP_FAILED", error=str(e), exc_info=True)
        raise

    logger.info("WORKER_WARMUP_COMPLETE")
