"""Session domain entity - pure business logic.

Session represents a clinical consultation session with audio recording,
transcription, diarization, and SOAP note generation.

This is a PURE domain entity with ZERO framework dependencies.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 2 - Pure Domain Entities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session lifecycle status."""

    NEW = "new"  # Just created, no activity
    ACTIVE = "active"  # In progress (recording/processing)
    PROCESSING = "processing"  # Background tasks running
    COMPLETE = "complete"  # All tasks finished
    ARCHIVED = "archived"  # Finalized and archived


@dataclass
class Session:
    """Session domain entity.

    Represents a clinical consultation session in the healthcare system.

    Business rules:
    - session_id is immutable
    - status can only progress forward (new → active → complete → archived)
    - last_active is updated on any interaction
    - owner_hash identifies the session owner (user)
    """

    session_id: str
    created_at: datetime
    status: SessionStatus = SessionStatus.NEW
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_active: datetime = field(default_factory=lambda: datetime.now(UTC))
    interaction_count: int = 0
    is_persisted: bool = False
    owner_hash: str | None = None
    thread_id: str | None = None

    # Session metadata (derived from tasks)
    has_transcription: bool = False
    has_diarization: bool = False
    has_soap: bool = False
    chunk_count: int = 0
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        """Validate entity after initialization.

        Raises:
            ValueError: If business rules are violated
        """
        if not self.session_id or not self.session_id.strip():
            raise ValueError("Session ID cannot be empty")

        # Ensure dates are UTC-aware
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=UTC)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=UTC)
        if self.last_active.tzinfo is None:
            self.last_active = self.last_active.replace(tzinfo=UTC)

    # ========================================================================
    # Domain Behavior (Business Logic)
    # ========================================================================

    def record_interaction(self) -> None:
        """Record user interaction with session.

        Updates interaction_count and last_active timestamp.
        """
        self.interaction_count += 1
        self.last_active = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def advance_status(self, new_status: SessionStatus) -> None:
        """Advance session to new status.

        Args:
            new_status: Target status

        Raises:
            ValueError: If status transition is invalid
        """
        # Define allowed transitions
        valid_transitions = {
            SessionStatus.NEW: [SessionStatus.ACTIVE],
            SessionStatus.ACTIVE: [SessionStatus.PROCESSING, SessionStatus.COMPLETE],
            SessionStatus.PROCESSING: [SessionStatus.COMPLETE, SessionStatus.ACTIVE],
            SessionStatus.COMPLETE: [SessionStatus.ARCHIVED],
            SessionStatus.ARCHIVED: [],  # Terminal state
        }

        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(
                f"Invalid status transition: {self.status} → {new_status}"
            )

        self.status = new_status
        self.updated_at = datetime.now(UTC)

    def mark_persisted(self) -> None:
        """Mark session as persisted to HDF5 storage."""
        self.is_persisted = True
        self.updated_at = datetime.now(UTC)

    def update_metadata(
        self,
        has_transcription: bool | None = None,
        has_diarization: bool | None = None,
        has_soap: bool | None = None,
        chunk_count: int | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        """Update session metadata from task results.

        Args:
            has_transcription: Transcription task completed
            has_diarization: Diarization task completed
            has_soap: SOAP generation task completed
            chunk_count: Number of transcription chunks
            duration_seconds: Total audio duration
        """
        if has_transcription is not None:
            self.has_transcription = has_transcription
        if has_diarization is not None:
            self.has_diarization = has_diarization
        if has_soap is not None:
            self.has_soap = has_soap
        if chunk_count is not None:
            self.chunk_count = chunk_count
        if duration_seconds is not None:
            self.duration_seconds = duration_seconds

        self.updated_at = datetime.now(UTC)

    def is_ready_for_soap(self) -> bool:
        """Check if session has completed diarization (ready for SOAP).

        Returns:
            True if diarization is complete
        """
        return self.has_diarization

    def is_complete(self) -> bool:
        """Check if all processing tasks are complete.

        Returns:
            True if session is fully processed
        """
        return self.status == SessionStatus.COMPLETE

    def get_age_minutes(self) -> float:
        """Get session age in minutes.

        Returns:
            Minutes since session creation
        """
        age = datetime.now(UTC) - self.created_at
        return age.total_seconds() / 60

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Session(id={self.session_id}, status={self.status.value}, "
            f"age={self.get_age_minutes():.1f}m)"
        )
