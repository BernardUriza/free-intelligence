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
from backend.models import JobType, SessionStatus, TranscriptionJob
from backend.repositories import job_repository
from backend.repositories.session_repository import SessionRepository
from backend.services.diarization.models import DiarizationSegment
from backend.services.diarization.service import DiarizationService
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

        # 2. Load transcription job
        transcription_job = job_repository.load(
            job_id=session_id,
            session_id=session_id,
            job_type=JobType.TRANSCRIPTION,
            job_class=TranscriptionJob,
        )

        if not transcription_job:
            logger.error("DIARIZATION_NO_TRANSCRIPTION", session_id=session_id)
            return {
                "status": "failed",
                "error": f"No transcription job found for session {session_id}",
            }

        if transcription_job.progress_percent < 100:
            logger.warning(
                "DIARIZATION_INCOMPLETE_TRANSCRIPTION",
                session_id=session_id,
                progress=transcription_job.progress_percent,
            )
            # Retry after 30 seconds if transcription not complete
            raise self.retry(countdown=30, max_retries=10)

        logger.info(
            "TRANSCRIPTION_LOADED",
            session_id=session_id,
            total_chunks=transcription_job.total_chunks,
            processed_chunks=transcription_job.processed_chunks,
        )

        # 2. Convert chunks to DiarizationSegment[]
        segments: list[DiarizationSegment] = []
        total_duration = 0.0

        for chunk in transcription_job.chunks:
            if chunk.status != "completed" or not chunk.transcript:
                logger.warning(
                    "SKIPPING_INCOMPLETE_CHUNK",
                    session_id=session_id,
                    chunk_number=chunk.chunk_number,
                    status=chunk.status,
                )
                continue

            segment = DiarizationSegment(
                start_time=chunk.timestamp_start or 0.0,
                end_time=chunk.timestamp_end or 0.0,
                speaker="DESCONOCIDO",  # Will be classified by DiarizationService
                text=chunk.transcript,
                confidence=chunk.confidence,
            )
            segments.append(segment)
            total_duration = max(total_duration, segment.end_time)

        if not segments:
            logger.error("DIARIZATION_NO_SEGMENTS", session_id=session_id)
            return {
                "status": "failed",
                "error": "No completed segments found for diarization",
            }

        logger.info(
            "SEGMENTS_PREPARED",
            session_id=session_id,
            segment_count=len(segments),
            total_duration=total_duration,
        )

        # 3. Run DiarizationService (with access to 3 transcription sources)
        # TODO: Pass transcription_sources to DiarizationService for LLM analysis
        # The LLM can compare:
        # - webspeech_final: instant previews (may have errors)
        # - transcription_per_chunks: high-quality Whisper per chunk
        # - full_transcription: concatenated final
        # And produce a curated, diarized transcript (PACIENTE vs MÉDICO)
        diarization_service = DiarizationService()

        # Calculate audio hash (dummy for now, as we don't have audio file path)
        audio_hash = hashlib.sha256(f"{session_id}-audio".encode()).hexdigest()

        diarization_result = diarization_service.diarize_segments(
            session_id=session_id,
            segments=segments,
            audio_file_path=f"storage/audio/{session_id}/full.webm",  # Path where full audio should be
            audio_file_hash=audio_hash,
            duration_sec=total_duration,
            language=transcription_job.primary_language,
        )

        logger.info(
            "DIARIZATION_COMPLETED",
            session_id=session_id,
            segment_count=len(diarization_result.segments),
            processing_time=diarization_result.processing_time_sec,
        )

        # 4. Save diarization result to HDF5
        # TODO: Implement diarization result storage (similar to transcription chunks)
        # For now, we'll store it in session metadata

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
