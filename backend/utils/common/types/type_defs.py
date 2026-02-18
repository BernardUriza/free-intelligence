"""Type definitions for Free Intelligence backend.

Provides TypedDict and dataclass definitions for type safety.
Improves IDE autocomplete and Pylance type checking.

File: backend/types.py
Created: 2025-10-31
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict


def utc_now() -> datetime:
    """
    Get current UTC time with timezone info.

    HIPAA-compliant timezone-aware datetime utility.
    All timestamps in the system should use this function
    to ensure consistency across audit logs, documents, and sessions.

    Returns:
        datetime: Current UTC time with tzinfo=timezone.utc

    Examples:
        >>> now = utc_now()
        >>> now.tzinfo
        datetime.timezone.utc
        >>> now > utc_now()  # False - time moves forward
        False

    HIPAA Rationale:
        - Audit trails require consistent timestamps
        - Cross-timezone queries need UTC normalization
        - Prevents bugs from naive datetime comparisons
    """
    return datetime.now(timezone.utc)


class KPIsSnapshot(TypedDict, total=False):
    """KPIs aggregator snapshot."""

    http_requests: int
    http_latency_p95_ms: int
    llm_requests: int
    llm_latency_p95_ms: int
    cache_hits: int
    timestamp: str


class JobStatusDict(TypedDict, total=False):
    """Diarization job status."""

    job_id: str
    session_id: str
    status: str
    progress_pct: int
    error: str | None
    result: dict[str, Any] | None
    created_at: str
    updated_at: str


class DiarizationChunkDict(TypedDict, total=False):
    """Diarization chunk result."""

    chunk_idx: int
    start_time: float
    end_time: float
    text: str
    speaker: str
    temperature: float
    rtf: float
    timestamp: str


class AuditLogDict(TypedDict, total=False):
    """Audit log entry with multi-tenancy support."""

    timestamp: datetime
    action: str
    user_id: str
    clinic_id: str | None  # Multi-tenancy: track which clinic performed action
    resource: str
    result: str
    details: dict[str, Any]


class ConsultationMetadataDict(TypedDict, total=False):
    """Consultation metadata."""

    consultation_id: str
    session_id: str
    created_at: str
    updated_at: str
    status: str
    duration_sec: float
