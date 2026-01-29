"""Session mapper - DTO to Entity conversions.

Translates between HTTP DTOs and domain entities.
Session data is stored in HDF5 (task-based schema).

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 3B - Complete Mappers
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from backend.domain.session.entity import Session, SessionStatus

if TYPE_CHECKING:
    from backend.api.routers.session.internal.sessions.router import (
        CreateSessionRequest,
        SessionResponse,
    )


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
    def from_hdf5(session_id: str, metadata: Dict[str, Any]) -> Session:
        """Convert HDF5 metadata to domain entity.

        Args:
            session_id: Session UUID
            metadata: HDF5 session metadata dict

        Returns:
            Session domain entity
        """
        return Session(
            session_id=session_id,
            created_at=datetime.fromisoformat(
                metadata.get("created_at", datetime.utcnow().isoformat())
            ),
            status=SessionStatus(metadata.get("status", "new")),
            updated_at=datetime.fromisoformat(
                metadata.get("updated_at", datetime.utcnow().isoformat())
            ),
            last_active=datetime.fromisoformat(
                metadata.get("last_active", datetime.utcnow().isoformat())
            ),
            interaction_count=metadata.get("interaction_count", 0),
            is_persisted=metadata.get("is_persisted", False),
            owner_hash=metadata.get("owner_hash"),
            thread_id=metadata.get("thread_id"),
            has_transcription=metadata.get("has_transcription", False),
            has_diarization=metadata.get("has_diarization", False),
            has_soap=metadata.get("has_soap", False),
            chunk_count=metadata.get("chunk_count", 0),
            duration_seconds=metadata.get("duration_seconds", 0.0),
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
    def to_hdf5_metadata(entity: Session) -> Dict[str, Any]:
        """Convert domain entity to HDF5 metadata dict.

        Args:
            entity: Session domain entity

        Returns:
            Metadata dict for HDF5 storage
        """
        return {
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat(),
            "last_active": entity.last_active.isoformat(),
            "status": entity.status.value,
            "interaction_count": entity.interaction_count,
            "is_persisted": entity.is_persisted,
            "owner_hash": entity.owner_hash,
            "thread_id": entity.thread_id,
            "has_transcription": entity.has_transcription,
            "has_diarization": entity.has_diarization,
            "has_soap": entity.has_soap,
            "chunk_count": entity.chunk_count,
            "duration_seconds": entity.duration_seconds,
        }
