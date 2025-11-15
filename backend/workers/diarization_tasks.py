"""Celery tasks for diarization (speaker separation + text improvement).

Tasks:
- diarize_session_task: Process all chunks from a session with DiarizationService

Architecture:
  PUBLIC/INTERNAL → dispatch task → WORKER (this file) → DiarizationService

Author: Bernard Uriza Orozco
Created: 2025-11-14
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from backend.logger import get_logger
from backend.models import SessionStatus
from backend.models.task_type import TaskStatus, TaskType
from backend.repositories.session_repository import SessionRepository
from backend.services.diarization.diarization_service import DiarizationService
from backend.storage.task_repository import (
    ensure_task_exists,
    get_task_chunks,
    get_task_metadata,
    save_diarization_segments,
    update_task_metadata,
)
from backend.workers.celery_app import celery_app

logger = get_logger(__name__)

# Initialize repositories
session_repo = SessionRepository(
    "/Users/bernardurizaorozco/Documents/free-intelligence/storage/corpus.h5"
)


@celery_app.task(name="diarize_session", bind=True, max_retries=3)
def diarize_session_task(self, session_id: str) -> dict[str, Any]:
    """Diarize all transcribed chunks from a session.

    Reads TranscriptionJob, converts chunks to DiarizationSegments,
    applies speaker classification + text improvement with Ollama.

    Args:
        session_id: Session identifier

    Returns:
        dict with diarization results
    """
    start_time = time.time()
    logger.info("DIARIZATION_TASK_STARTED", session_id=session_id, task_id=self.request.id)

    try:
        # 1. Load session metadata (contains 3 transcription sources)
        session_data = session_repo.read(session_id)
        transcription_sources = (
            session_data.get("metadata", {}).get("transcription_sources", {})
            if session_data
            else {}
        )

        if transcription_sources:
            logger.info(
                "3_SOURCES_LOADED",
                session_id=session_id,
                webspeech_count=len(transcription_sources.get("webspeech_final", [])),
                chunks_count=len(transcription_sources.get("transcription_per_chunks", [])),
                full_length=len(transcription_sources.get("full_transcription", "")),
            )
        else:
            logger.warning("NO_TRANSCRIPTION_SOURCES", session_id=session_id)

        # 2. Load transcription task metadata
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)

        if not task_metadata:
            logger.error("DIARIZATION_NO_TRANSCRIPTION", session_id=session_id)
            return {
                "status": "failed",
                "error": f"No transcription task found for session {session_id}",
            }

        # 3. Load TRIPLE VISION from HDF5: full_transcription + chunks + webspeech_final
        import h5py

        from backend.storage.task_repository import CORPUS_PATH

        full_transcription = None
        webspeech_final = None

        with h5py.File(CORPUS_PATH, "r") as f:
            # Load full_transcription
            full_text_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_transcription"
            if full_text_path in f:
                text_data = f[full_text_path][()]
                full_transcription = bytes(text_data).decode("utf-8")
                logger.info(
                    "FULL_TRANSCRIPTION_LOADED",
                    session_id=session_id,
                    text_length=len(full_transcription),
                )

            # Load webspeech_final
            webspeech_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/webspeech_final"
            if webspeech_path in f:
                import json

                ws_data = f[webspeech_path][()]
                webspeech_json = bytes(ws_data).decode("utf-8")
                webspeech_final = json.loads(webspeech_json)
                logger.info(
                    "WEBSPEECH_FINAL_LOADED",
                    session_id=session_id,
                    count=len(webspeech_final),
                )

        if not full_transcription:
            logger.error("NO_FULL_TRANSCRIPTION", session_id=session_id)
            return {
                "status": "failed",
                "error": "full_transcription not found in TRANSCRIPTION task",
            }

        # Load transcription chunks (for timestamps and metadata)
        chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)

        logger.info(
            "TRANSCRIPTION_LOADED",
            session_id=session_id,
            total_chunks=task_metadata.get("total_chunks", 0),
            processed_chunks=task_metadata.get("processed_chunks", 0),
            chunks_loaded=len(chunks),
        )

        # 4. Calculate metadata from chunks (duration, language)
        total_duration = 0.0
        for chunk in chunks:
            end_time = chunk.get("timestamp_end", 0.0)
            total_duration = max(total_duration, end_time)

        # Get primary language from chunks (most common language)
        languages = [chunk.get("language", "unknown") for chunk in chunks if chunk.get("language")]
        primary_language = max(set(languages), key=languages.count) if languages else "en"

        logger.info(
            "METADATA_PREPARED",
            session_id=session_id,
            total_duration=total_duration,
            primary_language=primary_language,
        )

        # 5. Run DiarizationService with TRIPLE VISION (full_text + chunks + webspeech)
        logger.info("🔧 [WORKER] Initializing DiarizationService...", session_id=session_id)
        diarization_service = DiarizationService()

        # Calculate audio hash (dummy for now, as we don't have audio file path)
        audio_hash = hashlib.sha256(f"{session_id}-audio".encode()).hexdigest()

        logger.info(
            "🚀 [WORKER] Calling diarize_full_text with TRIPLE VISION",
            session_id=session_id,
            full_text_length=len(full_transcription),
            chunks_count=len(chunks),
            webspeech_count=len(webspeech_final) if webspeech_final else 0,
            duration_sec=total_duration,
            language=primary_language,
        )

        # NEW: Use diarize_full_text() with TRIPLE VISION
        # Qwen will intelligently segment and classify using 3 sources:
        # - chunks: Timestamps (every 13s) with mixed speakers
        # - full_transcription: Clean complete text
        # - webspeech_final: Instant transcriptions (for pause detection)
        logger.info(
            "⏳ [WORKER] This will call Claude API and may take 10-60 seconds...",
            session_id=session_id,
        )

        diarization_result = diarization_service.diarize_full_text(
            session_id=session_id,
            full_text=full_transcription,
            chunks=chunks,
            webspeech_final=webspeech_final,
            audio_file_path=f"storage/audio/{session_id}/full.webm",
            audio_file_hash=audio_hash,
            duration_sec=total_duration,
            language=primary_language,
        )

        logger.info(
            "✅ [WORKER] DIARIZATION_COMPLETED",
            session_id=session_id,
            segment_count=len(diarization_result.segments),
            processing_time=diarization_result.processing_time_sec,
        )

        # 4. Save diarization result to DIARIZATION task
        ensure_task_exists(session_id, TaskType.DIARIZATION, allow_existing=True)

        # 5. Save segments to HDF5
        save_diarization_segments(
            session_id=session_id,
            segments=diarization_result.segments,
            task_type=TaskType.DIARIZATION,
        )

        diarization_metadata = {
            "job_id": self.request.id,
            "status": TaskStatus.COMPLETED.value,
            "progress_percent": 100,
            "segment_count": len(diarization_result.segments),
            "processing_time_sec": diarization_result.processing_time_sec,
            "model_llm": diarization_result.model_llm,
            "language": primary_language,
            "audio_hash": audio_hash,
            "duration_sec": total_duration,
        }

        update_task_metadata(session_id, TaskType.DIARIZATION, diarization_metadata)

        logger.info(
            "DIARIZATION_TASK_SAVED",
            session_id=session_id,
            path=f"/sessions/{session_id}/tasks/DIARIZATION",
        )

        # 5. Update Session status to DIARIZED
        session_data = session_repo.read(session_id)
        if session_data:
            session_repo.update(
                session_id,
                {
                    "status": SessionStatus.DIARIZED.value,
                    "metadata": {
                        **session_data.get("metadata", {}),
                        "diarization_completed_at": diarization_result.created_at,
                        "diarization_segment_count": len(diarization_result.segments),
                        "diarization_model": diarization_result.model_llm,
                    },
                },
            )
            logger.info(
                "SESSION_MARKED_DIARIZED",
                session_id=session_id,
                status=SessionStatus.DIARIZED.value,
            )
        else:
            logger.warning(
                "SESSION_NOT_FOUND_FOR_UPDATE",
                session_id=session_id,
            )

        processing_time = time.time() - start_time

        return {
            "status": "completed",
            "session_id": session_id,
            "segment_count": len(diarization_result.segments),
            "processing_time_sec": processing_time,
            "model_llm": diarization_result.model_llm,
        }

    except Exception as e:
        logger.error(
            "DIARIZATION_TASK_FAILED",
            session_id=session_id,
            task_id=self.request.id,
            error=str(e),
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": str(e),
        }
