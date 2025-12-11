"""Audio Repository Port - Secondary/Driven Port.

Defines the contract for audio chunk storage operations.
The application core depends on this abstraction, not concrete implementations.

Implementations:
- HDF5AudioRepository (production)
- InMemoryAudioRepository (testing)
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import Protocol

from ..domain import AudioChunk, CheckpointRange, SessionId


class AudioRepositoryPort(Protocol):
    """Abstract interface for audio chunk storage.

    This is a Secondary Port (Driven) - the application uses this
    to retrieve and store audio data.

    Implementations must be stateless and thread-safe.
    """

    @abstractmethod
    def get_available_chunk_indices(self, session_id: SessionId) -> Sequence[int]:
        """Get all available chunk indices for a session.

        Args:
            session_id: Session identifier

        Returns:
            Sorted sequence of chunk indices (may have gaps)

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        ...

    @abstractmethod
    def get_chunks_in_range(
        self, session_id: SessionId, range_: CheckpointRange
    ) -> Sequence[AudioChunk]:
        """Get audio chunks within the specified range.

        Args:
            session_id: Session identifier
            range_: Checkpoint range (exclusive start, inclusive end)

        Returns:
            Sequence of AudioChunk objects, sorted by index

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        ...

    @abstractmethod
    def get_existing_full_audio(self, session_id: SessionId) -> bytes | None:
        """Get existing concatenated audio from previous checkpoint.

        Args:
            session_id: Session identifier

        Returns:
            Audio bytes if exists, None otherwise
        """
        ...

    @abstractmethod
    def save_full_audio(self, session_id: SessionId, audio_bytes: bytes) -> None:
        """Save concatenated audio to storage.

        Args:
            session_id: Session identifier
            audio_bytes: Concatenated audio data

        Raises:
            StorageError: If save fails
        """
        ...

    @abstractmethod
    def update_checkpoint_metadata(self, session_id: SessionId, checkpoint_idx: int) -> None:
        """Update session metadata with new checkpoint index.

        Args:
            session_id: Session identifier
            checkpoint_idx: New checkpoint index

        Raises:
            StorageError: If update fails
        """
        ...


class SessionNotFoundError(Exception):
    """Raised when session doesn't exist in storage."""

    def __init__(self, session_id: SessionId) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class StorageError(Exception):
    """Raised when storage operation fails."""

    pass
