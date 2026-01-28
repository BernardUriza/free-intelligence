"""Session Repository Interface - Domain Layer.

Pure domain interface with ZERO infrastructure dependencies.
Defines contract for session persistence without specifying implementation.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.4 - Domain Layer (Interfaces)
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from backend.models.session import SessionStatus


class ISessionRepository(ABC):
    """Session repository interface.

    Defines contract for medical session persistence operations.
    Implementations can use HDF5, PostgreSQL, or any other storage.

    Sessions follow lifecycle: ACTIVE → FINALIZED → DIARIZED → REVIEWED → COMPLETED
    """

    @abstractmethod
    def create(
        self,
        session_id: str,
        patient_id: str | None = None,
        provider_id: str | None = None,
    ) -> str:
        """Create a new active session.

        Args:
            session_id: Unique session identifier (UUID4)
            patient_id: Optional patient UUID
            provider_id: Optional provider UUID

        Returns:
            session_id: UUID of created session

        Raises:
            ValueError: If session_id already exists
        """
        pass

    @abstractmethod
    def get_by_id(self, session_id: str) -> dict | None:
        """Get session by ID.

        Args:
            session_id: Session UUID

        Returns:
            Session data dict or None if not found
        """
        pass

    @abstractmethod
    def list_by_patient(
        self,
        patient_id: str,
        skip: int = 0,
        limit: int = 100,
        status: SessionStatus | None = None,
    ) -> List[dict]:
        """List sessions for a patient.

        Args:
            patient_id: Patient UUID
            skip: Number of records to skip
            limit: Maximum records to return
            status: Optional status filter

        Returns:
            List of session data dicts
        """
        pass

    @abstractmethod
    def list_by_provider(
        self,
        provider_id: str,
        skip: int = 0,
        limit: int = 100,
        status: SessionStatus | None = None,
    ) -> List[dict]:
        """List sessions for a provider.

        Args:
            provider_id: Provider UUID
            skip: Number of records to skip
            limit: Maximum records to return
            status: Optional status filter

        Returns:
            List of session data dicts
        """
        pass

    @abstractmethod
    def list_by_status(
        self,
        status: SessionStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """List sessions by status.

        Args:
            status: Session status to filter
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of session data dicts
        """
        pass

    @abstractmethod
    def update(
        self,
        session_id: str,
        patient_id: str | None = None,
        provider_id: str | None = None,
        recording_duration: float | None = None,
        total_chunks: int | None = None,
    ) -> bool:
        """Update session metadata.

        Args:
            session_id: Session UUID
            patient_id: New patient ID (optional)
            provider_id: New provider ID (optional)
            recording_duration: New duration in seconds (optional)
            total_chunks: New chunk count (optional)

        Returns:
            True if updated, False if session not found
        """
        pass

    @abstractmethod
    def update_status(
        self,
        session_id: str,
        status: SessionStatus,
    ) -> bool:
        """Update session status.

        Args:
            session_id: Session UUID
            status: New status

        Returns:
            True if updated, False if session not found
        """
        pass

    @abstractmethod
    def finalize(
        self,
        session_id: str,
        encryption_algorithm: str = "AES-GCM-256",
        key_id: str = "",
        iv: str = "",
        encrypted_by: str = "system",
    ) -> bool:
        """Mark session as finalized (encrypted, immutable).

        Args:
            session_id: Session UUID
            encryption_algorithm: Encryption algorithm used
            key_id: Encryption key identifier
            iv: Initialization vector (hex string)
            encrypted_by: User/system that encrypted

        Returns:
            True if finalized, False if session not found
        """
        pass

    @abstractmethod
    def mark_diarized(
        self,
        session_id: str,
        diarization_job_id: str,
    ) -> bool:
        """Mark session as diarized (speaker separation completed).

        Args:
            session_id: Session UUID
            diarization_job_id: Job ID that performed diarization

        Returns:
            True if updated, False if session not found
        """
        pass

    @abstractmethod
    def mark_reviewed(self, session_id: str) -> bool:
        """Mark session as reviewed (human approved).

        Args:
            session_id: Session UUID

        Returns:
            True if updated, False if session not found
        """
        pass

    @abstractmethod
    def mark_completed(
        self,
        session_id: str,
        soap_note_path: str,
    ) -> bool:
        """Mark session as completed (SOAP note generated).

        Args:
            session_id: Session UUID
            soap_note_path: Path in HDF5/storage to SOAP note

        Returns:
            True if updated, False if session not found
        """
        pass

    @abstractmethod
    def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Session UUID

        Returns:
            True if session exists
        """
        pass

    @abstractmethod
    def get_stats(self) -> dict:
        """Get session statistics.

        Returns:
            dict with:
                - total: Total number of sessions
                - by_status: Count per status
                - active_count: Number of ACTIVE sessions
                - completed_count: Number of COMPLETED sessions
        """
        pass
