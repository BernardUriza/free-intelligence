"""Celery tasks for audio transcription.

WORKER layer:
- Processes audio chunks with Whisper ASR
- Dual write to HDF5 (production + ml_ready)
- Updates TranscriptionJob with results

Architecture:
  PUBLIC → INTERNAL → WORKER (this file)

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Architecture unification
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from backend.logger import get_logger
from backend.models import JobType, TranscriptionJob
from backend.repositories import job_repository
from backend.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="transcribe_chunk", bind=True, max_retries=3)
def transcribe_chunk_task(
    self,
    session_id: str,
    chunk_number: int,
    audio_bytes: bytes,
    timestamp_start: Optional[float] = None,
    timestamp_end: Optional[float] = None,
) -> dict:
    """Transcribe audio chunk using Whisper ASR.

    This is a Celery task that:
    1. Loads TranscriptionJob from HDF5
    2. Marks chunk as "processing"
    3. Converts audio to WAV
    4. Runs Whisper transcription
    5. Dual write to HDF5 (production + ml_ready)
    6. Marks chunk as "completed" with results
    7. Updates job progress

    Args:
        session_id: Session UUID
        chunk_number: Chunk index
        audio_bytes: Raw audio bytes (WebM/WAV/MP3)
        timestamp_start: Optional chunk start time
        timestamp_end: Optional chunk end time

    Returns:
        dict with transcript, duration, language, etc.

    Raises:
        Retry on transient errors
    """
    start_time = time.time()

    try:
        logger.info(
            "CELERY_CHUNK_STARTED",
            task_id=self.request.id,
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=len(audio_bytes),
        )

        # 1. Load job from HDF5
        job = job_repository.load(
            job_id=session_id,
            session_id=session_id,
            job_type=JobType.TRANSCRIPTION,
            job_class=TranscriptionJob,
        )

        if not job:
            error_msg = f"TranscriptionJob not found for session {session_id}"
            logger.error("JOB_NOT_FOUND", session_id=session_id)
            raise ValueError(error_msg)

        # 2. Mark chunk as processing
        chunk = job.get_chunk(chunk_number)
        if chunk:
            chunk.status = "processing"
            job_repository.save(job)

        # 3. Save audio to temp file
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

        # 6. Dual write to HDF5 (if transcript not empty)
        if len(transcript) > 0:
            from backend.storage.session_chunks_schema import append_chunk_to_session

            # Calculate timestamps
            if timestamp_start is None:
                timestamp_start = chunk_number * 3.0
            if timestamp_end is None:
                timestamp_end = timestamp_start + duration

            created_at = datetime.now(UTC).isoformat()

            append_chunk_to_session(
                session_id=session_id,
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
                "HDF5_DUAL_WRITE_DONE",
                session_id=session_id,
                chunk_number=chunk_number,
            )

            # 7. Mark chunk completed in job
            job = job_repository.load(
                job_id=session_id,
                session_id=session_id,
                job_type=JobType.TRANSCRIPTION,
                job_class=TranscriptionJob,
            )

            if job:
                job.mark_chunk_completed(
                    chunk_number=chunk_number,
                    transcript=transcript,
                    duration=duration,
                    language=language,
                    audio_hash=audio_hash,
                    confidence=confidence,
                    audio_quality=audio_quality,
                    timestamp_start=timestamp_start,
                    timestamp_end=timestamp_end,
                    created_at=created_at,
                )

                # Update job status to in_progress
                if job.status.value == "pending":
                    job.start()

                job_repository.save(job)

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

        # Mark chunk as failed in job
        try:
            job = job_repository.load(
                job_id=session_id,
                session_id=session_id,
                job_type=JobType.TRANSCRIPTION,
                job_class=TranscriptionJob,
            )
            if job:
                job.mark_chunk_failed(chunk_number, str(e))
                job_repository.save(job)
        except Exception as save_error:
            logger.error("FAILED_TO_MARK_CHUNK_FAILED", error=str(save_error))

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
