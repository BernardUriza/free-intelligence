"""Base Job model for unified job architecture.

Philosophy:
  Session → Jobs (1 per type)
    ├─ TranscriptionJob (processes chunks)
    ├─ DiarizationJob (processes speakers)
    ├─ SoapGenerationJob (generates notes)
    └─ [Future jobs...]

Each job:
  - Belongs to exactly 1 session
  - Has a specific job_type
  - Processes its domain (chunks, segments, etc.)
  - Can depend on other jobs
  - Persisted in HDF5: /sessions/{session_id}/jobs/{job_type}/{job_id}.json

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Architecture unification
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class JobType(str, Enum):
    """Job types in the system."""

    TRANSCRIPTION = "transcription"
    DIARIZATION = "diarization"
    SOAP_GENERATION = "soap_generation"
    EVIDENCE_EXTRACTION = "evidence_extraction"
    TIMELINE_VERIFICATION = "timeline_verification"


class JobStatus(str, Enum):
    """Job status states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Base job model for all job types.

    All jobs in the system inherit from this base class and add
    their specific fields.

    Attributes:
        job_id: Unique job identifier (UUID)
        session_id: Parent session identifier
        job_type: Type of job (transcription, diarization, etc.)
        status: Current job status
        created_at: Job creation timestamp (ISO 8601)
        started_at: Job start timestamp (optional)
        completed_at: Job completion timestamp (optional)
        updated_at: Last update timestamp
        error_message: Error message if failed (optional)
        depends_on: List of job_ids this job depends on (optional)
        progress_percent: Progress percentage (0-100)
        result_data: Job-specific result data (optional)
    """

    job_id: str
    session_id: str
    job_type: JobType
    status: JobStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    updated_at: str = ""
    error_message: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)
    progress_percent: int = 0
    result_data: Optional[dict[str, Any]] = None

    def __post_init__(self):
        """Set defaults after initialization."""
        if not self.updated_at:
            self.updated_at = self.created_at

    @classmethod
    def create_now(
        cls,
        job_id: str,
        session_id: str,
        job_type: JobType,
        depends_on: Optional[list[str]] = None,
    ) -> Job:
        """Create a new job with current timestamp.

        Args:
            job_id: Unique job identifier
            session_id: Parent session identifier
            job_type: Type of job
            depends_on: List of job_ids this job depends on

        Returns:
            Job instance with pending status and current timestamp
        """
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            job_id=job_id,
            session_id=session_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            depends_on=depends_on or [],
        )

    def start(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.started_at

    def complete(self, result_data: Optional[dict[str, Any]] = None) -> None:
        """Mark job as completed.

        Args:
            result_data: Job-specific result data
        """
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.completed_at
        self.progress_percent = 100
        if result_data:
            self.result_data = result_data

    def fail(self, error_message: str) -> None:
        """Mark job as failed.

        Args:
            error_message: Error description
        """
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def update_progress(self, percent: int) -> None:
        """Update job progress.

        Args:
            percent: Progress percentage (0-100)
        """
        self.progress_percent = max(0, min(100, percent))
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "session_id": self.session_id,
            "job_type": self.job_type.value
            if isinstance(self.job_type, JobType)
            else self.job_type,
            "status": self.status.value if isinstance(self.status, JobStatus) else self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "updated_at": self.updated_at,
            "error_message": self.error_message,
            "depends_on": self.depends_on,
            "progress_percent": self.progress_percent,
            "result_data": self.result_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        """Create Job from dictionary.

        Args:
            data: Dictionary with job data

        Returns:
            Job instance
        """
        # Convert string enums to enum instances
        if isinstance(data.get("job_type"), str):
            data["job_type"] = JobType(data["job_type"])
        if isinstance(data.get("status"), str):
            data["status"] = JobStatus(data["status"])

        return cls(**data)
