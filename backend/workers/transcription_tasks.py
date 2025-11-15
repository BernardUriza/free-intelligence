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

import hashlib
import subprocess
import tempfile
import time
from pathlib import Path

from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType
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
) -> dict:
    """Transcribe audio chunk using Whisper ASR.

    This is a Celery task that:
    1. Ensures TRANSCRIPTION task exists
    2. Reads audio from HDF5 (already stored by service layer)
    3. Converts audio to WAV
    4. Runs Whisper transcription
    5. Writes chunk to HDF5 (tasks/TRANSCRIPTION/chunks/)
    6. Updates task metadata with progress

    Args:
        session_id: Session UUID
        chunk_number: Chunk index

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

        # 5. Whisper transcription
        from backend.services.transcription.whisper import transcribe_audio

        result = transcribe_audio(str(wav_path), language=None, vad_filter=False)

        transcript = result.get("text", "").strip()
        duration = result.get("duration", 0.0)
        language = result.get("language", "unknown")

        # Extract confidence (avg_logprob normalized to 0-1)
        avg_logprob = result.get("avg_logprob", -0.5)
        confidence = max(0.0, min(1.0, 1.0 + (avg_logprob / 1.0)))

        # Calculate audio quality heuristic
        words_count = len(transcript.split())
        words_per_second = words_count / duration if duration > 0 else 0
        audio_quality = max(0.5, min(1.0, words_per_second / 2.5))

        logger.info(
            "WHISPER_DONE",
            session_id=session_id,
            chunk_number=chunk_number,
            transcript_length=len(transcript),
            duration=duration,
            language=language,
            confidence=confidence,
        )

        # 6. Write chunk to HDF5 (tasks/TRANSCRIPTION/chunks/)
        if len(transcript) > 0:
            # Calculate timestamps
            if timestamp_start is None:
                timestamp_start = chunk_number * 3.0
            if timestamp_end is None:
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
            error=str(e),
            latency_ms=latency_ms,
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
