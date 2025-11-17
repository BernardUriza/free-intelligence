"""Background worker for processing diarization jobs.

Processes jobs in background:
  1. Load pending job from HDF5
  2. Transcribe audio using TranscriptionService
  3. Apply diarization (speaker classification) using DiarizationService
  4. Update job status and save result
  5. Mark job as completed

This worker can be called from:
  - Background thread/process
  - Celery task
  - AWS Lambda
  - Direct call for synchronous processing

Card: FI-BACKEND-FEAT-005
Created: 2025-11-09
"""

from __future__ import annotations

import time
from pathlib import Path

# DEPRECATED: Legacy service module removed
# from backend.services.diarization.service import DiarizationService
from typing import TYPE_CHECKING, Any

from backend.logger import get_logger
from backend.services.diarization.jobs import get_job, update_job
from backend.services.diarization.models import DiarizationSegment
from backend.services.transcription.service import TranscriptionService

if TYPE_CHECKING:
    # Import only for type checking to avoid runtime errors
    class DiarizationService:  # type: ignore[no-redef]
        """Placeholder for deprecated DiarizationService"""

        pass

logger = get_logger(__name__)


def process_job(
    job_id: str,
    transcription_service: TranscriptionService,
    diarization_service: DiarizationService,
) -> bool:
    """Process a single diarization job.

    Args:
        job_id: Job identifier
        transcription_service: TranscriptionService instance
        diarization_service: DiarizationService instance

    Returns:
        True if job processed successfully, False otherwise
    """
    start_time = time.time()

    # Load job
    job = get_job(job_id)
    if not job:
        logger.error("WORKER_JOB_NOT_FOUND", job_id=job_id)
        return False

    if job.status != "pending":
        logger.warning("WORKER_JOB_NOT_PENDING", job_id=job_id, status=job.status)
        return False

    logger.info("WORKER_JOB_START", job_id=job_id, session_id=job.session_id)

    try:
        # Update status to in_progress
        update_job(job_id, status="in_progress", progress_percent=10)

        # Step 1: Read audio file
        audio_path = Path(job.audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with open(audio_path, "rb") as f:
            audio_content = f.read()

        logger.info("WORKER_AUDIO_LOADED", job_id=job_id, size=len(audio_content))
        update_job(job_id, progress_percent=20)

        # Step 2: Transcribe audio
        logger.info("WORKER_TRANSCRIPTION_START", job_id=job_id)
        transcription_result = transcription_service.process_transcription(
            session_id=job.session_id,
            audio_content=audio_content,
            filename=audio_path.name,
            content_type="audio/mpeg",  # TODO: Detect from file
        )

        logger.info(
            "WORKER_TRANSCRIPTION_COMPLETE",
            job_id=job_id,
            segments=len(transcription_result.get("segments", [])),
            duration=transcription_result.get("duration", 0),
        )
        update_job(job_id, progress_percent=60)

        # Step 3: Convert transcription segments to DiarizationSegment
        # Transcription returns: [{"start": 0.0, "end": 5.2, "text": "..."}, ...]
        # We need to add speaker classification
        transcription_segments = transcription_result.get("segments", [])
        diarization_segments = []

        for seg in transcription_segments:
            diarization_segments.append(
                DiarizationSegment(
                    start_time=seg.get("start", 0.0),
                    end_time=seg.get("end", 0.0),
                    speaker="DESCONOCIDO",  # Will be classified by diarization
                    text=seg.get("text", ""),
                )
            )

        logger.info("WORKER_DIARIZATION_START", job_id=job_id, segments=len(diarization_segments))
        update_job(job_id, progress_percent=70)

        # Step 4: Apply diarization (speaker classification + text improvement)
        diarization_result = diarization_service.diarize_segments(
            session_id=job.session_id,
            segments=diarization_segments,
            audio_file_path=str(audio_path),
            audio_file_hash="",  # TODO: Calculate SHA256
            duration_sec=transcription_result.get("duration", 0.0),
            language=transcription_result.get("language", "es"),
        )

        logger.info(
            "WORKER_DIARIZATION_COMPLETE",
            job_id=job_id,
            enriched_segments=len(diarization_result.segments),
        )
        update_job(job_id, progress_percent=90)

        # Step 5: Build result data
        result_data = {
            "transcription": transcription_result,
            "diarization": {
                "segments": [
                    {
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "speaker": seg.speaker,
                        "text": seg.text,
                        "improved_text": seg.improved_text,
                    }
                    for seg in diarization_result.segments
                ],
                "duration_sec": diarization_result.duration_sec,
                "language": diarization_result.language,
                "processing_time_sec": diarization_result.processing_time_sec,
            },
        }

        # Step 6: Mark job as completed
        update_job(
            job_id,
            status="completed",
            progress_percent=100,
            result_data=result_data,
        )

        elapsed = time.time() - start_time
        logger.info(
            "WORKER_JOB_COMPLETE",
            job_id=job_id,
            session_id=job.session_id,
            elapsed_sec=elapsed,
            segments=len(diarization_result.segments),
        )

        return True

    except Exception as e:
        logger.error("WORKER_JOB_FAILED", job_id=job_id, error=str(e), error_type=type(e).__name__)

        # Mark job as failed
        update_job(
            job_id,
            status="failed",
            error_message=str(e),
        )

        return False


def process_pending_jobs(max_jobs: int = 10) -> dict[str, Any]:
    """Process all pending jobs (up to max_jobs).

    Args:
        max_jobs: Maximum number of jobs to process

    Returns:
        Summary dict with processed, succeeded, failed counts
    """
    from backend.services.diarization.jobs import list_jobs

    logger.info("WORKER_SCAN_PENDING_JOBS", max_jobs=max_jobs)

    # Get all pending jobs
    all_jobs = list_jobs()
    pending_jobs = [job for job in all_jobs if job.status == "pending"]

    logger.info("WORKER_FOUND_PENDING", count=len(pending_jobs))

    if not pending_jobs:
        return {"processed": 0, "succeeded": 0, "failed": 0}

    # Limit to max_jobs
    jobs_to_process = pending_jobs[:max_jobs]

    # Create services
    transcription_service = TranscriptionService()
    diarization_service = DiarizationService()

    succeeded = 0
    failed = 0

    for job in jobs_to_process:
        success = process_job(job.job_id, transcription_service, diarization_service)
        if success:
            succeeded += 1
        else:
            failed += 1

    result = {
        "processed": len(jobs_to_process),
        "succeeded": succeeded,
        "failed": failed,
    }

    logger.info("WORKER_BATCH_COMPLETE", **result)
    return result
