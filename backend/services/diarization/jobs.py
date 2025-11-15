"""HDF5-backed diarization job management.

Manages async diarization jobs with states: pending, in_progress, completed, failed.
Uses unified JobRepository for persistent job storage in corpus.h5.

Functions:
  - create_job(): Create new job
  - get_job(): Retrieve job by ID
  - update_job(): Update job status and progress
  - list_jobs(): List all jobs
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from backend.logger import get_logger
from backend.models import JobType
from backend.repositories import job_repository
from backend.services.diarization.models import DiarizationJob

logger = get_logger(__name__)


def create_job(session_id: str, audio_file_path: str, audio_file_size: int) -> str:
    """Create new diarization job with HDF5 persistence.

    Args:
        session_id: Session identifier
        audio_file_path: Path to audio file
        audio_file_size: File size in bytes

    Returns:
        job_id (UUID)
    """
    job_id = str(uuid.uuid4())

    # Create job using factory method
    job = DiarizationJob.create_for_session(
        job_id=job_id,
        session_id=session_id,
        audio_file_path=audio_file_path,
        audio_file_size=audio_file_size,
        total_chunks=0,
    )

    # Save to HDF5 using unified repository
    job_repository.save(job)

    logger.info("JOB_CREATED", job_id=job_id, session_id=session_id, file_size=audio_file_size)
    return job_id


def get_job(job_id: str, session_id: Optional[str] = None) -> Optional[DiarizationJob]:
    """Retrieve job by ID from HDF5.

    Args:
        job_id: Job identifier
        session_id: Optional session identifier (for faster lookup)

    Returns:
        DiarizationJob or None if not found
    """
    # If session_id provided, direct lookup
    if session_id:
        job = job_repository.load(
            job_id=job_id,
            session_id=session_id,
            job_type=JobType.DIARIZATION,
            job_class=DiarizationJob,
        )
        if not job:
            logger.warning("JOB_NOT_FOUND", job_id=job_id, session_id=session_id)
        return job

    # Otherwise, search across all diarization jobs (less efficient)
    # This maintains backward compatibility but is slower
    all_jobs = list_jobs()
    for job in all_jobs:
        if job.job_id == job_id:
            return job

    logger.warning("JOB_NOT_FOUND", job_id=job_id)
    return None


def update_job(
    job_id: str,
    session_id: Optional[str] = None,
    status: Optional[str] = None,
    progress_percent: Optional[int] = None,
    processed_chunks: Optional[int] = None,
    total_chunks: Optional[int] = None,
    error_message: Optional[str] = None,
    result_path: Optional[str] = None,
    result_data: Optional[dict[str, Any]] = None,
) -> Optional[DiarizationJob]:
    """Update job status and progress with HDF5 persistence.

    Args:
        job_id: Job identifier
        session_id: Optional session identifier (for faster lookup)
        status: New status (Union[pending, in_progress, completed] | failed)
        progress_percent: Progress percentage (0-100)
        processed_chunks: Number of chunks processed
        total_chunks: Total number of chunks
        error_message: Error message if failed
        result_path: Path to result in HDF5
        result_data: Cached result data

    Returns:
        Updated DiarizationJob or None if not found
    """
    # Load job from HDF5
    job = get_job(job_id, session_id=session_id)

    if not job:
        logger.warning("JOB_NOT_FOUND", job_id=job_id)
        return None

    # Update fields using base Job methods where applicable
    if status:
        from backend.models import JobStatus

        job_status = JobStatus(status)
        if job_status == JobStatus.IN_PROGRESS and job.status == JobStatus.PENDING:
            job.start()
        elif job_status == JobStatus.COMPLETED:
            job.complete(result_data=result_data)
        elif job_status == JobStatus.FAILED and error_message:
            job.fail(error_message)
        else:
            job.status = job_status
            job.updated_at = datetime.now(timezone.utc).isoformat()

    if progress_percent is not None:
        job.update_progress(progress_percent)

    if processed_chunks is not None:
        job.processed_chunks = processed_chunks

    if total_chunks is not None:
        job.total_chunks = total_chunks

    if result_path:
        job.result_path = result_path

    # Save updated job to HDF5 using unified repository
    job_repository.save(job)

    logger.info(
        "JOB_UPDATED",
        job_id=job_id,
        status=status,
        progress_percent=progress_percent,
        processed=processed_chunks,
        total=total_chunks,
    )

    return job


def list_jobs(session_id: Optional[str] = None) -> list[DiarizationJob]:
    """List all diarization jobs from HDF5.

    Args:
        session_id: Optional session identifier to filter by session

    Returns:
        List of all DiarizationJob objects
    """
    if session_id:
        # List jobs for specific session
        return job_repository.list_by_session(
            session_id=session_id, job_type=JobType.DIARIZATION, job_class=DiarizationJob
        )
    else:
        # List all diarization jobs across all sessions
        # Combine jobs from all statuses
        from backend.models import JobStatus

        all_jobs = []
        for status in JobStatus:
            jobs = job_repository.list_by_status(status=status, job_class=DiarizationJob)
            # Filter to only diarization jobs
            all_jobs.extend([j for j in jobs if j.job_type == JobType.DIARIZATION])

        # Remove duplicates by job_id
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            if job.job_id not in seen:
                seen.add(job.job_id)
                unique_jobs.append(job)

        return unique_jobs


def delete_job(job_id: str, session_id: Optional[str] = None) -> bool:
    """Delete job from HDF5 (for cleanup).

    Args:
        job_id: Job identifier
        session_id: Optional session identifier (for faster lookup)

    Returns:
        True if job was deleted, False if not found
    """
    # Load job first to get session_id if not provided
    job = get_job(job_id, session_id=session_id)
    if not job:
        return False

    # Delete using repository
    deleted = job_repository.delete(
        job_id=job_id, session_id=job.session_id, job_type=JobType.DIARIZATION
    )

    if deleted:
        logger.info("JOB_DELETED", job_id=job_id, session_id=job.session_id)
    else:
        logger.error("DELETE_JOB_FAILED", job_id=job_id, session_id=job.session_id)

    return deleted
