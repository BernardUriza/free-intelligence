"""DEPRECATED: Unified job repository for HDF5 storage.

⚠️  DEPRECATION WARNING ⚠️

This module is DEPRECATED as of 2025-11-14.
Use backend.storage.task_repository instead.

The old architecture (jobs/ + production/) has been replaced with
a unified task-based architecture (tasks/{TASK_TYPE}/).

Migration:
  OLD: job_repository.save(job)
  NEW: ensure_task_exists(session_id, task_type)
       update_task_metadata(session_id, task_type, metadata)

See: backend/storage/task_repository.py

Philosophy (OLD - DEPRECATED):
  - Jobs stored in /sessions/{session_id}/jobs/{job_type}/{job_id}.json
  - Each job type (transcription, diarization, etc.) uses same storage pattern
  - Supports polymorphic job types via to_dict/from_dict
  - Thread-safe HDF5 operations

Storage structure (OLD - DEPRECATED):
  /sessions/{session_id}/jobs/
    ├─ transcription/{job_id}.json
    ├─ diarization/{job_id}.json
    ├─ soap_generation/{job_id}.json
    └─ [other job types...]

Author: Bernard Uriza Orozco
Created: 2025-11-14
Deprecated: 2025-11-14
Card: Architecture refactor - task-based HDF5
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Type, TypeVar

import h5py

from backend.logger import get_logger
from backend.models import Job, JobStatus, JobType

logger = get_logger(__name__)

# Type variable for polymorphic job handling
TJob = TypeVar("TJob", bound=Job)

# HDF5 storage path (corpus.h5 is the single source of truth)
CORPUS_H5_PATH = Path(__file__).parent.parent.parent / "storage" / "corpus.h5"


class JobRepository:
    """Repository for unified job storage in HDF5."""

    def __init__(self, corpus_path: Optional[Path] = None):
        """Initialize repository.

        Args:
            corpus_path: Path to corpus.h5 (defaults to storage/corpus.h5)
        """
        self.corpus_path = corpus_path or CORPUS_H5_PATH

    def _ensure_job_group(self, session_id: str, job_type: JobType) -> None:
        """Ensure HDF5 job group exists for session and job type.

        Args:
            session_id: Session identifier
            job_type: Type of job
        """
        self.corpus_path.parent.mkdir(parents=True, exist_ok=True)

        with h5py.File(self.corpus_path, "a") as f:
            # Create sessions group if not exists
            if "sessions" not in f:
                f.create_group("sessions")

            # Create session group if not exists
            if session_id not in f["sessions"]:  # type: ignore[operator]
                f["sessions"].create_group(session_id)  # type: ignore[index]

            session_group = f["sessions"][session_id]  # type: ignore[index]

            # Create jobs group if not exists
            if "jobs" not in session_group:  # type: ignore[operator]
                session_group.create_group("jobs")  # type: ignore[index]

            jobs_group = session_group["jobs"]  # type: ignore[index]

            # Create job_type group if not exists
            job_type_str = job_type.value if isinstance(job_type, JobType) else job_type
            if job_type_str not in jobs_group:  # type: ignore[operator]
                jobs_group.create_group(job_type_str)  # type: ignore[index]

    def save(self, job: Job) -> None:
        """Save job to HDF5.

        Args:
            job: Job instance to save
        """
        self._ensure_job_group(job.session_id, job.job_type)

        job_dict = job.to_dict()
        job_json = json.dumps(job_dict)

        with h5py.File(self.corpus_path, "a") as f:
            job_type_str = job.job_type.value if isinstance(job.job_type, JobType) else job.job_type
            job_group_path = f"sessions/{job.session_id}/jobs/{job_type_str}"
            job_group = f[job_group_path]  # type: ignore[index]

            # Delete existing dataset if present
            if job.job_id in job_group:  # type: ignore[operator]
                del job_group[job.job_id]  # type: ignore[index]

            # Create new dataset with JSON string
            job_group.create_dataset(  # type: ignore[union-attr]
                job.job_id, data=job_json, dtype=h5py.string_dtype(encoding="utf-8")
            )

        logger.info(
            "JOB_SAVED",
            job_id=job.job_id,
            session_id=job.session_id,
            job_type=job_type_str,
            status=job.status.value if isinstance(job.status, JobStatus) else job.status,
        )

    def load(
        self,
        job_id: str,
        session_id: str,
        job_type: JobType,
        job_class: Type[TJob] = Job,  # type: ignore[assignment]
    ) -> Optional[TJob]:
        """Load job from HDF5.

        Args:
            job_id: Job identifier
            session_id: Session identifier
            job_type: Type of job
            job_class: Job class to instantiate

        Returns:
            Job instance or None if not found
        """
        if not self.corpus_path.exists():
            return None

        job_type_str = job_type.value if isinstance(job_type, JobType) else job_type

        try:
            with h5py.File(self.corpus_path, "r") as f:
                job_group_path = f"sessions/{session_id}/jobs/{job_type_str}"

                # Check if path exists
                if job_group_path not in f:  # type: ignore[operator]
                    return None

                job_group = f[job_group_path]  # type: ignore[index]

                if job_id not in job_group:  # type: ignore[operator]
                    return None

                # Load JSON string
                job_json = job_group[job_id][()]  # type: ignore[index]
                if isinstance(job_json, bytes):
                    job_json = job_json.decode("utf-8")

                job_dict = json.loads(job_json)

                # Use from_dict if available, otherwise constructor
                if hasattr(job_class, "from_dict"):
                    return job_class.from_dict(job_dict)  # type: ignore[return-value]
                else:
                    return job_class(**job_dict)  # type: ignore[return-value]

        except Exception as e:
            logger.error(
                "LOAD_JOB_FAILED",
                job_id=job_id,
                session_id=session_id,
                job_type=job_type_str,
                error=str(e),
            )
            return None

    def list_by_session(
        self,
        session_id: str,
        job_type: Optional[JobType] = None,
        job_class: Type[TJob] = Job,  # type: ignore[assignment]
    ) -> list[TJob]:
        """List all jobs for a session, optionally filtered by job_type.

        Args:
            session_id: Session identifier
            job_type: Optional job type filter
            job_class: Job class to instantiate

        Returns:
            List of job instances
        """
        if not self.corpus_path.exists():
            return []

        jobs = []
        try:
            with h5py.File(self.corpus_path, "r") as f:
                session_path = f"sessions/{session_id}"
                if session_path not in f:  # type: ignore[operator]
                    return []

                session_group = f[session_path]  # type: ignore[index]
                if "jobs" not in session_group:  # type: ignore[operator]
                    return []

                jobs_group = session_group["jobs"]  # type: ignore[index]

                # Determine which job types to iterate
                if job_type:
                    job_type_str = job_type.value if isinstance(job_type, JobType) else job_type
                    job_types = [job_type_str] if job_type_str in jobs_group else []  # type: ignore[operator]
                else:
                    job_types = list(jobs_group.keys())  # type: ignore[union-attr]

                # Load all jobs
                for jt in job_types:
                    job_type_group = jobs_group[jt]  # type: ignore[index]
                    for job_id in job_type_group.keys():  # type: ignore[union-attr]
                        job_type_enum = JobType(jt)
                        job = self.load(job_id, session_id, job_type_enum, job_class)
                        if job:
                            jobs.append(job)

        except Exception as e:
            logger.error("LIST_JOBS_FAILED", session_id=session_id, error=str(e))

        return jobs

    def list_by_status(
        self,
        status: JobStatus,
        job_class: Type[TJob] = Job,  # type: ignore[assignment]
    ) -> list[TJob]:
        """List all jobs with a specific status across all sessions.

        Args:
            status: Job status to filter
            job_class: Job class to instantiate

        Returns:
            List of job instances
        """
        if not self.corpus_path.exists():
            return []

        jobs = []
        try:
            with h5py.File(self.corpus_path, "r") as f:
                if "sessions" not in f:
                    return []

                sessions_group = f["sessions"]

                # Iterate all sessions
                for session_id in sessions_group.keys():  # type: ignore[union-attr]
                    session_jobs = self.list_by_session(session_id, job_class=job_class)
                    # Filter by status
                    jobs.extend([j for j in session_jobs if j.status == status])

        except Exception as e:
            logger.error("LIST_JOBS_BY_STATUS_FAILED", status=status.value, error=str(e))

        return jobs

    def delete(self, job_id: str, session_id: str, job_type: JobType) -> bool:
        """Delete job from HDF5.

        Args:
            job_id: Job identifier
            session_id: Session identifier
            job_type: Type of job

        Returns:
            True if deleted, False if not found
        """
        if not self.corpus_path.exists():
            return False

        job_type_str = job_type.value if isinstance(job_type, JobType) else job_type

        try:
            with h5py.File(self.corpus_path, "a") as f:
                job_group_path = f"sessions/{session_id}/jobs/{job_type_str}"

                if job_group_path not in f:  # type: ignore[operator]
                    return False

                job_group = f[job_group_path]  # type: ignore[index]

                if job_id not in job_group:  # type: ignore[operator]
                    return False

                del job_group[job_id]  # type: ignore[index]
                logger.info(
                    "JOB_DELETED",
                    job_id=job_id,
                    session_id=session_id,
                    job_type=job_type_str,
                )
                return True

        except Exception as e:
            logger.error(
                "DELETE_JOB_FAILED",
                job_id=job_id,
                session_id=session_id,
                job_type=job_type_str,
                error=str(e),
            )
            return False


# Singleton instance for global use
job_repository = JobRepository()
