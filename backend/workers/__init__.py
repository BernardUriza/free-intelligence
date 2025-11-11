"""Celery workers initialization.

Warm-up singleton services when worker starts (NOT in each task).
This avoids re-initializing heavy models like Whisper on every fork.

Card: AUR-PROMPT-3.4
Created: 2025-11-09
"""

from __future__ import annotations

from backend.logger import get_logger

logger = get_logger(__name__)


def warmup_worker_services() -> None:
    """
    Initialize heavy singleton services once when worker starts.

    Called by Celery worker signal (worker_process_init) to pre-load:
    - Whisper model (cached singleton)
    - Any other ML models

    This ensures workers don't deadlock trying to init models in forked processes.
    """
    import os

    logger.info("WORKER_WARMUP_STARTED", worker_pid=os.getpid())

    try:
        # Warm-up Whisper model (singleton cached instance)
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
            logger.warning(
                "WORKER_WHISPER_UNAVAILABLE", reason="faster-whisper not installed"
            )

    except Exception as e:
        logger.error("WORKER_WARMUP_FAILED", error=str(e), exc_info=True)
        raise

    logger.info("WORKER_WARMUP_COMPLETE")
