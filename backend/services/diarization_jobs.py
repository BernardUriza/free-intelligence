"""Compatibility wrapper - re-exports from backend.services.diarization.jobs

This module provides backward compatibility for code that imports from
the old 'backend.services.diarization_jobs' location. All imports are
redirected to backend.services.diarization.jobs module.
"""

from __future__ import annotations

from backend.services.diarization.jobs import create_job, get_job, update_job


# JobStatus enum-like class for status strings
class JobStatus:
    """Job status constants"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# Alias for backward compatibility
update_job_status = update_job

__all__ = [
    "JobStatus",
    "create_job",
    "get_job",
    "update_job",
    "update_job_status",
]
