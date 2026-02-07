"""Checkpoint service - Audio concatenation for incremental session saves.

This service concatenates audio chunks at checkpoint boundaries (pause events).
It uses the IAudioChunkRepository to retrieve raw audio bytes and concatenates
them into a single audio file.

Flow:
1. Frontend pauses recording
2. POST /sessions/{session_id}/checkpoint { last_chunk_idx: N }
3. This service concatenates chunks [last_checkpoint+1, N]
4. Returns concatenated bytes to endpoint for storage

Clean Architecture:
- Uses IAudioChunkRepository (not HDF5 directly)
- Pure business logic, no framework dependencies
- Easy to test with mock repositories

Author: Bernard Uriza Orozco
Created: 2025-11-14
Updated: 2026-02-02 (Implemented from stub)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.utils.common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.repositories.interfaces.iaudio_chunk_repository import (
        IAudioChunkRepository,
    )

logger = get_logger(__name__)

# Safety limit to prevent memory issues
MAX_CHUNKS_PER_CHECKPOINT = 100


class CheckpointError(Exception):
    """Base exception for checkpoint use case errors."""

    pass


class NoChunksToProcessError(CheckpointError):
    """Raised when no chunks are available in the checkpoint range."""

    pass


class TooManyChunksError(CheckpointError):
    """Raised when chunk count exceeds safety limit."""

    pass


class AudioConcatenationError(CheckpointError):
    """Raised when audio concatenation fails."""

    pass


@dataclass(frozen=True, slots=True)
class CheckpointRequest:
    """Input DTO for checkpoint creation.

    Validates that the checkpoint range is valid.
    """

    session_id: str
    last_checkpoint_idx: int
    new_checkpoint_idx: int

    def __post_init__(self) -> None:
        """Validate request parameters."""
        if not self.session_id or len(self.session_id) < 5:
            raise ValueError("session_id must be at least 5 characters")
        if self.last_checkpoint_idx < -1:
            raise ValueError("last_checkpoint_idx must be >= -1")
        if self.new_checkpoint_idx < 0:
            raise ValueError("new_checkpoint_idx must be >= 0")
        if self.new_checkpoint_idx <= self.last_checkpoint_idx:
            raise ValueError("new_checkpoint_idx must be > last_checkpoint_idx")

    @property
    def chunk_range(self) -> tuple[int, int]:
        """Return (start_chunk, end_chunk) inclusive range."""
        return (self.last_checkpoint_idx + 1, self.new_checkpoint_idx)

    @property
    def expected_chunk_count(self) -> int:
        """Expected number of chunks in range."""
        return self.new_checkpoint_idx - self.last_checkpoint_idx


@dataclass
class CheckpointResult:
    """Result of checkpoint creation."""

    chunks_concatenated: int
    audio_bytes: bytes
    start_chunk: int
    end_chunk: int


class CheckpointService:
    """Service for creating audio checkpoints.

    Concatenates audio chunks in a range into a single byte stream.
    Uses IAudioChunkRepository for storage abstraction.
    """

    def __init__(self, audio_repository: IAudioChunkRepository) -> None:
        """Initialize with injected audio repository.

        Args:
            audio_repository: Repository for audio chunk access
        """
        self._audio_repo = audio_repository

    def execute(self, request: CheckpointRequest) -> CheckpointResult:
        """Execute checkpoint - concatenate audio chunks.

        Args:
            request: CheckpointRequest with session_id and chunk range

        Returns:
            CheckpointResult with concatenated audio bytes

        Raises:
            NoChunksToProcessError: If no chunks found in range
            TooManyChunksError: If chunk count exceeds safety limit
            AudioConcatenationError: If concatenation fails
        """
        start_chunk, end_chunk = request.chunk_range
        expected_count = request.expected_chunk_count

        logger.info(
            "CHECKPOINT_EXECUTE_START",
            session_id=request.session_id,
            start_chunk=start_chunk,
            end_chunk=end_chunk,
            expected_count=expected_count,
        )

        # Safety check
        if expected_count > MAX_CHUNKS_PER_CHECKPOINT:
            raise TooManyChunksError(
                f"Chunk count {expected_count} exceeds limit {MAX_CHUNKS_PER_CHECKPOINT}. "
                f"Process in smaller batches."
            )

        # Retrieve audio bytes in batch
        try:
            audio_chunks = self._audio_repo.get_audio_data_range(
                session_id=request.session_id,
                start_chunk=start_chunk,
                end_chunk=end_chunk,
            )
        except Exception as e:
            logger.error(
                "CHECKPOINT_RETRIEVE_FAILED",
                session_id=request.session_id,
                error=str(e),
            )
            raise AudioConcatenationError(f"Failed to retrieve chunks: {e}") from e

        if not audio_chunks:
            raise NoChunksToProcessError(
                f"No chunks found in range [{start_chunk}, {end_chunk}]"
            )

        # Concatenate audio bytes
        try:
            concatenated = b"".join(audio_chunks)
        except Exception as e:
            logger.error(
                "CHECKPOINT_CONCATENATE_FAILED",
                session_id=request.session_id,
                chunk_count=len(audio_chunks),
                error=str(e),
            )
            raise AudioConcatenationError(f"Concatenation failed: {e}") from e

        logger.info(
            "CHECKPOINT_EXECUTE_COMPLETE",
            session_id=request.session_id,
            chunks_concatenated=len(audio_chunks),
            total_bytes=len(concatenated),
        )

        return CheckpointResult(
            chunks_concatenated=len(audio_chunks),
            audio_bytes=concatenated,
            start_chunk=start_chunk,
            end_chunk=end_chunk,
        )


def create_checkpoint_service(
    audio_repository: IAudioChunkRepository | None = None,
) -> CheckpointService:
    """Factory function for checkpoint service.

    Args:
        audio_repository: Optional pre-configured repository.
            If None, creates default HDF5AudioChunkRepository.

    Returns:
        Configured CheckpointService instance
    """
    if audio_repository is None:
        # Lazy import to avoid circular dependencies
        from backend.repositories.hdf5_audio_chunk_repository import (
            HDF5AudioChunkRepository,
        )
        from backend.config import get_settings

        settings = get_settings()
        audio_repository = HDF5AudioChunkRepository(settings.hdf5_corpus_path)

    return CheckpointService(audio_repository)
