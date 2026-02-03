"""Session Mapper - DB ↔ Domain mapping for Session entities.

Handles bidirectional conversion between Session domain entities and HDF5 persistence.

Pattern:
    Repository calls: SessionMapper.to_hdf5_metadata(session) → SessionHDF5Metadata
    Repository calls: SessionMapper.from_hdf5(session_id, metadata) → Session

Author: Claude Code (P1-5 Repository Mappers)
Created: 2026-02-02
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.models.session import Session


# ============================================================================
# HDF5 Persistence Structure
# ============================================================================


@dataclass
class SessionHDF5Metadata:
    """Metadata for Session persistence in HDF5.

    Includes all Session fields stored as JSON in HDF5 group attributes.
    Matches Session.to_dict() output for seamless conversion.
    """

    session_id: str
    status: str  # SessionStatus.value (active|finalized|diarized|reviewed|completed)
    created_at: str  # ISO 8601 datetime
    updated_at: str  # ISO 8601 datetime
    patient_id: str | None = None
    provider_id: str | None = None
    recording_duration: float = 0.0
    total_chunks: int = 0
    encryption_metadata: dict[str, Any] | None = None
    diarization_job_id: str | None = None
    soap_note_path: str | None = None
    finalized_at: str | None = None
    diarized_at: str | None = None
    reviewed_at: str | None = None
    completed_at: str | None = None


# ============================================================================
# SessionMapper - Bidirectional Mapping
# ============================================================================


class SessionMapper:
    """Maps Session domain entity ↔ HDF5 persistence structures.

    Leverages Session's built-in to_dict()/from_dict() methods.
    Ensures type safety with SessionHDF5Metadata dataclass.
    """

    @staticmethod
    def to_hdf5_metadata(session: Session) -> SessionHDF5Metadata:
        """Convert Session domain entity to HDF5 metadata structure.

        Args:
            session: Session entity from domain layer

        Returns:
            SessionHDF5Metadata dataclass for HDF5 storage

        Example:
            >>> session = Session.create_now(session_id="123")
            >>> metadata = SessionMapper.to_hdf5_metadata(session)
            >>> # Store in HDF5: group.attrs["metadata"] = json.dumps(asdict(metadata))
        """
        # Use Session's built-in to_dict() method
        session_dict = session.to_dict()

        # Convert to typed dataclass for type safety
        return SessionHDF5Metadata(**session_dict)

    @staticmethod
    def from_hdf5(session_id: str, metadata: SessionHDF5Metadata | dict[str, Any]) -> Session:
        """Convert HDF5 metadata to Session domain entity.

        Args:
            session_id: Session identifier (for validation)
            metadata: SessionHDF5Metadata dataclass or dict from HDF5 attributes

        Returns:
            Session domain entity with all fields populated

        Example:
            >>> metadata_dict = json.loads(group.attrs["metadata"])
            >>> metadata = SessionHDF5Metadata(**metadata_dict)
            >>> session = SessionMapper.from_hdf5("123", metadata)
        """
        # Handle both dataclass and dict inputs (for backwards compatibility)
        if isinstance(metadata, SessionHDF5Metadata):
            metadata_dict = {
                "session_id": metadata.session_id,
                "status": metadata.status,
                "created_at": metadata.created_at,
                "updated_at": metadata.updated_at,
                "patient_id": metadata.patient_id,
                "provider_id": metadata.provider_id,
                "recording_duration": metadata.recording_duration,
                "total_chunks": metadata.total_chunks,
                "encryption_metadata": metadata.encryption_metadata,
                "diarization_job_id": metadata.diarization_job_id,
                "soap_note_path": metadata.soap_note_path,
                "finalized_at": metadata.finalized_at,
                "diarized_at": metadata.diarized_at,
                "reviewed_at": metadata.reviewed_at,
                "completed_at": metadata.completed_at,
            }
        else:
            metadata_dict = metadata

        # Validate session_id consistency
        if session_id != metadata_dict.get("session_id"):
            raise ValueError(
                f"session_id mismatch: path={session_id}, metadata={metadata_dict.get('session_id')}"
            )

        # Use Session's built-in from_dict() method
        return Session.from_dict(metadata_dict)
