"""Transcription worker - STT processing."""

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


@measure_time
def transcribe_chunk_worker(
    session_id: str,
    chunk_number: int,
    stt_provider: str | None = None,
) -> dict[str, Any]:
    """Synchronous transcription of audio chunk.

    Args:
        session_id: Session identifier
        chunk_number: Chunk index
        stt_provider: Provider name (deepgram). Defaults to deepgram if None.

    Returns:
        WorkerResult with transcript, duration, language, confidence
    """
    import time

    start_time = time.time()

    try:
        # Get metadata first (read-only operation)
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {
            "total_chunks": 1,
            "processed_chunks": 0,
        }

        # Read audio
        audio_bytes = get_chunk_audio_bytes(session_id, TaskType.TRANSCRIPTION, chunk_number)
        if not audio_bytes:
            raise ValueError(f"No audio for chunk {chunk_number}")

        # Single provider: Deepgram (no load balancer needed)
        if stt_provider is None:
            stt_provider = "deepgram"

        logger.info(
            "TRANSCRIBE_CHUNK_START",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=stt_provider,
            audio_size_mb=len(audio_bytes) / (1024 * 1024),
        )

        # Transcribe (returns result + retry_attempts)
        result = _transcribe_audio(audio_bytes, stt_provider)
        resolution_time = time.time() - start_time

        # ATOMIC BATCH UPDATE: Write all chunk fields in one transaction with retry
        # This fixes the HDF5 SWMR race condition where concurrent readers blocked writes
        success = batch_update_chunk_datasets(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            updates={
                "transcript": result.get("transcript", ""),
                "language": result.get("language", "es"),
                "confidence": result.get("confidence", 0.0),
                "duration": result.get("duration", 0.0),
                "provider": stt_provider,
                "resolution_time_seconds": resolution_time,
                "retry_attempts": result.get("retry_attempts", 0),
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
                "status": (
                    TaskStatus.COMPLETED.name.lower()
                    if processed >= total
                    else TaskStatus.IN_PROGRESS.name.lower()
                ),
                "estimated_seconds_remaining": estimated_seconds_remaining,
                "provider": stt_provider,
            },
        )

        # Record performance metrics for adaptive load balancing
        balancer.record_performance(
            provider=stt_provider,
            resolution_time=resolution_time,
            retry_attempts=result.get("retry_attempts", 0),
            failed=False,
        )

        logger.info(
            "TRANSCRIBE_CHUNK_SUCCESS",
            session_id=session_id,
            chunk_number=chunk_number,
            processed=f"{processed}/{total}",
            provider=stt_provider,
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
    """Transcribe audio bytes using STT provider with fallback.

    Strategy:
    1. Try primary provider (Deepgram)
    2. If transcript is empty (0 chars), try fallback provider (Azure Whisper)
    3. If both return empty, it's confirmed silence

    Args:
        audio_bytes: Audio data
        provider_name: Provider to use

    Returns:
        Transcription result with retry_attempts (0 = no fallback, 1 = fallback used)
    """
    retry_attempts = 0  # Track if fallback was used

    # Detect format from magic bytes
    # WebM starts with 0x1A45DFA3 (EBML header)
    # MP3 starts with 0xFFFA or 0xFFFB or ID3
    # WAV starts with RIFF
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
        # WebM/Matroska check: EBML header 0x1A45DFA3
        elif audio_bytes[0:4] == bytes([0x1A, 0x45, 0xDF, 0xA3]):
            ext = ".webm"

    logger.info("AUDIO_FORMAT_DETECTED", extension=ext)

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Single provider: Deepgram (no fallback chain needed)
        provider = get_stt_provider(provider_name)
        response = provider.transcribe(tmp_path, language="es")

        # Log empty transcripts but accept them (confirmed silence)
        if not response.text or len(response.text.strip()) == 0:
            logger.info(
                "EMPTY_TRANSCRIPT",
                provider=provider_name,
                message="Provider returned empty transcript - likely silence",
            )

        return {
            "transcript": response.text,
            "language": response.language,
            "confidence": response.confidence,
            "duration": response.duration,
            "segments": response.segments,
            "provider": response.provider,
            "retry_attempts": 0,
        }
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
