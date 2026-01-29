"""Session mapper - DTO to Entity conversions.

Translates between HTTP DTOs and domain entities.
Session data is stored in HDF5 (task-based schema).

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 3B - Complete Mappers
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from backend.domain.session.entity import Session, SessionStatus

if TYPE_CHECKING:
    from backend.api.routers.session.internal.sessions.router import (
        CreateSessionRequest,
        SessionResponse,
    )


@dataclass
class SessionHDF5Metadata:
    """Typed HDF5 metadata for Session (Fix #3 - Type Safety).

    Replaces Dict[str, Any] to prevent silent schema mismatches.
    All fields are REQUIRED - missing keys will fail at parse time.
    """

    created_at: str  # ISO format datetime
    updated_at: str  # ISO format datetime
    last_active: str  # ISO format datetime
    status: str  # SessionStatus.value
    interaction_count: int
    is_persisted: bool
    owner_hash: str | None
    thread_id: str | None
    has_transcription: bool
    has_diarization: bool
    has_soap: bool
    chunk_count: int
    duration_seconds: float


class SessionMapper:
    """Maps between Session representations."""

    @staticmethod
    def from_create_dto(dto: CreateSessionRequest, session_id: str) -> Session:
        """Convert CreateSessionRequest to domain entity.

        Args:
            dto: API create request
            session_id: Generated UUID

        Returns:
            Session domain entity
        """
        return Session(
            session_id=session_id,
            created_at=datetime.utcnow(),
            status=SessionStatus(dto.status) if dto.status else SessionStatus.NEW,
            thread_id=dto.thread_id,
        )

    @staticmethod
    def from_hdf5(session_id: str, metadata: SessionHDF5Metadata) -> Session:
        """Convert HDF5 metadata to domain entity (Fix #3 - Type Safety).

        Args:
            session_id: Session UUID
            metadata: TYPED HDF5 session metadata (no Dict[str, Any])

        Returns:
            Session domain entity

        Raises:
            AttributeError: If metadata is missing required keys (FAIL FAST)
            ValueError: If datetime strings are invalid ISO format
        """
        return Session(
            session_id=session_id,
            created_at=datetime.fromisoformat(metadata.created_at),
            status=SessionStatus(metadata.status),
            updated_at=datetime.fromisoformat(metadata.updated_at),
            last_active=datetime.fromisoformat(metadata.last_active),
            interaction_count=metadata.interaction_count,
            is_persisted=metadata.is_persisted,
            owner_hash=metadata.owner_hash,
            thread_id=metadata.thread_id,
            has_transcription=metadata.has_transcription,
            has_diarization=metadata.has_diarization,
            has_soap=metadata.has_soap,
            chunk_count=metadata.chunk_count,
            duration_seconds=metadata.duration_seconds,
        )

    @staticmethod
    def to_response_dto(entity: Session) -> SessionResponse:
        """Convert domain entity to API response DTO.

        Args:
            entity: Session domain entity

        Returns:
            SessionResponse Pydantic model
        """
        from backend.api.routers.session.internal.sessions.router import SessionResponse

        return SessionResponse(
            id=entity.session_id,
            created_at=entity.created_at.isoformat(),
            updated_at=entity.updated_at.isoformat(),
            last_active=entity.last_active.isoformat(),
            interaction_count=entity.interaction_count,
            status=entity.status.value,
            is_persisted=entity.is_persisted,
            owner_hash=entity.owner_hash or "",
            thread_id=entity.thread_id,
        )

    @staticmethod
    def to_hdf5_metadata(entity: Session) -> SessionHDF5Metadata:
        """Convert domain entity to HDF5 metadata (Fix #3 - Type Safety).

        Args:
            entity: Session domain entity

        Returns:
            TYPED SessionHDF5Metadata (use dataclasses.asdict() in repository)
        """
        return SessionHDF5Metadata(
            created_at=entity.created_at.isoformat(),
            updated_at=entity.updated_at.isoformat(),
            last_active=entity.last_active.isoformat(),
            status=entity.status.value,
            interaction_count=entity.interaction_count,
            is_persisted=entity.is_persisted,
            owner_hash=entity.owner_hash,
            thread_id=entity.thread_id,
            has_transcription=entity.has_transcription,
            has_diarization=entity.has_diarization,
            has_soap=entity.has_soap,
            chunk_count=entity.chunk_count,
            duration_seconds=entity.duration_seconds,
        )
