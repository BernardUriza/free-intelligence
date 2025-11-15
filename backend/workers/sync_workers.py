"""Synchronous worker functions (replaces Celery tasks).

PHILOSOPHY:
  - Run synchronously in the request thread
  - No async/background processing for MVP
  - Keep same function signatures as Celery tasks
  - Called from API routers and services

Functions:
  - transcribe_chunk_worker: Synchronous transcription (Whisper ASR)
  - diarize_session_worker: Synchronous diarization (speaker separation)
  - log_audit_event_worker: Synchronous audit logging

Created: 2025-11-15
Updated: Migration from Celery to sync workers
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from backend.app.audit.sink import write_audit_event
from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType
from backend.storage.task_repository import (
    ensure_task_exists,
    get_task_metadata,
    update_task_metadata,
)

logger = get_logger(__name__)


def transcribe_chunk_worker(
    session_id: str,
    chunk_number: int,
    stt_provider: str = "faster_whisper",
) -> dict[str, Any]:
    """Synchronous transcription of audio chunk.

    This replaces transcribe_chunk_task (Celery).

    Args:
        session_id: Session identifier
        chunk_number: Chunk index
        stt_provider: Provider name (faster_whisper, deepgram, azure_whisper)

    Returns:
        dict with transcript, duration, language, confidence
    """
    start_time = time.time()

    try:
        logger.info(
            "TRANSCRIBE_CHUNK_START",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=stt_provider,
        )

        # Ensure TRANSCRIPTION task exists
        ensure_task_exists(session_id, TaskType.TRANSCRIPTION)

        # Get task metadata to find audio path in HDF5
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)
        chunk_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/chunks/chunk_{chunk_number}"

        # For now, read audio from HDF5 and transcribe with faster-whisper
        # (Deepgram integration can be added later as async option)
        from backend.services.transcription_service import TranscriptionService

        service = TranscriptionService()
        result = service.transcribe_chunk(session_id, chunk_number, stt_provider)

        # Update task metadata with progress
        total_chunks = task_metadata.get("total_chunks", 1)
        processed = task_metadata.get("processed_chunks", 0) + 1
        progress = int((processed / total_chunks) * 100)

        update_task_metadata(
            session_id,
            TaskType.TRANSCRIPTION,
            {
                "processed_chunks": processed,
                "progress_percent": progress,
                "last_chunk": chunk_number,
                "status": TaskStatus.IN_PROGRESS
                if processed < total_chunks
                else TaskStatus.COMPLETED,
            },
        )

        elapsed = time.time() - start_time
        logger.info(
            "TRANSCRIBE_CHUNK_SUCCESS",
            session_id=session_id,
            chunk_number=chunk_number,
            duration_seconds=elapsed,
        )

        return {
            "session_id": session_id,
            "chunk_number": chunk_number,
            "status": "SUCCESS",
            "result": result,
            "duration_seconds": elapsed,
        }

    except Exception as e:
        logger.error(
            "TRANSCRIBE_CHUNK_FAILED",
            session_id=session_id,
            chunk_number=chunk_number,
            error=str(e),
        )
        raise


def diarize_session_worker(
    session_id: str, diarization_provider: Optional[str] = None
) -> dict[str, Any]:
    """Synchronous diarization (speaker separation + text improvement).

    This replaces diarize_session_task (Celery).

    Args:
        session_id: Session identifier
        diarization_provider: Provider (pyannote, deepgram, ollama, claude)

    Returns:
        dict with diarization results (segments, confidence, model)
    """
    start_time = time.time()

    try:
        logger.info(
            "DIARIZE_SESSION_START",
            session_id=session_id,
            provider=diarization_provider,
        )

        # Ensure DIARIZATION task exists
        ensure_task_exists(session_id, TaskType.DIARIZATION)

        # Run diarization service
        from backend.policy.policy_loader import get_policy_loader
        from backend.services.diarization.diarization_service import DiarizationService

        if diarization_provider is None:
            policy_loader = get_policy_loader()
            policy = policy_loader.load_policy("diarization")
            diarization_provider = policy.get("primary_provider", "ollama")

        service = DiarizationService()
        result = service.diarize_session(session_id, diarization_provider)

        # Update task metadata
        update_task_metadata(
            session_id,
            TaskType.DIARIZATION,
            {
                "status": TaskStatus.COMPLETED,
                "provider": diarization_provider,
                "segment_count": len(result.get("segments", [])),
            },
        )

        elapsed = time.time() - start_time
        logger.info(
            "DIARIZE_SESSION_SUCCESS",
            session_id=session_id,
            duration_seconds=elapsed,
            segments=len(result.get("segments", [])),
        )

        return {
            "session_id": session_id,
            "status": "SUCCESS",
            "result": result,
            "duration_seconds": elapsed,
        }

    except Exception as e:
        logger.error(
            "DIARIZE_SESSION_FAILED",
            session_id=session_id,
            error=str(e),
        )
        raise


def log_audit_event_worker(
    action: str,
    user_id: str,
    resource: str,
    result: str,
    metadata: Dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synchronous audit logging.

    This replaces log_audit_event (Celery task).

    Args:
        action: Action performed (TIMELINE_HASH_VERIFIED, etc.)
        user_id: User/resource identifier
        resource: Resource path
        result: Result status (SUCCESS, FAILED, etc.)
        metadata: Additional context

    Returns:
        dict with event_id and status
    """
    try:
        event_id = write_audit_event(
            action=action,
            user_id=user_id,
            resource=resource,
            result=result,
            metadata=metadata or {},
        )

        logger.info(
            "AUDIT_EVENT_LOGGED",
            event_id=event_id,
            action=action,
        )

        return {"event_id": event_id, "status": "SUCCESS"}

    except Exception as e:
        logger.error("AUDIT_EVENT_FAILED", error=str(e), action=action)
        raise
