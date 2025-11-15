"""Deepgram Transcription Worker Task.

Celery task that:
1. Reads audio chunk from HDF5
2. Sends to Deepgram API
3. Updates HDF5 with transcript + metadata
4. Tracks progress in task metadata

Much faster than local Whisper - no GPU needed.

Usage:
    from backend.workers.deepgram_transcription_task import deepgram_transcribe_chunk
    task = deepgram_transcribe_chunk.delay(session_id="...", chunk_number=0)
"""

from __future__ import annotations

import hashlib
import time
from datetime import UTC

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import (
    get_chunk_audio_bytes,
    get_task_metadata,
    update_chunk_dataset,
    update_task_metadata,
)
from backend.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="deepgram_transcribe_chunk", bind=True, max_retries=3)
def deepgram_transcribe_chunk(
    self,
    session_id: str,
    chunk_number: int,
    language: str = "es",
) -> dict:
    """Transcribe chunk using Deepgram API.

    This is a Celery task that:
    1. Reads audio from HDF5 (stored by service layer)
    2. Converts audio to WAV if needed
    3. Sends to Deepgram API
    4. Writes transcript to HDF5
    5. Updates task metadata with progress

    Args:
        session_id: Session UUID
        chunk_number: Chunk index (0, 1, 2, ...)
        language: Language code (default "es")

    Returns:
        dict with transcript, confidence, duration, etc.

    Raises:
        Retry on transient errors
    """
    start_time = time.time()

    try:
        logger.info(
            "DEEPGRAM_CHUNK_STARTED",
            task_id=self.request.id,
            session_id=session_id,
            chunk_number=chunk_number,
            language=language,
        )

        # 1. Read audio from HDF5 (stored by service layer)
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
        logger.info(
            "AUDIO_READ_FROM_HDF5",
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=len(audio_bytes),
            audio_hash=audio_hash,
        )

        # 2. Audio ready to send
        audio_to_send = audio_bytes

        # 3. Call Deepgram API

        import os

        deepgram_api_key = os.environ.get("DEEPGRAM_API_KEY")
        if not deepgram_api_key:
            logger.error(
                "DEEPGRAM_API_KEY_MISSING",
                session_id=session_id,
            )
            raise ValueError("DEEPGRAM_API_KEY environment variable not set")

        # Call Deepgram REST API directly (sync)
        result = _transcribe_with_deepgram_sync(
            audio_bytes=audio_to_send,
            language=language,
            api_key=deepgram_api_key,
            session_id=session_id,
            chunk_number=chunk_number,
        )

        # 4. Update HDF5 with transcript and metadata
        from datetime import datetime

        update_chunk_dataset(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            field="transcript",
            value=result["transcript"],
        )
        update_chunk_dataset(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            field="audio_hash",
            value=audio_hash,
        )
        update_chunk_dataset(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            field="confidence",
            value=result["confidence"],
        )
        update_chunk_dataset(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            field="duration",
            value=result["duration"],
        )
        update_chunk_dataset(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            field="language",
            value=result["language"],
        )

        logger.info(
            "CHUNK_TRANSCRIPT_UPDATED",
            session_id=session_id,
            chunk_number=chunk_number,
            transcript_length=len(result["transcript"]),
            confidence=result["confidence"],
        )

        # 5. Update task metadata with progress
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}
        processed = task_metadata.get("processed_chunks", 0) + 1
        total = task_metadata.get("total_chunks", 0)

        task_metadata["processed_chunks"] = processed
        task_metadata["updated_at"] = datetime.now(UTC).isoformat()

        if total > 0:
            task_metadata["progress_percent"] = int((processed / total) * 100)

        update_task_metadata(session_id, TaskType.TRANSCRIPTION, task_metadata)

        elapsed = time.time() - start_time

        logger.info(
            "DEEPGRAM_CHUNK_COMPLETED",
            task_id=self.request.id,
            session_id=session_id,
            chunk_number=chunk_number,
            elapsed_seconds=round(elapsed, 2),
            transcript_length=len(result["transcript"]),
            progress=f"{processed}/{total}",
        )

        return {
            "session_id": session_id,
            "chunk_number": chunk_number,
            "transcript": result["transcript"],
            "confidence": result["confidence"],
            "duration": result["duration"],
            "language": result["language"],
            "elapsed_seconds": elapsed,
        }

    except Exception as e:
        logger.error(
            "DEEPGRAM_CHUNK_FAILED",
            task_id=self.request.id,
            session_id=session_id,
            chunk_number=chunk_number,
            error=str(e),
            retry_count=self.request.retries,
        )

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 2**self.request.retries  # 2, 4, 8 seconds
            raise self.retry(exc=e, countdown=retry_delay)
        else:
            # Final failure - mark chunk as failed
            logger.error(
                "DEEPGRAM_CHUNK_FINAL_FAILURE",
                session_id=session_id,
                chunk_number=chunk_number,
            )
            raise


def _transcribe_with_deepgram_sync(
    audio_bytes: bytes,
    language: str,
    api_key: str,
    session_id: str,
    chunk_number: int,
) -> dict:
    """Call Deepgram API synchronously using requests library.

    Args:
        audio_bytes: Raw audio data
        language: Language code
        api_key: Deepgram API key
        session_id: Session ID for logging
        chunk_number: Chunk number for logging

    Returns:
        dict with transcript, confidence, duration, language
    """
    import requests

    base_url = "https://api.deepgram.com/v1"
    url = f"{base_url}/listen"

    params = {
        "model": "nova-2",
        "language": language,
        "detect_language": "false",
        "punctuate": "true",
        "diarize": "false",
        "smart_format": "true",
        "filler_words": "false",
    }

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/mpeg",  # MP3 MIME type
    }

    try:
        logger.info(
            "DEEPGRAM_API_CALL",
            audio_size=len(audio_bytes),
            language=language,
            session_id=session_id,
            chunk_number=chunk_number,
        )

        response = requests.post(
            url,
            params=params,
            headers=headers,
            data=audio_bytes,
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(
                "DEEPGRAM_API_ERROR",
                status=response.status_code,
                error=response.text,
            )
            raise ValueError(f"Deepgram API error: {response.status_code}")

        response_data = response.json()

        # Extract transcript from response
        transcript = ""
        confidence = 0.0
        duration = 0.0

        try:
            channels = response_data.get("results", {}).get("channels", [])
            if channels:
                alternatives = channels[0].get("alternatives", [])
                if alternatives:
                    transcript = alternatives[0].get("transcript", "")
                    confidence = alternatives[0].get("confidence", 0.0)

            metadata = response_data.get("metadata", {})
            duration = metadata.get("duration", 0.0)
        except (KeyError, IndexError, TypeError):
            pass

        logger.info(
            "DEEPGRAM_TRANSCRIPTION_COMPLETE",
            transcript_length=len(transcript),
            confidence=confidence,
            duration=duration,
        )

        return {
            "transcript": transcript,
            "confidence": confidence,
            "duration": duration,
            "language": language,
        }

    except Exception as e:
        logger.error(
            "DEEPGRAM_API_EXCEPTION",
            error=str(e),
            session_id=session_id,
            chunk_number=chunk_number,
        )
        raise
