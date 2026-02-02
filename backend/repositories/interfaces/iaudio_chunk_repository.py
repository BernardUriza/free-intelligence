"""Audio chunk repository interface.

Decouples transcription service from HDF5 implementation.
Enables future migrations to PostgreSQL, S3, or other backends.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IAudioChunkRepository(ABC):
    """Audio chunk storage abstraction.

    Responsibilities:
    - Store audio chunks with metadata
    - Retrieve chunks by session and chunk number
    - List all chunks for a session
    - Update chunk metadata (transcript, confidence, etc.)

    Clean Architecture Benefits:
    - Business logic doesn't know about HDF5
    - Easy to mock for testing
    - Can swap storage backend without changing services
    """

    @abstractmethod
    def save_chunk(
        self,
        session_id: str,
        chunk_number: int,
        audio_data: bytes,
        metadata: dict[str, Any],
    ) -> str:
        """Save audio chunk with metadata.

        Args:
            session_id: Session UUID
            chunk_number: Sequential chunk index (0-based)
            audio_data: Raw audio bytes
            metadata: Chunk metadata (timestamps, hash, etc.)

        Returns:
            Chunk ID (usually f"{session_id}_{chunk_number}")

        Raises:
            ValueError: If chunk_number < 0 or audio_data is empty
            IOError: If storage operation fails
        """
        pass

    @abstractmethod
    def get_chunk(self, session_id: str, chunk_number: int) -> dict[str, Any] | None:
        """Retrieve chunk with all metadata.

        Args:
            session_id: Session UUID
            chunk_number: Chunk index

        Returns:
            Dict with keys:
                - chunk_number: int
                - audio_data: bytes (optional, may be excluded for performance)
                - transcript: str
                - timestamp_start: float
                - timestamp_end: float
                - confidence: float
                - audio_hash: str
                - status: str (pending, completed, failed)
            None if chunk doesn't exist

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def list_chunks(self, session_id: str) -> list[dict[str, Any]]:
        """List all chunks for session.

        Args:
            session_id: Session UUID

        Returns:
            List of chunk dicts (see get_chunk for structure)
            Empty list if no chunks exist

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def update_chunk_metadata(
        self,
        session_id: str,
        chunk_number: int,
        updates: dict[str, Any],
    ) -> bool:
        """Update chunk metadata (e.g., after transcription completes).

        Args:
            session_id: Session UUID
            chunk_number: Chunk index
            updates: Dict of fields to update (transcript, confidence, status, etc.)

        Returns:
            True if update successful, False if chunk not found

        Raises:
            IOError: If update operation fails
        """
        pass

    @abstractmethod
    def delete_chunk(self, session_id: str, chunk_number: int) -> bool:
        """Delete audio chunk.

        Args:
            session_id: Session UUID
            chunk_number: Chunk index

        Returns:
            True if deletion successful, False if chunk not found

        Raises:
            IOError: If delete operation fails
        """
        pass

    @abstractmethod
    def get_chunk_count(self, session_id: str) -> int:
        """Get total chunk count for session.

        Args:
            session_id: Session UUID

        Returns:
            Number of chunks (0 if session doesn't exist)

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def get_audio_data(self, session_id: str, chunk_number: int) -> bytes | None:
        """Retrieve raw audio bytes for a specific chunk.

        Separate from get_chunk() for performance - audio can be very large.

        Args:
            session_id: Session UUID
            chunk_number: Chunk index

        Returns:
            Raw audio bytes if chunk exists, None otherwise

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def get_audio_data_range(
        self,
        session_id: str,
        start_chunk: int,
        end_chunk: int,
    ) -> list[bytes]:
        """Retrieve audio bytes for a range of chunks.

        Optimized batch retrieval for checkpoint concatenation.

        Args:
            session_id: Session UUID
            start_chunk: First chunk index (inclusive)
            end_chunk: Last chunk index (inclusive)

        Returns:
            List of audio bytes in chunk order

        Raises:
            ValueError: If start_chunk > end_chunk
            IOError: If read operation fails
        """
        pass
