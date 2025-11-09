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

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import h5py

from backend.logger import get_logger
from backend.services.diarization.models import DiarizationJob

logger = get_logger(__name__)

# HDF5 storage path
DIARIZATION_H5_PATH = Path(__file__).parent.parent.parent.parent / "storage" / "diarization.h5"


def _ensure_jobs_group() -> None:
    """Ensure HDF5 file and jobs group exist."""
    DIARIZATION_H5_PATH.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(DIARIZATION_H5_PATH, "a") as f:
        if "jobs" not in f:
            f.create_group("jobs")


def _job_to_dict(job: DiarizationJob) -> dict[str, Any]:
    """Convert DiarizationJob to dict for JSON serialization."""
    return {
        "job_id": job.job_id,
        "session_id": job.session_id,
        "audio_file_path": job.audio_file_path,
        "audio_file_size": job.audio_file_size,
        "status": job.status,
        "progress_percent": job.progress_percent,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message,
        "result_path": job.result_path,
        "processed_chunks": job.processed_chunks,
        "total_chunks": job.total_chunks,
        "last_event": job.last_event,
        "updated_at": job.updated_at,
        "result_data": job.result_data,
    }


def _dict_to_job(data: dict[str, Any]) -> DiarizationJob:
    """Convert dict to DiarizationJob."""
    return DiarizationJob(**data)


def _save_job_to_hdf5(job: DiarizationJob) -> None:
    """Save job to HDF5 as JSON string."""
    _ensure_jobs_group()

    job_dict = _job_to_dict(job)
    job_json = json.dumps(job_dict)

    with h5py.File(DIARIZATION_H5_PATH, "a") as f:
        jobs_group = f["jobs"]

        # Delete existing dataset if present
        if job.job_id in jobs_group:
            del jobs_group[job.job_id]

        # Create new dataset with JSON string
        jobs_group.create_dataset(
            job.job_id, data=job_json, dtype=h5py.string_dtype(encoding="utf-8")
        )


def _load_job_from_hdf5(job_id: str) -> Optional[DiarizationJob]:
    """Load job from HDF5."""
    if not DIARIZATION_H5_PATH.exists():
        return None

    try:
        with h5py.File(DIARIZATION_H5_PATH, "r") as f:
            if "jobs" not in f or job_id not in f["jobs"]:
                return None

            job_json = f["jobs"][job_id][()]
            if isinstance(job_json, bytes):
                job_json = job_json.decode("utf-8")

            job_dict = json.loads(job_json)
            return _dict_to_job(job_dict)
    except Exception as e:
        logger.error("LOAD_JOB_FAILED", job_id=job_id, error=str(e))
        return None


def _list_jobs_from_hdf5() -> list[DiarizationJob]:
    """List all jobs from HDF5."""
    if not DIARIZATION_H5_PATH.exists():
        return []

    jobs = []
    try:
        with h5py.File(DIARIZATION_H5_PATH, "r") as f:
            if "jobs" not in f:
                return []

            jobs_group = f["jobs"]
            for job_id in jobs_group.keys():
                job = _load_job_from_hdf5(job_id)
                if job:
                    jobs.append(job)
    except Exception as e:
        logger.error("LIST_JOBS_FAILED", error=str(e))

    return jobs


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
    now = datetime.now(UTC).isoformat().replace("+00:00", "") + "Z"

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

    # Save to HDF5 for persistence
    _save_job_to_hdf5(job)

    logger.info("JOB_CREATED", job_id=job_id, session_id=session_id, file_size=audio_file_size)
    return job_id


def get_job(job_id: str) -> Optional[DiarizationJob]:
    """Retrieve job by ID from HDF5.

    Args:
        job_id: Job identifier

    Returns:
        DiarizationJob or None if not found
    """
    job = _load_job_from_hdf5(job_id)

    if not job:
        logger.warning("JOB_NOT_FOUND", job_id=job_id)
        return None

    return job


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
    """Update job status and progress with HDF5 persistence.

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
    # Load job from HDF5
    job = _load_job_from_hdf5(job_id)

    if not job:
        logger.warning("JOB_NOT_FOUND", job_id=job_id)
        return None

    now = datetime.now(UTC).isoformat().replace("+00:00", "") + "Z"

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

    # Save updated job to HDF5
    _save_job_to_hdf5(job)

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
    """List all jobs from HDF5.

    Returns:
        List of all DiarizationJob objects
    """
    return _list_jobs_from_hdf5()


def delete_job(job_id: str) -> bool:
    """Delete job from HDF5 (for cleanup).

    Args:
        job_id: Job identifier

    Returns:
        True if job was deleted, False if not found
    """
    if not DIARIZATION_H5_PATH.exists():
        return False

    try:
        with h5py.File(DIARIZATION_H5_PATH, "a") as f:
            if "jobs" not in f or job_id not in f["jobs"]:
                return False

            del f["jobs"][job_id]
            logger.info("JOB_DELETED", job_id=job_id)
            return True
    except Exception as e:
        logger.error("DELETE_JOB_FAILED", job_id=job_id, error=str(e))
        return False
