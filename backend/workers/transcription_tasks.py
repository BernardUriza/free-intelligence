"""Celery tasks for audio transcription.

WORKER layer:
- Processes audio chunks with Whisper ASR
- Writes to task-based HDF5 (tasks/TRANSCRIPTION/)
- Updates task metadata with progress

Architecture:
  PUBLIC → INTERNAL → WORKER (this file)

Migration notes:
  - NOW USES: backend.storage.task_repository (NEW task-based API)
  - DEPRECATED: backend.repositories.job_repository
  - DEPRECATED: backend.storage.session_chunks_schema

Author: Bernard Uriza Orozco
Created: 2025-11-14
Updated: 2025-11-14 (task-based refactor)
Card: Architecture refactor - task-based HDF5
"""

from __future__ import annotations

import contextlib
import hashlib
import subprocess
import tempfile
import time
from pathlib import Path

from backend.logger import get_logger
from backend.models.task_type import CHUNK_DURATION_SECONDS, TaskStatus, TaskType
from backend.storage.task_repository import (
    add_audio_to_chunk,
    append_chunk_to_task,
    ensure_task_exists,
    get_task_metadata,
    update_task_metadata,
)
from backend.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="transcribe_chunk", bind=True, max_retries=3)
def transcribe_chunk_task(
    self,
    session_id: str,
    chunk_number: int,
    stt_provider: str = "faster_whisper",
) -> dict:
    """Transcribe audio chunk using configurable STT provider.

    This is a Celery task that:
    1. Ensures TRANSCRIPTION task exists
    2. Reads audio from HDF5 (already stored by service layer)
    3. Converts audio to WAV (if needed for local providers)
    4. Runs transcription via selected STT provider (Azure, Deepgram, or Faster-Whisper)
    5. Writes chunk to HDF5 (tasks/TRANSCRIPTION/chunks/)
    6. Updates task metadata with progress

    Args:
        session_id: Session UUID
        chunk_number: Chunk index
        stt_provider: Provider name ("azure_whisper", "deepgram", "faster_whisper")

    Returns:
        dict with transcript, duration, language, etc.

    Raises:
        Retry on transient errors

    Note:
        Audio is already in HDF5, stored by service layer.
        This avoids serializing large binary blobs through Redis.
    """
    start_time = time.time()

    try:
        logger.info(
            "CELERY_CHUNK_STARTED",
            task_id=self.request.id,
            session_id=session_id,
            chunk_number=chunk_number,
        )

        # 1. Ensure TRANSCRIPTION task exists
        ensure_task_exists(session_id, TaskType.TRANSCRIPTION, allow_existing=True)

        # 2. Get current task metadata
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)
        if not task_metadata:
            task_metadata = {
                "job_id": self.request.id,
                "status": TaskStatus.PENDING.value,
                "progress_percent": 0,
                "total_chunks": 0,
                "processed_chunks": 0,
            }

        # 3. Read audio from HDF5 (stored by service layer)
        from backend.storage.task_repository import get_chunk_audio_bytes

        audio_bytes = get_chunk_audio_bytes(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
        )
        if not audio_bytes:
            logger.error(
                "CHUNK_AUDIO_NOT_FOUND",
                session_id=session_id,
                chunk_number=chunk_number,
            )
            raise ValueError(f"Audio for chunk {chunk_number} not found in HDF5")

        audio_hash = hashlib.sha256(audio_bytes).hexdigest()[:16]
        temp_dir = Path(tempfile.gettempdir()) / "fi_chunks"
        temp_dir.mkdir(exist_ok=True)

        audio_path = temp_dir / f"{session_id}_{chunk_number}.webm"
        audio_path.write_bytes(audio_bytes)

        # 4. Convert to WAV for Whisper
        wav_path = temp_dir / f"{session_id}_{chunk_number}.wav"
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav_path),
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True, timeout=30, capture_output=True)
        except subprocess.TimeoutExpired:
            logger.error("FFMPEG_TIMEOUT", session_id=session_id, chunk_number=chunk_number)
            raise
        except subprocess.CalledProcessError as e:
            logger.error(
                "FFMPEG_FAILED",
                session_id=session_id,
                chunk_number=chunk_number,
                stderr=e.stderr.decode() if e.stderr else None,
            )
            raise

        logger.info(
            "WAV_CONVERTED",
            session_id=session_id,
            chunk_number=chunk_number,
            wav_size=wav_path.stat().st_size,
        )

        # 5. STT Transcription via selected provider
        from backend.providers.stt import get_stt_provider

        logger.info(
            "STT_PROVIDER_SELECTED",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=stt_provider,
        )

        try:
            provider = get_stt_provider(stt_provider)
        except ValueError as e:
            logger.error(
                "STT_PROVIDER_INVALID",
                session_id=session_id,
                provider=stt_provider,
                error=str(e),
            )
            # Fallback to faster_whisper
            stt_provider = "faster_whisper"
            provider = get_stt_provider(stt_provider)

        # Use WAV path for local provider, original audio for cloud providers
        if stt_provider == "faster_whisper":
            audio_input_path = wav_path
        else:
            # Cloud providers (Azure, Deepgram) work with webm/mp3
            audio_input_path = audio_path

        logger.info(
            "STT_TRANSCRIPTION_STARTING",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=stt_provider,
            audio_path=str(audio_input_path),
        )

        try:
            stt_response = provider.transcribe(str(audio_input_path), language=None)

            transcript = stt_response.text.strip()
            duration = stt_response.duration
            language = stt_response.language
            confidence = stt_response.confidence

            logger.info(
                "STT_TRANSCRIPTION_SUCCESS",
                session_id=session_id,
                chunk_number=chunk_number,
            )

            logger.info(
                "STT_TRANSCRIPTION_DONE",
                session_id=session_id,
                chunk_number=chunk_number,
                provider=stt_provider,
                transcript_length=len(transcript),
                duration=duration,
                language=language,
                confidence=confidence,
                latency_ms=stt_response.latency_ms,
            )
        except Exception as e:
            logger.error(
                "STT_TRANSCRIPTION_CALL_FAILED",
                session_id=session_id,
                chunk_number=chunk_number,
                provider=stt_provider,
                error_type=type(e).__name__,
                error_message=str(e),
                audio_path=str(audio_input_path),
                exc_info=True,
            )
            raise

        # Calculate audio quality heuristic
        words_count = len(transcript.split())
        words_per_second = words_count / duration if duration > 0 else 0
        audio_quality = max(0.5, min(1.0, words_per_second / 2.5))

        # 6. Write chunk to HDF5 (tasks/TRANSCRIPTION/chunks/)
        if len(transcript) > 0:
            # Calculate timestamps (worker generates these)
            # Using CHUNK_DURATION_SECONDS from config as single source of truth
            timestamp_start = chunk_number * CHUNK_DURATION_SECONDS
            timestamp_end = timestamp_start + duration

            append_chunk_to_task(
                session_id=session_id,
                task_type=TaskType.TRANSCRIPTION,
                chunk_idx=chunk_number,
                transcript=transcript,
                audio_hash=audio_hash,
                duration=duration,
                language=language,
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                confidence=confidence,
                audio_quality=audio_quality,
            )

            logger.info(
                "HDF5_CHUNK_WRITTEN",
                session_id=session_id,
                chunk_number=chunk_number,
                path=f"/sessions/{session_id}/tasks/TRANSCRIPTION/chunks/chunk_{chunk_number}",
            )

            # 7. Save audio file alongside transcript (NEW: audio + transcript colocated)
            try:
                # Determine audio extension from original file
                audio_ext = audio_path.suffix if audio_path.suffix else ".webm"
                audio_filename = f"audio{audio_ext}"

                add_audio_to_chunk(
                    session_id=session_id,
                    chunk_idx=chunk_number,
                    audio_bytes=audio_bytes,
                    filename=audio_filename,
                    task_type=TaskType.TRANSCRIPTION,
                )

                logger.info(
                    "CHUNK_AUDIO_SAVED",
                    session_id=session_id,
                    chunk_number=chunk_number,
                    filename=audio_filename,
                    size_bytes=len(audio_bytes),
                )
            except Exception as audio_err:
                # Don't fail the entire task if audio save fails
                logger.error(
                    "CHUNK_AUDIO_SAVE_FAILED",
                    session_id=session_id,
                    chunk_number=chunk_number,
                    error=str(audio_err),
                )

            # 8. Update task metadata with progress
            task_metadata["status"] = TaskStatus.IN_PROGRESS.value
            task_metadata["processed_chunks"] = task_metadata.get("processed_chunks", 0) + 1

            # Update total_chunks if this chunk is higher
            if chunk_number + 1 > task_metadata.get("total_chunks", 0):
                task_metadata["total_chunks"] = chunk_number + 1

            # Calculate progress
            total = task_metadata["total_chunks"]
            processed = task_metadata["processed_chunks"]
            if total > 0:
                task_metadata["progress_percent"] = int((processed / total) * 100)

            update_task_metadata(session_id, TaskType.TRANSCRIPTION, task_metadata)

            logger.info(
                "TASK_METADATA_UPDATED",
                session_id=session_id,
                progress=f"{processed}/{total} ({task_metadata['progress_percent']}%)",
            )

        # Cleanup temp files
        audio_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "CELERY_CHUNK_COMPLETED",
            task_id=self.request.id,
            session_id=session_id,
            chunk_number=chunk_number,
            latency_ms=latency_ms,
        )

        return {
            "session_id": session_id,
            "chunk_number": chunk_number,
            "transcript": transcript,
            "duration": duration,
            "language": language,
            "confidence": confidence,
            "audio_quality": audio_quality,
            "latency_ms": latency_ms,
        }

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "CELERY_CHUNK_FAILED",
            task_id=self.request.id,
            session_id=session_id,
            chunk_number=chunk_number,
            error_type=type(e).__name__,
            error_message=str(e),
            latency_ms=latency_ms,
            exc_info=True,
        )

        # Update task metadata with error
        try:
            task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}
            task_metadata["status"] = TaskStatus.FAILED.value
            task_metadata["error_message"] = str(e)
            update_task_metadata(session_id, TaskType.TRANSCRIPTION, task_metadata)
        except Exception as meta_error:
            logger.error("FAILED_TO_UPDATE_ERROR_METADATA", error=str(meta_error))

        # Retry on transient errors
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            logger.info(
                "CELERY_TASK_RETRY",
                task_id=self.request.id,
                retry_count=self.request.retries,
            )
            raise self.retry(exc=e, countdown=5 * (2**self.request.retries))

        # Don't retry on permanent errors
        raise


