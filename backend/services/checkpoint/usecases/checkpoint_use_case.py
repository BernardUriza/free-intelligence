"""Checkpoint Use Case - Core Business Logic.

Orchestrates the checkpoint creation process:
1. Validate input parameters
2. Retrieve audio chunks from repository
3. Concatenate chunks using audio concatenator
4. Persist the result
5. Update metadata

This use case is framework-agnostic and depends only on ports (interfaces).
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

from backend.logger import get_logger

from ..domain import (
    AudioChunk,
    AudioFormat,
    CheckpointRange,
    CheckpointResult,
    SessionId,
)
from ..ports.audio_concatenator import AudioConcatenatorPort, ConcatenationError
from ..ports.audio_repository import (
    AudioRepositoryPort,
    SessionNotFoundError,
    StorageError,
)

logger = get_logger(__name__)


class CheckpointError(Exception):
    """Base exception for checkpoint use case errors."""

    pass


class NoChunksToProcessError(CheckpointError):
    """Raised when no chunks are available in the checkpoint range."""

    pass


class TooManyChunksError(CheckpointError):
    """Raised when chunk count exceeds safety limit."""

    pass


@dataclass(frozen=True, slots=True)
class CheckpointRequest:
    """Input DTO for checkpoint creation.

    Immutable request object - validates input at construction time.
    """

    session_id: str
    last_checkpoint_idx: int
    new_checkpoint_idx: int
    output_format: AudioFormat = AudioFormat.WEBM

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

    def to_checkpoint_range(self) -> CheckpointRange:
        """Convert to domain CheckpointRange object."""
        return CheckpointRange(
            start_index=self.last_checkpoint_idx,
            end_index=self.new_checkpoint_idx,
        )


class CheckpointUseCase:
    """Use case for creating audio checkpoints.

    Follows Clean Architecture principles:
    - Depends on ports (interfaces), not concrete implementations
    - Contains application-specific business rules
    - Framework-agnostic (no FastAPI, Flask, etc.)

    Thread-safety: Stateless, safe for concurrent use.
    """

    # Safety limit for chunks in a single checkpoint (configurable via env)
    DEFAULT_MAX_CHUNKS = 500

    def __init__(
        self,
        audio_repository: AudioRepositoryPort,
        audio_concatenator: AudioConcatenatorPort,
    ) -> None:
        """Initialize use case with required ports.

        Args:
            audio_repository: Port for audio chunk storage operations
            audio_concatenator: Port for audio concatenation operations
        """
        self._repository = audio_repository
        self._concatenator = audio_concatenator
        self._max_chunks = int(os.getenv("MAX_CONCAT_CHUNKS", str(self.DEFAULT_MAX_CHUNKS)))

    def execute(self, request: CheckpointRequest) -> CheckpointResult:
        """Execute checkpoint creation.

        Args:
            request: Validated checkpoint request

        Returns:
            CheckpointResult with concatenated audio

        Raises:
            NoChunksToProcessError: No chunks in the specified range
            TooManyChunksError: Chunk count exceeds safety limit
            CheckpointError: Other checkpoint failures
        """
        session_id = SessionId(request.session_id)
        checkpoint_range = request.to_checkpoint_range()

        logger.info(
            "CHECKPOINT_STARTED",
            session_id=str(session_id),
            range_start=checkpoint_range.start_index,
            range_end=checkpoint_range.end_index,
        )

        try:
            # Step 1: Verify concatenator is available
            self._verify_concatenator()

            # Step 2: Get chunks in range
            chunks = self._get_chunks(session_id, checkpoint_range)

            # Step 3: Validate chunk count
            self._validate_chunk_count(chunks)

            # Step 4: Get existing audio (from previous checkpoint)
            existing_audio = self._get_existing_audio(session_id)

            # Step 5: Concatenate audio
            concatenated_audio = self._concatenate_audio(
                chunks, existing_audio, request.output_format
            )

            # Step 6: Persist result
            self._persist_result(session_id, concatenated_audio)

            # Step 7: Update metadata
            self._update_metadata(session_id, checkpoint_range.end_index)

            # Build result
            result = CheckpointResult(
                session_id=session_id,
                checkpoint_range=checkpoint_range,
                chunks_concatenated=len(chunks),
                audio_bytes=concatenated_audio,
                output_format=request.output_format,
            )

            logger.info(
                "CHECKPOINT_COMPLETED",
                session_id=str(session_id),
                chunks_concatenated=result.chunks_concatenated,
                output_size_bytes=len(result.audio_bytes),
            )

            return result

        except (NoChunksToProcessError, TooManyChunksError):
            raise
        except SessionNotFoundError as e:
            logger.error("CHECKPOINT_SESSION_NOT_FOUND", session_id=str(session_id))
            raise CheckpointError(f"Session not found: {session_id}") from e
        except ConcatenationError as e:
            logger.error("CHECKPOINT_CONCAT_FAILED", error=str(e))
            raise CheckpointError(f"Audio concatenation failed: {e}") from e
        except StorageError as e:
            logger.error("CHECKPOINT_STORAGE_FAILED", error=str(e))
            raise CheckpointError(f"Storage operation failed: {e}") from e
        except Exception as e:
            logger.error("CHECKPOINT_UNEXPECTED_ERROR", error=str(e), exc_info=True)
            raise CheckpointError(f"Unexpected error: {e}") from e

    def _verify_concatenator(self) -> None:
        """Verify that audio concatenator is available."""
        if not self._concatenator.is_available():
            raise CheckpointError("Audio concatenator not available. Ensure FFmpeg is installed.")

    def _get_chunks(
        self, session_id: SessionId, checkpoint_range: CheckpointRange
    ) -> Sequence[AudioChunk]:
        """Retrieve chunks from repository."""
        # First, discover available chunks
        available_indices = self._repository.get_available_chunk_indices(session_id)

        logger.debug(
            "CHECKPOINT_AVAILABLE_CHUNKS",
            session_id=str(session_id),
            available_count=len(available_indices),
            first_10=list(available_indices[:10]),
        )

        # Get chunks in the checkpoint range
        chunks = self._repository.get_chunks_in_range(session_id, checkpoint_range)

        if not chunks:
            logger.warning(
                "CHECKPOINT_NO_CHUNKS",
                session_id=str(session_id),
                range_start=checkpoint_range.start_index,
                range_end=checkpoint_range.end_index,
            )
            raise NoChunksToProcessError(
                f"No chunks found in range ({checkpoint_range.start_index}, {checkpoint_range.end_index}]"
            )

        return chunks

    def _validate_chunk_count(self, chunks: Sequence[AudioChunk]) -> None:
        """Validate chunk count is within safety limits."""
        if len(chunks) > self._max_chunks:
            logger.error(
                "CHECKPOINT_TOO_MANY_CHUNKS",
                chunk_count=len(chunks),
                max_allowed=self._max_chunks,
            )
            raise TooManyChunksError(
                f"Too many chunks ({len(chunks)}) exceeds limit ({self._max_chunks}). "
                f"Increase MAX_CONCAT_CHUNKS if necessary."
            )

    def _get_existing_audio(self, session_id: SessionId) -> bytes | None:
        """Get existing full audio from previous checkpoint."""
        existing = self._repository.get_existing_full_audio(session_id)
        if existing:
            logger.debug(
                "CHECKPOINT_EXISTING_AUDIO",
                session_id=str(session_id),
                size_bytes=len(existing),
            )
        return existing

    def _concatenate_audio(
        self,
        chunks: Sequence[AudioChunk],
        existing_audio: bytes | None,
        output_format: AudioFormat,
    ) -> bytes:
        """Concatenate chunks using the audio concatenator port."""
        return self._concatenator.concatenate(chunks, existing_audio, output_format)

    def _persist_result(self, session_id: SessionId, audio_bytes: bytes) -> None:
        """Persist concatenated audio to repository."""
        self._repository.save_full_audio(session_id, audio_bytes)

    def _update_metadata(self, session_id: SessionId, checkpoint_idx: int) -> None:
        """Update checkpoint metadata in repository."""
        self._repository.update_checkpoint_metadata(session_id, checkpoint_idx)
