"""Task repository interface.

Manages task lifecycle for multi-step workflows (transcription, diarization, SOAP).
Tasks track chunks, metadata, and progress state.

Author: Claude Code (migrated from utils/common/interfaces/, enhanced)
Created: 2026-01-28
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from abc import ABC, abstractmethod
from typing import Any


class ITaskRepository(ABC):
    """Task workflow storage abstraction.

    Responsibilities:
    - Create tasks for workflows (transcription, diarization, SOAP)
    - Track task metadata (status, progress, timestamps)
    - Manage task chunks (audio segments, speaker segments, etc.)
    - Update chunk datasets (transcript, confidence, etc.)

    Task Types:
    - TRANSCRIPTION: Audio-to-text workflow
    - DIARIZATION: Speaker separation workflow
    - SOAP: Clinical note generation workflow
    - EMOTION_ANALYSIS: Emotional state analysis
    - ENCRYPTION: Session encryption workflow

    Clean Architecture Benefits:
    - Services don't know about HDF5 storage structure
    - Easy to test with in-memory mock
    - Can migrate storage backend without changing services
    """

    @abstractmethod
    def task_exists(self, session_id: str, task_type: str) -> bool:
        """Check if task exists for session.

        Args:
            session_id: Session UUID
            task_type: Task type (TRANSCRIPTION, DIARIZATION, SOAP, etc.)

        Returns:
            True if task exists, False otherwise

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def ensure_task_exists(
        self,
        session_id: str,
        task_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Ensure task exists, create if not.

        Idempotent operation - safe to call multiple times.

        Args:
            session_id: Session UUID
            task_type: Task type (TRANSCRIPTION, DIARIZATION, etc.)
            metadata: Optional initial metadata

        Returns:
            Task ID (usually same as session_id)

        Raises:
            IOError: If create operation fails
        """
        pass

    @abstractmethod
    def get_task_metadata(self, session_id: str, task_type: str) -> dict[str, Any] | None:
        """Get task metadata.

        Args:
            session_id: Session UUID
            task_type: Task type

        Returns:
            Metadata dict with keys:
                - status: str (pending, in_progress, completed, failed)
                - total_chunks: int
                - processed_chunks: int
                - created_at: str (ISO 8601)
                - updated_at: str (ISO 8601)
                - custom fields (workflow-specific)
            None if task doesn't exist

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def save_task_metadata(
        self,
        session_id: str,
        task_type: str,
        metadata: dict[str, Any],
    ) -> None:
        """Save task metadata.

        Args:
            session_id: Session UUID
            task_type: Task type
            metadata: Metadata dict to save

        Raises:
            ValueError: If task doesn't exist
            IOError: If write operation fails
        """
        pass

    @abstractmethod
    def get_task_chunks(self, session_id: str, task_type: str) -> list[dict[str, Any]]:
        """Get all task chunks.

        Args:
            session_id: Session UUID
            task_type: Task type

        Returns:
            List of chunk dicts with keys:
                - chunk_number: int
                - status: str (pending, completed, failed)
                - Custom fields (workflow-specific)
            Empty list if no chunks exist

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def batch_update_chunk_datasets(
        self,
        session_id: str,
        task_type: str,
        chunk_idx: int,
        updates: dict[str, Any],
    ) -> None:
        """Batch update chunk datasets.

        Used by workers to update multiple fields atomically
        (e.g., transcript + confidence + duration in one operation).

        Args:
            session_id: Session UUID
            task_type: Task type
            chunk_idx: Chunk index (0-based)
            updates: Dict of fields to update

        Raises:
            ValueError: If task or chunk doesn't exist
            IOError: If write operation fails
        """
        pass

    @abstractmethod
    def delete_task(self, session_id: str, task_type: str) -> bool:
        """Delete task and all chunks.

        Args:
            session_id: Session UUID
            task_type: Task type

        Returns:
            True if deletion successful, False if task not found

        Raises:
            IOError: If delete operation fails
        """
        pass

    @abstractmethod
    def get_task_progress(self, session_id: str, task_type: str) -> dict[str, Any]:
        """Get task progress summary.

        Args:
            session_id: Session UUID
            task_type: Task type

        Returns:
            Dict with keys:
                - status: str (pending, in_progress, completed, failed)
                - total_chunks: int
                - processed_chunks: int
                - progress_percent: float (0.0-100.0)
                - estimated_completion: str | None (ISO 8601)

        Raises:
            ValueError: If task doesn't exist
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def get_soap_data(self, session_id: str) -> dict[str, Any] | None:
        """Get SOAP note data for session.

        Args:
            session_id: Session UUID

        Returns:
            SOAP note dict with keys (subjective, objective, assessment, plan)
            or None if SOAP doesn't exist

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def get_diarization_segments(self, session_id: str) -> list[dict[str, Any]]:
        """Get diarization segments for session.

        Args:
            session_id: Session UUID

        Returns:
            List of segment dicts with keys (speaker, text, start, end)
            Empty list if no diarization exists

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def save_soap_data(
        self, session_id: str, soap_data: dict[str, Any], task_type: str = "SOAP_GENERATION"
    ) -> None:
        """Save SOAP note data for session.

        Args:
            session_id: Session UUID
            soap_data: SOAP note dict
            task_type: Task type (default: SOAP_GENERATION)

        Raises:
            IOError: If write operation fails
        """
        pass
