"""Deepgram Full Transcription Task.

Celery task that transcribes the COMPLETE audio (full_audio.webm) accumulated
at a checkpoint. This provides context-aware transcription for diarization.

Flow:
1. Read full_audio.webm from HDF5
2. Call Deepgram API with complete audio
3. Store result in full_transcription dataset
4. Update task metadata

Usage:
    from backend.workers.deepgram_full_transcription_task import deepgram_transcribe_full_audio
    task = deepgram_transcribe_full_audio.delay(session_id="...")
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import (
    CORPUS_PATH,
    add_full_transcription,
    get_task_metadata,
    update_task_metadata,
)
from backend.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="deepgram_transcribe_full_audio", bind=True, max_retries=3)
def deepgram_transcribe_full_audio(
    self,
    session_id: str,
) -> dict:
    """Transcribe full audio accumulation using Deepgram API.

    Called after each checkpoint. Transcribes the complete audio file
    (full_audio.webm) that has been accumulated since session start.

    Args:
        session_id: Session UUID

    Returns:
        dict with transcript, confidence, duration, language

    Raises:
        Retry on transient errors
    """
    start_time = time.time()

    try:
        logger.info(
            "DEEPGRAM_FULL_TRANSCRIPTION_STARTED",
            task_id=self.request.id,
            session_id=session_id,
        )

        # 1. Read full_audio.webm from HDF5
        import h5py

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

        # 2. Call Deepgram API
        import os

        deepgram_api_key = os.environ.get("DEEPGRAM_API_KEY")
        if not deepgram_api_key:
            logger.error(
                "DEEPGRAM_API_KEY_MISSING",
                session_id=session_id,
            )
            raise ValueError("DEEPGRAM_API_KEY environment variable not set")

        result = _transcribe_with_deepgram_sync(
            audio_bytes=audio_bytes,
            api_key=deepgram_api_key,
            session_id=session_id,
        )

        # 3. Save full_transcription to HDF5
        add_full_transcription(
            session_id=session_id,
            transcript=result["transcript"],
            confidence=result["confidence"],
            duration=result["duration"],
            language=result["language"],
            audio_hash=audio_hash,
            task_type=TaskType.TRANSCRIPTION,
        )

        logger.info(
            "FULL_TRANSCRIPTION_SAVED",
            session_id=session_id,
            transcript_length=len(result["transcript"]),
            confidence=result["confidence"],
        )

        # 4. Update task metadata
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}
        task_metadata["full_transcription_completed_at"] = datetime.now(timezone.utc).isoformat()
        task_metadata["full_transcription_confidence"] = result["confidence"]
        update_task_metadata(session_id, TaskType.TRANSCRIPTION, task_metadata)

        elapsed = time.time() - start_time

        logger.info(
            "DEEPGRAM_FULL_TRANSCRIPTION_COMPLETED",
            task_id=self.request.id,
            session_id=session_id,
            elapsed_seconds=round(elapsed, 2),
            transcript_length=len(result["transcript"]),
        )

        return {
            "session_id": session_id,
            "transcript": result["transcript"],
            "confidence": result["confidence"],
            "duration": result["duration"],
            "language": result["language"],
            "elapsed_seconds": elapsed,
        }

    except Exception as e:
        logger.error(
            "DEEPGRAM_FULL_TRANSCRIPTION_FAILED",
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
                "DEEPGRAM_FULL_TRANSCRIPTION_FINAL_FAILURE",
                session_id=session_id,
            )
            raise


def _transcribe_with_deepgram_sync(
    audio_bytes: bytes,
    api_key: str,
    session_id: str,
) -> dict:
    """Call Deepgram API synchronously for full audio.

    Args:
        audio_bytes: Raw audio data
        api_key: Deepgram API key
        session_id: Session ID for logging

    Returns:
        dict with transcript, confidence, duration, language
    """
    import requests

    base_url = "https://api.deepgram.com/v1"
    url = f"{base_url}/listen"

    # Auto-detect language (no forced language for full transcription)
    params = {
        "detect_language": "true",
        "punctuate": "true",
        "smart_format": "true",
        "filler_words": "false",
    }

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/mpeg",
    }

    try:
        logger.info(
            "DEEPGRAM_FULL_API_CALL",
            audio_size=len(audio_bytes),
            session_id=session_id,
        )

        response = requests.post(
            url,
            params=params,
            headers=headers,
            data=audio_bytes,
            timeout=120,  # Full audio may take longer
        )

        if response.status_code != 200:
            logger.error(
                "DEEPGRAM_FULL_API_ERROR",
                status=response.status_code,
                error=response.text,
            )
            raise ValueError(f"Deepgram API error: {response.status_code}")

        response_data = response.json()

        # Extract transcript from response
        transcript = ""
        confidence = 0.0
        duration = 0.0
        language = "unknown"

        try:
            channels = response_data.get("results", {}).get("channels", [])
            if channels:
                alternatives = channels[0].get("alternatives", [])
                if alternatives:
                    transcript = alternatives[0].get("transcript", "")
                    confidence = alternatives[0].get("confidence", 0.0)

            metadata = response_data.get("metadata", {})
            duration = metadata.get("duration", 0.0)

            # Detect language from response if available
            model_info = metadata.get("model_info", {})
            if model_info:
                first_model = next(iter(model_info.values()), {})
                language = first_model.get("arch", "unknown")
        except (KeyError, IndexError, TypeError):
            pass

        logger.info(
            "DEEPGRAM_FULL_TRANSCRIPTION_COMPLETE",
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
            "DEEPGRAM_FULL_API_EXCEPTION",
            error=str(e),
            session_id=session_id,
        )
        raise
