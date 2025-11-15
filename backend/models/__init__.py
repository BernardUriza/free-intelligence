"""Job and Session models for unified architecture.

Exports:
    - Job: Base job model
    - JobType: Job type enum
    - JobStatus: Job status enum
    - TranscriptionJob: Transcription job (processes chunks)
    - ChunkMetadata: Chunk metadata for TranscriptionJob
    - Session: Medical consultation session
    - SessionStatus: Session lifecycle status
    - EncryptionMetadata: Encryption metadata for sessions
"""

from __future__ import annotations

from backend.models.job import Job, JobStatus, JobType
from backend.models.session import EncryptionMetadata, Session, SessionStatus
from backend.models.transcription_job import ChunkMetadata, TranscriptionJob

__all__ = [
    "Job",
    "JobType",
    "JobStatus",
    "TranscriptionJob",
    "ChunkMetadata",
    "Session",
    "SessionStatus",
    "EncryptionMetadata",
]