@celery_app.task(name="transcribe_full_audio", bind=True, max_retries=3)
def transcribe_full_audio_task(
    self,
    session_id: str,
    stt_provider: str = "faster_whisper",
) -> dict:
    """Transcribe full concatenated audio using configurable STT provider.

    Called after checkpoint pause. Transcribes the complete audio file
    (full_audio.webm) that has been accumulated since session start.
    Used for context-aware diarization and SOAP generation.

    Args:
        session_id: Session UUID
        stt_provider: Provider name (default "faster_whisper")

    Returns:
        dict with transcript, confidence, duration, language

    Raises:
        Retry on transient errors
    """
    start_time = time.time()

    try:
        logger.info(
            "FULL_AUDIO_TRANSCRIPTION_STARTED",
            task_id=self.request.id,
            session_id=session_id,
            provider=stt_provider,
        )

        # 1. Read full_audio.webm from HDF5
        import h5py

        from backend.storage.task_repository import CORPUS_PATH, get_task_metadata

        audio_bytes = None
        with h5py.File(CORPUS_PATH, "r") as f:
            full_audio_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm"
            if full_audio_path in f:
                audio_data = f[full_audio_path][()]
                audio_bytes = bytes(audio_data) if hasattr(audio_data, "__iter__") else audio_data

        if not audio_bytes:
            logger.error(
                "FULL_AUDIO_NOT_FOUND",
                session_id=session_id,
            )
            raise ValueError(f"Full audio not found for session {session_id}")

        audio_hash = hashlib.sha256(audio_bytes).hexdigest()[:16]
        logger.info(
            "FULL_AUDIO_READ_FROM_HDF5",
            session_id=session_id,
            audio_size=len(audio_bytes),
            audio_hash=audio_hash,
        )

        # 2. Get STT provider
        from backend.providers.stt import get_stt_provider

        try:
            provider = get_stt_provider(stt_provider)
        except ValueError as e:
            logger.error(
                "STT_PROVIDER_INVALID",
                session_id=session_id,
                provider=stt_provider,
                error=str(e),
            )
            # Fallback to faster_whisper
            stt_provider = "faster_whisper"
            provider = get_stt_provider(stt_provider)

        # 3. Write audio to temp file for provider
        temp_dir = Path(tempfile.gettempdir()) / "fi_full_audio"
        temp_dir.mkdir(exist_ok=True)
        temp_audio_path = temp_dir / f"{session_id}_full_audio.webm"
        temp_audio_path.write_bytes(audio_bytes)

        try:
            stt_response = provider.transcribe(str(temp_audio_path), language=None)

            transcript = stt_response.text.strip()
            duration = stt_response.duration
            language = stt_response.language
            confidence = stt_response.confidence

            logger.info(
                "FULL_AUDIO_TRANSCRIPTION_DONE",
                session_id=session_id,
                provider=stt_provider,
                transcript_length=len(transcript),
                duration=duration,
                language=language,
                confidence=confidence,
                latency_ms=stt_response.latency_ms,
            )
        except Exception as e:
            logger.error(
                "STT_TRANSCRIPTION_FAILED",
                session_id=session_id,
                provider=stt_provider,
                error=str(e),
            )
            raise
        finally:
            # Clean up temp file
            with contextlib.suppress(Exception):
                temp_audio_path.unlink()

        # 4. Save full_transcription to HDF5
        from backend.storage.task_repository import add_full_transcription

        add_full_transcription(
            session_id=session_id,
            transcript=transcript,
            confidence=confidence,
            duration=duration,
            language=language,
            audio_hash=audio_hash,
            task_type=TaskType.TRANSCRIPTION,
        )

        logger.info(
            "FULL_TRANSCRIPTION_SAVED",
            session_id=session_id,
            transcript_length=len(transcript),
            confidence=confidence,
        )

        # 5. Update task metadata

        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}
        task_metadata["full_transcription_completed_at"] = time.time()
        task_metadata["full_transcription_confidence"] = confidence
        task_metadata["full_transcription_provider"] = stt_provider
        update_task_metadata(session_id, TaskType.TRANSCRIPTION, task_metadata)

        elapsed = time.time() - start_time

        logger.info(
            "FULL_AUDIO_TRANSCRIPTION_COMPLETED",
            task_id=self.request.id,
            session_id=session_id,
            elapsed_seconds=round(elapsed, 2),
            transcript_length=len(transcript),
        )

        return {
            "session_id": session_id,
            "transcript": transcript,
            "confidence": confidence,
            "duration": duration,
            "language": language,
            "elapsed_seconds": elapsed,
        }

    except Exception as e:
        logger.error(
            "FULL_AUDIO_TRANSCRIPTION_FAILED",
            task_id=self.request.id,
            session_id=session_id,
            error=str(e),
            retry_count=self.request.retries,
        )

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 2**self.request.retries  # 2, 4, 8 seconds
            raise self.retry(exc=e, countdown=retry_delay)
        else:
            logger.error(
                "FULL_AUDIO_TRANSCRIPTION_FINAL_FAILURE",
                session_id=session_id,
            )
            raise
