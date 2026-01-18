"""Transcription worker - STT processing using Azure Whisper."""

from __future__ import annotations

import tempfile
from typing import Any

import os
from backend.models.task_type import TaskStatus, TaskType
from backend.providers.stt import get_stt_provider
from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_storage.infrastructure.hdf5.task_repository import (
    batch_update_chunk_datasets,
    get_chunk_audio_bytes,
    get_task_chunks,
    get_task_metadata,
    update_task_metadata,
)
from backend.src.fi_workers.tasks.base_worker import WorkerResult, measure_time

logger = get_logger(__name__)

# Default STT provider (single provider architecture)
DEFAULT_STT_PROVIDER = "azure_whisper"


@measure_time
def transcribe_chunk_worker(
    session_id: str,
    chunk_number: int,
    stt_provider: str | None = None,
) -> dict[str, Any]:
    """Synchronous transcription of audio chunk using Azure Whisper.

    Args:
        session_id: Session identifier
        chunk_number: Chunk index
        stt_provider: Provider name (default: azure_whisper)

    Returns:
        WorkerResult with transcript, duration, language, confidence
    """
    import time

    start_time = time.time()
    provider = stt_provider or DEFAULT_STT_PROVIDER

    try:
        # Get metadata first (read-only operation)
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {
            "total_chunks": 1,
            "processed_chunks": 0,
        }

        # Read audio bytes
        audio_bytes = get_chunk_audio_bytes(session_id, TaskType.TRANSCRIPTION, chunk_number)
        if not audio_bytes:
            raise ValueError(f"No audio for chunk {chunk_number}")

        logger.info(
            "TRANSCRIBE_CHUNK_START",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=provider,
            audio_size_mb=len(audio_bytes) / (1024 * 1024),
        )

        # Transcribe audio
        result = _transcribe_audio(audio_bytes, provider)
        resolution_time = time.time() - start_time

        # ATOMIC BATCH UPDATE: Write all chunk fields in one transaction with retry
        success = batch_update_chunk_datasets(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            updates={
                "transcript": result.get("transcript", ""),
                "language": result.get("language", "es"),
                "confidence": result.get("confidence", 0.0),
                "duration": result.get("duration", 0.0),
                "provider": provider,
                "resolution_time_seconds": resolution_time,
            },
            max_retries=5,
            initial_backoff=0.1,
        )

        if not success:
            # Batch update failed after retries - CRITICAL ERROR
            logger.error(
                "BATCH_UPDATE_FAILED_AFTER_RETRIES",
                session_id=session_id,
                chunk_number=chunk_number,
                message="Transcription succeeded but failed to save to HDF5 - data loss!",
            )
            raise RuntimeError(
                f"Failed to save transcription results for chunk {chunk_number} after retries"
            )

        # Update metadata
        actual_chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)
        total = max(len(actual_chunks), 1)
        processed = task_metadata.get("processed_chunks", 0) + 1
        progress = int((processed / total) * 100)

        # Estimate time remaining (Azure Whisper: ~15s per chunk)
        remaining_chunks = total - processed
        avg_time_per_chunk = 15.0
        estimated_seconds_remaining = int(remaining_chunks * avg_time_per_chunk)

        update_task_metadata(
            session_id,
            TaskType.TRANSCRIPTION,
            {
                "processed_chunks": processed,
                "progress_percent": progress,
                "last_chunk": chunk_number,
                "status": (
                    TaskStatus.COMPLETED.name.lower()
                    if processed >= total
                    else TaskStatus.IN_PROGRESS.name.lower()
                ),
                "estimated_seconds_remaining": estimated_seconds_remaining,
                "provider": provider,
            },
        )

        logger.info(
            "TRANSCRIBE_CHUNK_SUCCESS",
            session_id=session_id,
            chunk_number=chunk_number,
            processed=f"{processed}/{total}",
            provider=provider,
            duration_seconds=result.get("duration", 0.0),
            resolution_time=resolution_time,
        )

        return WorkerResult(
            session_id=session_id,
            result=result,
            chunk_number=chunk_number,
        ).to_dict()

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
    """Transcribe audio bytes using Azure Whisper.

    Args:
        audio_bytes: Audio data
        provider_name: Provider to use (default: azure_whisper)

    Returns:
        Transcription result dict
    """
    # Detect format from magic bytes
    ext = ".webm"  # default
    magic_bytes = audio_bytes[:8] if len(audio_bytes) > 8 else audio_bytes
    logger.info(
        "AUDIO_FORMAT_DETECTION",
        magic_bytes_hex=magic_bytes.hex(),
        audio_size=len(audio_bytes),
    )

    if len(audio_bytes) > 4:
        if audio_bytes[:4] == b"RIFF":
            ext = ".wav"
        elif audio_bytes[:3] == b"ID3" or (
            audio_bytes[0] == 0xFF and audio_bytes[1] in (0xFA, 0xFB, 0xF3, 0xF2)
        ):
            ext = ".mp3"
        elif audio_bytes[:4] == b"OggS":
            ext = ".ogg"
        elif audio_bytes[:4] == b"fLaC":
            ext = ".flac"
        elif audio_bytes[0:4] == bytes([0x1A, 0x45, 0xDF, 0xA3]):
            ext = ".webm"

    logger.info("AUDIO_FORMAT_DETECTED", extension=ext)

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Get STT provider (single provider architecture - Azure Whisper)
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
