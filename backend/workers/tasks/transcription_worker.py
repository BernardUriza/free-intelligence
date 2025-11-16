"""Transcription worker - STT processing."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType
from backend.providers.stt import get_stt_provider
from backend.storage.task_repository import (
    get_chunk_audio_bytes,
    get_task_chunks,
    get_task_metadata,
    update_chunk_dataset,
    update_task_metadata,
)
from backend.workers.tasks.base_worker import WorkerResult, measure_time

logger = get_logger(__name__)


@measure_time
def transcribe_chunk_worker(
    session_id: str,
    chunk_number: int,
    stt_provider: str = "deepgram",
) -> dict[str, Any]:
    """Synchronous transcription of audio chunk.

    Args:
        session_id: Session identifier
        chunk_number: Chunk index
        stt_provider: Provider name (deepgram, azure_whisper)

    Returns:
        WorkerResult with transcript, duration, language, confidence
    """
    try:
        logger.info(
            "TRANSCRIBE_CHUNK_START",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=stt_provider,
        )

        # DON'T ensure_task_exists here - it causes HDF5 race condition
        # Task was already created by Service layer before worker dispatch

        # Get metadata (read-only operation)
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {
            "total_chunks": 1,
            "processed_chunks": 0,
        }

        # Read audio
        audio_bytes = get_chunk_audio_bytes(session_id, TaskType.TRANSCRIPTION, chunk_number)
        if not audio_bytes:
            raise ValueError(f"No audio for chunk {chunk_number}")

        # Transcribe
        result = _transcribe_audio(audio_bytes, stt_provider)

        # Save transcript
        update_chunk_dataset(
            session_id,
            TaskType.TRANSCRIPTION,
            chunk_number,
            "transcript",
            result.get("transcript", ""),
        )
        update_chunk_dataset(
            session_id,
            TaskType.TRANSCRIPTION,
            chunk_number,
            "language",
            result.get("language", "es"),
        )
        update_chunk_dataset(
            session_id,
            TaskType.TRANSCRIPTION,
            chunk_number,
            "confidence",
            result.get("confidence", 0.0),
        )
        update_chunk_dataset(
            session_id,
            TaskType.TRANSCRIPTION,
            chunk_number,
            "duration",
            result.get("duration", 0.0),
        )
        update_chunk_dataset(
            session_id,
            TaskType.TRANSCRIPTION,
            chunk_number,
            "provider",
            stt_provider,
        )

        # Update metadata
        actual_chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)
        total = max(len(actual_chunks), 1)
        processed = task_metadata.get("processed_chunks", 0) + 1
        progress = int((processed / total) * 100)

        # Estimate time remaining based on provider
        remaining_chunks = total - processed
        avg_time_per_chunk = 2.0 if stt_provider == "deepgram" else 15.0  # Deepgram: 2s, Azure: 15s
        estimated_seconds_remaining = int(remaining_chunks * avg_time_per_chunk)

        update_task_metadata(
            session_id,
            TaskType.TRANSCRIPTION,
            {
                "processed_chunks": processed,
                "progress_percent": progress,
                "last_chunk": chunk_number,
                "status": TaskStatus.COMPLETED.value
                if processed >= total
                else TaskStatus.IN_PROGRESS.value,
                "estimated_seconds_remaining": estimated_seconds_remaining,
                "provider": stt_provider,
            },
        )

        logger.info(
            "TRANSCRIBE_CHUNK_SUCCESS",
            session_id=session_id,
            chunk_number=chunk_number,
            processed=f"{processed}/{total}",
            provider=stt_provider,
            duration_seconds=result.get("duration", 0.0),
        )

        return WorkerResult(
            session_id=session_id,
            result=result,
            chunk_number=chunk_number,
        )

    except Exception as e:
        logger.error(
            "TRANSCRIBE_CHUNK_FAILED",
            session_id=session_id,
            chunk_number=chunk_number,
            error=str(e),
            exc_info=True,
        )
        raise


def _transcribe_audio(audio_bytes: bytes, provider_name: str) -> dict[str, Any]:
    """Transcribe audio bytes using STT provider.

    Args:
        audio_bytes: Audio data
        provider_name: Provider to use

    Returns:
        Transcription result
    """
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        provider = get_stt_provider(provider_name)
        response = provider.transcribe(tmp_path, language="es")

        return {
            "transcript": response.text,
            "language": response.language,
            "confidence": response.confidence,
            "duration": response.duration,
            "segments": response.segments,
            "provider": response.provider,
        }
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
