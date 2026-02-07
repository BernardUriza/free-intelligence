"""Interface for corpus repository operations.

Defines the contract for corpus data access. Implementations handle
HDF5 operations for corpus documents, chunks, sessions, and metadata.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3A - Infrastructure Extraction
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.utils.common.types.type_defs import DiarizationChunkDict


class ICorpusRepository(ABC):
    """Interface for corpus document and session management.

    Provides abstraction over HDF5 corpus storage, enabling:
    - Document CRUD operations
    - Chunk management (diarization)
    - Session metadata and audio access
    - Workflow state tracking
    """

    # ========================================================================
    # Document Operations
    # ========================================================================

    @abstractmethod
    def create(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any | None] | None = None,
    ) -> str:
        """Create new corpus document.

        Args:
            document_id: Unique document identifier
            content: Document content
            metadata: Optional metadata (author, source, tags, etc.)

        Returns:
            Document ID

        Raises:
            ValueError: If document_id is empty or content is invalid
            IOError: If HDF5 operation fails
        """
        pass

    @abstractmethod
    def read(self, document_id: str) -> dict[str, Any | None] | None:
        """Read corpus document.

        Args:
            document_id: Document identifier

        Returns:
            Document data with metadata, or None if not found
        """
        pass

    @abstractmethod
    def update(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any | None] | None = None,
    ) -> bool:
        """Update corpus document (enforces append-only by creating new version).

        Args:
            document_id: Document identifier
            content: New content
            metadata: Updated metadata

        Returns:
            True if update successful
        """
        pass

    @abstractmethod
    def delete(self, document_id: str) -> bool:
        """Delete corpus document (marks as deleted in append-only mode).

        Args:
            document_id: Document identifier

        Returns:
            True if deletion successful
        """
        pass

    @abstractmethod
    def list_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        """List all documents in corpus.

        Args:
            limit: Maximum documents to return

        Returns:
            List of documents (metadata only)
        """
        pass

    # ========================================================================
    # Chunk Operations
    # ========================================================================

    @abstractmethod
    def add_chunk(self, chunk: DiarizationChunkDict, document_id: str) -> bool:
        """Add diarization chunk to document.

        Args:
            chunk: Chunk data (from diarization)
            document_id: Parent document ID

        Returns:
            True if chunk added successfully
        """
        pass

    @abstractmethod
    def get_chunks(self, document_id: str) -> list[DiarizationChunkDict]:
        """Get all chunks for document.

        Args:
            document_id: Document identifier

        Returns:
            List of chunks
        """
        pass

    # ========================================================================
    # Session Operations
    # ========================================================================

    @abstractmethod
    def get_session_metadata(self, session_id: str) -> dict[str, Any] | None:
        """Get session metadata from corpus.

        Args:
            session_id: Session identifier

        Returns:
            Session metadata dict or None if not found
        """
        pass

    @abstractmethod
    def update_session_metadata(self, session_id: str, updates: dict[str, Any]) -> bool:
        """Update session metadata in corpus (merge with existing).

        Args:
            session_id: Session identifier
            updates: Dictionary of metadata fields to update/add

        Returns:
            True if update successful, False otherwise
        """
        pass

    @abstractmethod
    def get_session_audio(
        self, session_id: str, audio_type: str = "full_audio.webm"
    ) -> bytes | None:
        """Get audio bytes from session.

        Args:
            session_id: Session identifier
            audio_type: Audio dataset name (default: full_audio.webm)

        Returns:
            Audio bytes or None if not found
        """
        pass

    @abstractmethod
    def get_session_transcription_chunks(
        self, session_id: str, task_type: str = "TRANSCRIPTION"
    ) -> list[dict[str, Any]]:
        """Get transcription chunks from session.

        Args:
            session_id: Session identifier
            task_type: Task type (default: TRANSCRIPTION)

        Returns:
            List of chunk dicts with metadata
        """
        pass

    @abstractmethod
    def get_session_workflow_state(self, session_id: str) -> dict[str, Any] | None:
        """Get workflow state from session.

        Args:
            session_id: Session identifier

        Returns:
            Workflow state dict or None if not found
        """
        pass

    @abstractmethod
    def list_all_sessions(
        self, limit: int | None = None, include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        """List all sessions in corpus.

        Args:
            limit: Maximum sessions to return
            include_deleted: Include deleted sessions

        Returns:
            List of sessions with metadata
        """
        pass

    @abstractmethod
    def get_session_dataset(self, session_id: str, dataset_path: str) -> bytes | None:
        """Get raw bytes from session dataset (generic accessor).

        Args:
            session_id: Session identifier
            dataset_path: Relative path to dataset (e.g., "tasks/TRANSCRIPTION/webspeech_final")

        Returns:
            Dataset bytes or None if not found
        """
        pass

    @abstractmethod
    def list_session_tasks(self, session_id: str) -> list[str]:
        """List all task types in session.

        Args:
            session_id: Session identifier

        Returns:
            List of task type names (e.g., ["TRANSCRIPTION", "DIARIZATION"])
        """
        pass

    @abstractmethod
    def list_all_sessions_with_metadata(
        self, limit: int = 20, offset: int = 0, clinic_id: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """List all sessions with detailed metadata (for sessions list endpoint).

        Reads directly from HDF5 task-based schema. Optimized for fast listing
        without Timeline API overhead.

        Multi-Tenancy Support:
        - If clinic_id provided: Returns ONLY sessions from that clinic
        - If clinic_id is None: Returns ALL sessions (SUPERADMIN mode)

        Args:
            limit: Maximum number of sessions to return (default 20)
            offset: Number of sessions to skip (default 0)
            clinic_id: Filter sessions by clinic_id (None = all clinics, for SUPERADMIN)

        Returns:
            Tuple of (sessions list, total count)
        """
        pass
