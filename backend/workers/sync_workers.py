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
            "TRANSCRIBE_CHUNK_WORKER_START",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=stt_provider,
            timestamp=start_time,
        )

        # Step 1: Ensure TRANSCRIPTION task exists
        logger.debug(
            "ENSURING_TASK_EXISTS",
            session_id=session_id,
            task_type="TRANSCRIPTION",
        )
        ensure_task_exists(session_id, TaskType.TRANSCRIPTION)
        logger.debug(
            "TASK_EXISTS_OK",
            session_id=session_id,
        )

        # Step 2: Get current task metadata
        logger.debug(
            "FETCHING_TASK_METADATA",
            session_id=session_id,
            chunk_number=chunk_number,
        )
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)
        if not task_metadata:
            task_metadata = {
                "total_chunks": 1,
                "processed_chunks": 0,
            }
            logger.warning(
                "NO_TASK_METADATA_FOUND",
                session_id=session_id,
                using_default=True,
            )
        logger.debug(
            "TASK_METADATA_FETCHED",
            session_id=session_id,
            total_chunks=task_metadata.get("total_chunks"),
            processed_chunks=task_metadata.get("processed_chunks"),
        )

        # Step 3: Read audio from HDF5 and transcribe using Whisper
        logger.info(
            "READING_AUDIO_FROM_HDF5",
            session_id=session_id,
            chunk_number=chunk_number,
        )

        from backend.storage.task_repository import get_chunk_audio_bytes

        audio_bytes = get_chunk_audio_bytes(session_id, TaskType.TRANSCRIPTION, chunk_number)
        logger.debug(
            "AUDIO_READ_FROM_HDF5",
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=len(audio_bytes) if audio_bytes else 0,
        )

        if not audio_bytes:
            raise ValueError(f"No audio data for chunk {chunk_number} in session {session_id}")

        # Transcribe using Whisper (or other provider)
        logger.info(
            "STARTING_TRANSCRIPTION",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=stt_provider,
        )

        if stt_provider == "faster_whisper":
            from backend.services.transcription.whisper import transcribe_audio

            result = transcribe_audio(audio_bytes)
        else:
            logger.warning(
                "UNSUPPORTED_STT_PROVIDER",
                provider=stt_provider,
                falling_back_to="faster_whisper",
            )
            from backend.services.transcription.whisper import transcribe_audio

            result = transcribe_audio(audio_bytes)

        logger.info(
            "TRANSCRIPTION_COMPLETED",
            session_id=session_id,
            chunk_number=chunk_number,
            has_transcript=bool(result and "transcript" in result),
            transcript_length=len(result.get("transcript", "")) if result else 0,
        )

        # Step 4: Update task metadata with progress
        logger.debug(
            "UPDATING_TASK_METADATA",
            session_id=session_id,
            chunk_number=chunk_number,
        )
        total_chunks = task_metadata.get("total_chunks", 1)
        processed = task_metadata.get("processed_chunks", 0) + 1
        progress = int((processed / total_chunks) * 100)

        metadata_update = {
            "processed_chunks": processed,
            "progress_percent": progress,
            "last_chunk": chunk_number,
            "status": TaskStatus.IN_PROGRESS.value
            if processed < total_chunks
            else TaskStatus.COMPLETED.value,
        }
        update_task_metadata(
            session_id,
            TaskType.TRANSCRIPTION,
            metadata_update,
        )
        logger.info(
            "TASK_METADATA_UPDATED",
            session_id=session_id,
            chunk_number=chunk_number,
            processed_chunks=processed,
            total_chunks=total_chunks,
            progress_percent=progress,
            new_status=metadata_update["status"],
        )

        elapsed = time.time() - start_time
        logger.info(
            "TRANSCRIBE_CHUNK_WORKER_SUCCESS",
            session_id=session_id,
            chunk_number=chunk_number,
            duration_seconds=elapsed,
            processed_chunks=processed,
            total_chunks=total_chunks,
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
            "TRANSCRIBE_CHUNK_WORKER_FAILED",
            session_id=session_id,
            chunk_number=chunk_number,
            error=str(e),
            error_type=type(e).__name__,
            duration_seconds=time.time() - start_time,
            exc_info=True,
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
