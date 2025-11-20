"""Session model for medical consultations.

A Session represents a complete medical consultation recording with:
- Multiple transcription chunks
- Encryption metadata (when finalized)
- Diarization results (PACIENTE vs MÉDICO)
- SOAP notes (generated)

Lifecycle:
1. ACTIVE: Recording in progress
2. FINALIZED: Recording stopped, encrypted, immutable
3. DIARIZED: Speaker separation completed
4. REVIEWED: Human review/approval done
5. COMPLETED: SOAP note generated, ready for export

Author: Bernard Uriza Orozco
Created: 2025-11-14
"""

from __future__ import annotations

from dataclasses import dataclass
from backend.compat import UTC, datetime
from enum import Enum
from typing import Any


class SessionStatus(str, Enum):
    """Session lifecycle status."""

    ACTIVE = "active"  # Recording in progress
    FINALIZED = "finalized"  # Encrypted, immutable
    DIARIZED = "diarized"  # Speaker separation done
    REVIEWED = "reviewed"  # Human approved
    COMPLETED = "completed"  # SOAP generated


@dataclass
class EncryptionMetadata:
    """Encryption metadata for finalized sessions."""

    algorithm: str = "AES-GCM-256"  # Encryption algorithm
    key_id: str = ""  # Key identifier (for key rotation)
    iv: str = ""  # Initialization vector (hex)
    encrypted_at: str = ""  # ISO timestamp
    encrypted_by: str = "system"  # User/system identifier


@dataclass
class Session:
    """Medical consultation session."""

    session_id: str
    status: SessionStatus
    created_at: str
    updated_at: str
    patient_id: str | None = None  # Optional patient identifier
    provider_id: str | None = None  # Optional provider identifier
    recording_duration: float = 0.0  # Total recording time (seconds)
    total_chunks: int = 0  # Number of audio chunks
    encryption_metadata: EncryptionMetadata | None = None
    diarization_job_id: str | None = None  # Reference to diarization job
    soap_note_path: str | None = None  # Path in HDF5 to SOAP note
    finalized_at: str | None = None
    diarized_at: str | None = None
    reviewed_at: str | None = None
    completed_at: str | None = None

    @classmethod
    def create_now(cls, session_id: str) -> Session:
        """Create a new active session.

        Args:
            session_id: Unique session identifier (UUID4)

        Returns:
            Session instance
        """
        now = datetime.now(UTC).isoformat()
        return cls(
            session_id=session_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    def finalize(self, encryption_metadata: EncryptionMetadata) -> None:
        """Mark session as finalized (encrypted, immutable).

        Args:
            encryption_metadata: Encryption details
        """
        self.status = SessionStatus.FINALIZED
        self.encryption_metadata = encryption_metadata
        self.finalized_at = datetime.now(UTC).isoformat()
        self.updated_at = self.finalized_at

    def mark_diarized(self, diarization_job_id: str) -> None:
        """Mark session as diarized (speaker separation completed).

        Args:
            diarization_job_id: Job ID that performed diarization
        """
        self.status = SessionStatus.DIARIZED
        self.diarization_job_id = diarization_job_id
        self.diarized_at = datetime.now(UTC).isoformat()
        self.updated_at = self.diarized_at

    def mark_reviewed(self) -> None:
        """Mark session as reviewed (human approved)."""
        self.status = SessionStatus.REVIEWED
        self.reviewed_at = datetime.now(UTC).isoformat()
        self.updated_at = self.reviewed_at

    def mark_completed(self, soap_note_path: str) -> None:
        """Mark session as completed (SOAP note generated).

        Args:
            soap_note_path: Path in HDF5 to SOAP note
        """
        self.status = SessionStatus.COMPLETED
        self.soap_note_path = soap_note_path
        self.completed_at = datetime.now(UTC).isoformat()
        self.updated_at = self.completed_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "session_id": self.session_id,
            "status": self.status.value if isinstance(self.status, SessionStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "patient_id": self.patient_id,
            "provider_id": self.provider_id,
            "recording_duration": self.recording_duration,
            "total_chunks": self.total_chunks,
            "diarization_job_id": self.diarization_job_id,
            "soap_note_path": self.soap_note_path,
            "finalized_at": self.finalized_at,
            "diarized_at": self.diarized_at,
            "reviewed_at": self.reviewed_at,
            "completed_at": self.completed_at,
        }

        if self.encryption_metadata:
            result["encryption_metadata"] = {
                "algorithm": self.encryption_metadata.algorithm,
                "key_id": self.encryption_metadata.key_id,
                "iv": self.encryption_metadata.iv,
                "encrypted_at": self.encryption_metadata.encrypted_at,
                "encrypted_by": self.encryption_metadata.encrypted_by,
            }
        else:
            result["encryption_metadata"] = None

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Create Session from dictionary.

        Args:
            data: Dictionary with session data

        Returns:
            Session instance
        """
        # Convert string enums to enum instances
        if isinstance(data.get("status"), str):
            data["status"] = SessionStatus(data["status"])

        # Convert encryption_metadata dict to EncryptionMetadata
        if data.get("encryption_metadata"):
            enc = data["encryption_metadata"]
            data["encryption_metadata"] = EncryptionMetadata(
                algorithm=enc.get("algorithm", "AES-GCM-256"),
                key_id=enc.get("key_id", ""),
                iv=enc.get("iv", ""),
                encrypted_at=enc.get("encrypted_at", ""),
                encrypted_by=enc.get("encrypted_by", "system"),
            )

        return cls(**data)
