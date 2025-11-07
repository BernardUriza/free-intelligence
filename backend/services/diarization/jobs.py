"""HDF5-backed diarization job management.

Manages async diarization jobs with states: pending, in_progress, completed, failed.
Uses HDF5 (storage/diarization.h5) for persistent job storage.

Functions:
  - create_job(): Create new job
  - get_job(): Retrieve job by ID
  - update_job(): Update job status and progress
  - list_jobs(): List all jobs
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.logger import get_logger
from backend.services.diarization.models import DiarizationJob

logger = get_logger(__name__)

# HDF5 storage path
DIARIZATION_H5_PATH = Path(__file__).parent.parent.parent.parent / "storage" / "diarization.h5"

# In-memory job store (TODO: replace with HDF5 for production)
_jobs: dict[str, DiarizationJob] = {}


def create_job(session_id: str, audio_file_path: str, audio_file_size: int) -> str:
    """Create new diarization job.

    Args:
        session_id: Session identifier
        audio_file_path: Path to audio file
        audio_file_size: File size in bytes

    Returns:
        job_id (UUID)
    """
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"

    job = DiarizationJob(
        job_id=job_id,
        session_id=session_id,
        audio_file_path=audio_file_path,
        audio_file_size=audio_file_size,
        status="pending",
        progress_percent=0,
        created_at=now,
        processed_chunks=0,
        total_chunks=0,
        last_event="JOB_CREATED",
        updated_at=now,
    )

    _jobs[job_id] = job

    logger.info("JOB_CREATED", job_id=job_id, session_id=session_id, file_size=audio_file_size)
    return job_id


def get_job(job_id: str) -> Optional[DiarizationJob]:
    """Retrieve job by ID.

    Args:
        job_id: Job identifier

    Returns:
        DiarizationJob or None if not found
    """
    if job_id not in _jobs:
        logger.warning("JOB_NOT_FOUND", job_id=job_id)
        return None

    return _jobs[job_id]


def update_job(
    job_id: str,
    status: Optional[str] = None,
    progress_percent: Optional[int] = None,
    processed_chunks: Optional[int] = None,
    total_chunks: Optional[int] = None,
    error_message: Optional[str] = None,
    result_path: Optional[str] = None,
    result_data: Optional[dict[str, Any]] = None,
) -> Optional[DiarizationJob]:
    """Update job status and progress.

    Args:
        job_id: Job identifier
        status: New status (pending | in_progress | completed | failed)
        progress_percent: Progress percentage (0-100)
        processed_chunks: Number of chunks processed
        total_chunks: Total number of chunks
        error_message: Error message if failed
        result_path: Path to result in HDF5
        result_data: Cached result data

    Returns:
        Updated DiarizationJob or None if not found
    """
    if job_id not in _jobs:
        logger.warning("JOB_NOT_FOUND", job_id=job_id)
        return None

    job = _jobs[job_id]
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"

    if status:
        job.status = status
        if status == "in_progress" and not job.started_at:
            job.started_at = now
        if status == "completed":
            job.completed_at = now
            job.progress_percent = 100

    if progress_percent is not None:
        job.progress_percent = progress_percent

    if processed_chunks is not None:
        job.processed_chunks = processed_chunks

    if total_chunks is not None:
        job.total_chunks = total_chunks

    if error_message:
        job.error_message = error_message

    if result_path:
        job.result_path = result_path

    if result_data:
        job.result_data = result_data

    job.updated_at = now

    logger.info(
        "JOB_UPDATED",
        job_id=job_id,
        status=status,
        progress_percent=progress_percent,
        processed=processed_chunks,
        total=total_chunks,
    )

    return job


def list_jobs() -> list[DiarizationJob]:
    """List all jobs.

    Returns:
        List of all DiarizationJob objects
    """
    return list(_jobs.values())


def delete_job(job_id: str) -> bool:
    """Delete job (for cleanup).

    Args:
        job_id: Job identifier

    Returns:
        True if job was deleted, False if not found
    """
    if job_id not in _jobs:
        return False

    del _jobs[job_id]
    logger.info("JOB_DELETED", job_id=job_id)
    return True
