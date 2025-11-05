from __future__ import annotations

"""
Diarization Job Management
Card: FI-BACKEND-FEAT-004

Manages async diarization jobs with states: pending, in_progress, completed, failed.
Simple in-memory storage for v1.

File: backend/diarization_jobs.py
Created: 2025-10-30
"""

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from backend.logger import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Job status enum."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DiarizationJob:
    """Diarization job metadata."""

    job_id: str
    session_id: str
    audio_file_path: str
    audio_file_size: int
    status: JobStatus
    progress_percent: int  # 0-100
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result_path: Optional[str] = None
    # Additional progress fields (FI-UI-FEAT-206)
    processed: int = 0  # Chunks processed
    total: int = 0  # Total chunks
    percent: float = 0.0  # Same as progress_percent but float
    last_event: str = ""  # Last event description
    updated_at: str = ""  # Last update timestamp
    # Result cache (FI-RELIABILITY-IMPL-003)
    result_data: Optional[dict[str, Any]] = None  # Cached diarization result


# In-memory job store (replace with Redis/DB for production)
_jobs: dict[str, DiarizationJob] = {}


def create_job(session_id: str, audio_file_path: str, audio_file_size: int) -> str:
    """
    Create new diarization job.

    Args:
        session_id: session identifier
        audio_file_path: path to audio file
        audio_file_size: file size in bytes

    Returns:
        job_id (UUID)
    """
    job_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat() + "Z"

    job = DiarizationJob(
        job_id=job_id,
        session_id=session_id,
        audio_file_path=audio_file_path,
        audio_file_size=audio_file_size,
        status=JobStatus.PENDING,
        progress_percent=0,
        created_at=now,
        processed=0,
        total=0,
        percent=0.0,
        last_event="JOB_CREATED",
        updated_at=now,
    )

    _jobs[job_id] = job

    logger.info("JOB_CREATED", job_id=job_id, session_id=session_id, file_size=audio_file_size)
    return job_id


def get_job(job_id: str) -> Optional[DiarizationJob]:
    """
    Get job by ID.

    Returns:
        DiarizationJob or None if not found
    """
    return _jobs.get(job_id)


def update_job_status(
    job_id: str,
    status: JobStatus,
    progress: Optional[int] = None,
    error: Optional[str] = None,
    result_path: Optional[str] = None,
    processed: Optional[int] = None,
    total: Optional[int] = None,
    last_event: Optional[str] = None,
    result_data: Optional[dict[str, Any]] = None,
) -> bool:
    """
    Update job status and metadata.

    Args:
        job_id: job identifier
        status: new job status
        progress: progress percentage (0-100)
        error: error message (if failed)
        result_path: path to result (if completed)
        processed: number of chunks processed
        total: total number of chunks
        last_event: last event description
        result_data: cached diarization result (dict)

    Returns:
        True if job updated, False if job not found
    """
    job = _jobs.get(job_id)
    if not job:
        return False

    job.status = status
    job.updated_at = datetime.now(UTC).isoformat() + "Z"

    if progress is not None:
        job.progress_percent = min(100, max(0, progress))
        job.percent = float(job.progress_percent)

    if processed is not None:
        job.processed = processed

    if total is not None:
        job.total = total

    if last_event is not None:
        job.last_event = last_event

    if status == JobStatus.IN_PROGRESS and not job.started_at:
        job.started_at = datetime.now(UTC).isoformat() + "Z"

    if status in (JobStatus.COMPLETED, JobStatus.FAILED):
        job.completed_at = datetime.now(UTC).isoformat() + "Z"
        job.progress_percent = 100 if status == JobStatus.COMPLETED else job.progress_percent
        job.percent = float(job.progress_percent)

    if error:
        job.error_message = error

    if result_path:
        job.result_path = result_path

    if result_data:
        job.result_data = result_data

    logger.info(
        "JOB_UPDATED",
        job_id=job_id,
        status=status.value,
        progress=job.progress_percent,
        last_event=last_event or "N/A",
    )
    return True


def list_jobs(session_id: Optional[str] = None, limit: int = 50) -> list[DiarizationJob]:
    """
    List jobs, optionally filtered by session_id.

    Returns:
        List of jobs, sorted by created_at (newest first)
    """
    jobs = list(_jobs.values())

    if session_id:
        jobs = [j for j in jobs if j.session_id == session_id]

    # Sort by created_at descending
    jobs.sort(key=lambda j: j.created_at, reverse=True)

    return jobs[:limit]


def cleanup_old_jobs(max_age_hours: int = 24) -> int:
    """
    Remove jobs older than max_age_hours.

    Returns:
        Number of jobs removed
    """
    now = time.time()
    cutoff = now - (max_age_hours * 3600)

    to_remove = []
    for job_id, job in _jobs.items():
        # Parse ISO timestamp
        try:
            created_ts = datetime.fromisoformat(job.created_at.replace("Z", "")).timestamp()
            if created_ts < cutoff:
                to_remove.append(job_id)
        except Exception:
            pass

    for job_id in to_remove:
        del _jobs[job_id]

    if to_remove:
        logger.info("JOBS_CLEANED")

    return len(to_remove)
