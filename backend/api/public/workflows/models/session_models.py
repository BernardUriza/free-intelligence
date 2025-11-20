"""Session Request/Response Models - Pydantic schemas.

SOLID Principle: Single Responsibility
- This module ONLY contains data models (Pydantic schemas)
- No business logic, no data access, no orchestration

File: backend/api/public/workflows/models/session_models.py
Created: 2025-11-20
Pattern: Data Transfer Objects (DTOs)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TranscriptionSourcesModel(BaseModel):
    """3 separate transcription sources for diarization."""

    webspeech_final: list[str] = Field(
        default_factory=list, description="WebSpeech instant previews"
    )
    transcription_per_chunks: list[dict] = Field(
        default_factory=list, description="Whisper per-chunk transcripts"
    )
    full_transcription: str = Field(default="", description="Concatenated full text")


class FinalizeSessionRequest(BaseModel):
    """Request to finalize session and start diarization."""

    transcription_sources: TranscriptionSourcesModel = Field(
        default_factory=TranscriptionSourcesModel,
        description="3 separate transcription sources",
    )


class FinalizeSessionResponse(BaseModel):
    """Response for session finalization (202 Accepted).

    Returns immediately with encryption queued asynchronously.
    """

    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="ACCEPTED (session finalized, encryption queued)")
    finalized_at: str = Field(..., description="ISO timestamp of finalization")
    encryption_status: str = Field(..., description="PENDING | QUEUED | ENQUEUE_FAILED")
    encryption_task_id: str | None = Field(
        None, description="ENCRYPTION task idempotency key (for tracking)"
    )
    diarization_job_id: str | None = Field(
        None, description="Deprecated - use /diarization endpoint instead"
    )
    message: str = Field(..., description="Human-readable message")


class CheckpointRequest(BaseModel):
    """Request for session checkpoint."""

    last_chunk_idx: int = Field(..., description="Last chunk index to include in checkpoint")


class CheckpointResponse(BaseModel):
    """Response for session checkpoint."""

    session_id: str = Field(..., description="Session identifier")
    checkpoint_at: str = Field(..., description="ISO timestamp")
    chunks_concatenated: int = Field(..., description="Number of chunks added")
    full_audio_size: int = Field(..., description="Total size of full_audio.webm in bytes")
    message: str = Field(..., description="Human-readable message")


class DiarizationStatusResponse(BaseModel):
    """Diarization job status for frontend polling."""

    job_id: str = Field(..., description="Celery task ID")
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="pending, processing, completed, failed")
    progress: int = Field(default=0, description="Progress percentage (0-100)")
    segment_count: int = Field(default=0, description="Number of diarized segments")
    transcription_sources: dict[str, Any] | None = Field(
        default=None, description="Triple vision transcription sources"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class UpdateSegmentRequest(BaseModel):
    """Request body for updating segment text."""

    text: str = Field(..., min_length=1, description="New text content for the segment")
