"""Task types for HDF5 session tasks.

Philosophy:
  - 1 Session = 1 medical consultation
  - 1 Session → N Tasks (each type appears MAX 1 time)
  - Task ≠ Job: Task is purpose, Job is execution metadata

Task lifecycle:
  PENDING → IN_PROGRESS → COMPLETED | FAILED

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Architecture refactor - task-based HDF5
"""

from __future__ import annotations

from enum import Enum


class TaskType(str, Enum):
    """Types of tasks that can be performed on a session.

    Each task type can appear AT MOST ONCE per session.
    """

    TRANSCRIPTION = "TRANSCRIPTION"
    """Audio-to-text transcription (Whisper ASR)."""

    DIARIZATION = "DIARIZATION"
    """Speaker diarization (pyannote)."""

    SOAP_GENERATION = "SOAP_GENERATION"
    """SOAP note generation from transcript."""

    EMOTION_ANALYSIS = "EMOTION_ANALYSIS"
    """Emotional analysis of audio/text."""

    ENCRYPTION = "ENCRYPTION"
    """Audio encryption (AES-GCM-256)."""

    SUMMARY = "SUMMARY"
    """Session summary generation."""

    TRANSLATION = "TRANSLATION"
    """Translation to another language."""


class TaskStatus(str, Enum):
    """Status of a task execution."""

    PENDING = "pending"
    """Task created, waiting for worker."""

    IN_PROGRESS = "in_progress"
    """Worker currently processing."""

    COMPLETED = "completed"
    """Task finished successfully."""

    FAILED = "failed"
    """Task failed with error."""

    CANCELLED = "cancelled"
    """Task cancelled by user/system."""
