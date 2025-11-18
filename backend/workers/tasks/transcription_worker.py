"""Transcription worker - STT processing."""

from __future__ import annotations

import os
import tempfile
from typing import Any

from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType
from backend.providers.stt import get_stt_provider
from backend.storage.task_repository import (
    batch_update_chunk_datasets,
    get_chunk_audio_bytes,
    get_task_chunks,
    get_task_metadata,
    update_task_metadata,
)
from backend.utils.stt_load_balancer import get_stt_load_balancer
from backend.workers.tasks.base_worker import WorkerResult, measure_time

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
        stt_provider: Provider name (deepgram, azure_whisper). If None, uses adaptive selection.

    Returns:
        WorkerResult with transcript, duration, language, confidence
    """
    # Initialize variables for exception handler type checking
    import time

    balancer = None
    start_time = time.time()  # Track resolution time

    try:
        # Get metadata first (read-only operation)
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {
            "total_chunks": 1,
            "processed_chunks": 0,
        }

        # Read audio BEFORE selecting provider (needed for size-based routing)
        audio_bytes = get_chunk_audio_bytes(session_id, TaskType.TRANSCRIPTION, chunk_number)
        if not audio_bytes:
            raise ValueError(f"No audio for chunk {chunk_number}")

        # Get policy-driven load balancer and select provider based on file size
        balancer = get_stt_load_balancer()
        if stt_provider is None:
            # Pass audio size for policy-based selection
            stt_provider, decision_reason = balancer.select_provider_for_file(
                audio_size_bytes=len(audio_bytes), chunk_number=chunk_number, session_id=session_id
            )
            logger.info(
                "POLICY_BASED_PROVIDER_SELECTED",
                session_id=session_id,
                chunk_number=chunk_number,
                provider=stt_provider,
                decision_reason=decision_reason,
                audio_size_mb=len(audio_bytes) / (1024 * 1024),
            )
        else:
            # Provider was forced by caller
            decision_reason = "forced_by_caller"

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
                "status": TaskStatus.COMPLETED.value
                if processed >= total
                else TaskStatus.IN_PROGRESS.value,
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
        # Record performance failure if we got far enough to select a provider
        try:
            if balancer is not None and stt_provider is not None:
                resolution_time = time.time() - start_time
                balancer.record_performance(
                    provider=stt_provider,
                    resolution_time=resolution_time,
                    retry_attempts=0,
                    failed=True,
                )
        except Exception:
            pass  # Don't let performance tracking errors hide the original error

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

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Get policy configuration for provider
        balancer = get_stt_load_balancer()
        provider_config = balancer.policy.get("stt", {}).get("providers", {}).get(provider_name, {})

        # Try primary provider with policy configuration
        provider = get_stt_provider(provider_name, config=provider_config)
        response = provider.transcribe(tmp_path, language="es")

        # If empty transcript, check policy for fallback
        if not response.text or len(response.text.strip()) == 0:
            # Get policy-driven fallback provider
            fallback_provider = balancer.get_fallback_for_empty(provider_name)

            if not fallback_provider:
                logger.info(
                    "NO_FALLBACK_FOR_EMPTY",
                    provider=provider_name,
                    message="No fallback configured - accepting empty transcript",
                )
                # Return empty result without retry
                return {
                    "transcript": response.text,
                    "language": response.language,
                    "confidence": response.confidence,
                    "duration": response.duration,
                    "segments": response.segments,
                    "provider": response.provider,
                    "retry_attempts": 0,
                }

            retry_attempts = 1  # Fallback attempt

            logger.warning(
                "EMPTY_TRANSCRIPT_TRYING_FALLBACK",
                primary_provider=provider_name,
                fallback_provider=fallback_provider,
                message="Primary provider returned empty transcript - trying policy-based fallback",
            )

            try:
                # Get fallback provider config from policy
                fallback_config = (
                    balancer.policy.get("stt", {}).get("providers", {}).get(fallback_provider, {})
                )
                fallback = get_stt_provider(fallback_provider, config=fallback_config)
                fallback_response = fallback.transcribe(tmp_path, language="es")

                if fallback_response.text and len(fallback_response.text.strip()) > 0:
                    # Fallback succeeded - use its result
                    logger.info(
                        "FALLBACK_TRANSCRIPTION_SUCCESS",
                        fallback_provider=fallback_provider,
                        transcript_length=len(fallback_response.text),
                        message="Fallback provider detected speech where primary failed",
                    )
                    response = fallback_response
                    provider_name = fallback_provider
                else:
                    # Both providers return empty - confirmed silence
                    logger.info(
                        "CONFIRMED_SILENCE",
                        primary_provider=provider_name,
                        fallback_provider=fallback_provider,
                        message="Both providers confirmed: chunk contains no speech",
                    )
            except Exception as fallback_error:
                logger.error(
                    "FALLBACK_TRANSCRIPTION_FAILED",
                    fallback_provider=fallback_provider,
                    error=str(fallback_error),
                    message="Fallback failed - using primary empty result",
                )

        return {
            "transcript": response.text,
            "language": response.language,
            "confidence": response.confidence,
            "duration": response.duration,
            "segments": response.segments,
            "provider": response.provider,
            "retry_attempts": retry_attempts,  # NEW: Track fallback usage
        }
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
