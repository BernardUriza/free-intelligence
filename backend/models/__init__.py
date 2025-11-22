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
    - Checkin models: Appointment, PendingAction, CheckinSession, Clinic, Doctor
"""

from __future__ import annotations

from backend.models.job import Job, JobStatus, JobType
from backend.models.session import EncryptionMetadata, Session, SessionStatus
from backend.models.transcription_job import ChunkMetadata, TranscriptionJob

# FI Receptionist Check-in models
from backend.models.checkin_models import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    CheckinSession,
    CheckinStep,
    Clinic,
    DeviceType,
    Doctor,
    PendingAction,
    PendingActionStatus,
    PendingActionType,
    WaitingRoomEvent,
)

__all__ = [
    # Core models
    "ChunkMetadata",
    "EncryptionMetadata",
    "Job",
    "JobStatus",
    "JobType",
    "Session",
    "SessionStatus",
    "TranscriptionJob",
    # Check-in models (FI-CHECKIN-001)
    "Appointment",
    "AppointmentStatus",
    "AppointmentType",
    "CheckinSession",
    "CheckinStep",
    "Clinic",
    "DeviceType",
    "Doctor",
    "PendingAction",
    "PendingActionStatus",
    "PendingActionType",
    "WaitingRoomEvent",
]
