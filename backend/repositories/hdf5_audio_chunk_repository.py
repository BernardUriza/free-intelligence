"""HDF5 implementation of IAudioChunkRepository.

Stores audio chunks in HDF5 datasets with metadata.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from pathlib import Path
from typing import Any, Dict, List

import h5py
from backend.repositories.base_repository import BaseRepository
from backend.repositories.interfaces import IAudioChunkRepository
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class HDF5AudioChunkRepository(BaseRepository[Dict], IAudioChunkRepository):
    """HDF5 implementation of audio chunk storage.

    Storage Structure:
        sessions/{session_id}/transcription/chunks/{chunk_number}/
            - audio (dataset): Raw audio bytes
            - metadata (attrs): Dict with transcript, timestamps, etc.

    Thread Safety:
        - Uses file locking via portalocker (cross-platform)
        - Safe for concurrent reads, exclusive writes
    """

    def __init__(self, h5_file_path: str | Path):
        """Initialize HDF5 audio chunk repository.

        Args:
            h5_file_path: Path to HDF5 database file
        """
        super().__init__(h5_file_path)

    def save_chunk(
        self,
        session_id: str,
        chunk_number: int,
        audio_data: bytes,
        metadata: Dict[str, Any],
    ) -> str:
        """Save audio chunk with metadata.

        Args:
            session_id: Session UUID
            chunk_number: Chunk index (0-based)
            audio_data: Raw audio bytes
            metadata: Chunk metadata (timestamp_start, timestamp_end, audio_hash, etc.)

        Returns:
            Chunk ID (f"{session_id}_{chunk_number}")

        Raises:
            ValueError: If chunk_number < 0 or audio_data is empty
            IOError: If HDF5 write fails
        """
        if chunk_number < 0:
            raise ValueError(f"chunk_number must be >= 0, got {chunk_number}")

        if not audio_data or len(audio_data) == 0:
            raise ValueError("audio_data cannot be empty")

        chunk_id = f"{session_id}_{chunk_number}"
        chunk_path = f"sessions/{session_id}/transcription/chunks/{chunk_number}"

        with self._open_file("a") as f:
            # Create chunk group if it doesn't exist
            if chunk_path not in f:
                chunk_group = f.create_group(chunk_path)
            else:
                chunk_group = f[chunk_path]

            # Save audio data
            if "audio" in chunk_group:
                del chunk_group["audio"]  # Replace if exists
            chunk_group.create_dataset("audio", data=audio_data)

            # Save metadata as attributes
            for key, value in metadata.items():
                chunk_group.attrs[key] = value

        self._log_operation("save_chunk", entity_id=chunk_id, status="success")
        logger.info(
            "AUDIO_CHUNK_SAVED",
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=len(audio_data),
            metadata_keys=list(metadata.keys()),
        )

        return chunk_id

    def get_chunk(self, session_id: str, chunk_number: int) -> Dict[str, Any] | None:
        """Retrieve chunk with metadata (excludes audio data for performance).

        Args:
            session_id: Session UUID
            chunk_number: Chunk index

        Returns:
            Dict with metadata (no audio_data field for performance)
            None if chunk doesn't exist
        """
        chunk_path = f"sessions/{session_id}/transcription/chunks/{chunk_number}"

        with self._open_file("r") as f:
            if chunk_path not in f:
                return None

            chunk_group = f[chunk_path]

            # Extract metadata from attributes
            metadata = dict(chunk_group.attrs.items())
            metadata["chunk_number"] = chunk_number
            metadata["session_id"] = session_id

            # Don't load audio data by default (can be GBs)
            # metadata["audio_data"] = bytes(chunk_group["audio"][:])

        return metadata

    def list_chunks(self, session_id: str) -> List[Dict[str, Any]]:
        """List all chunks for session.

        Args:
            session_id: Session UUID

        Returns:
            List of chunk dicts (sorted by chunk_number)
        """
        chunks_path = f"sessions/{session_id}/transcription/chunks"

        with self._open_file("r") as f:
            if chunks_path not in f:
                return []

            chunks_group = f[chunks_path]
            chunk_numbers = sorted([int(k) for k in chunks_group.keys()])

            chunks = []
            for chunk_num in chunk_numbers:
                chunk = self.get_chunk(session_id, chunk_num)
                if chunk:
                    chunks.append(chunk)

        return chunks

    def update_chunk_metadata(
        self,
        session_id: str,
        chunk_number: int,
        updates: Dict[str, Any],
    ) -> bool:
        """Update chunk metadata.

        Args:
            session_id: Session UUID
            chunk_number: Chunk index
            updates: Dict of fields to update

        Returns:
            True if update successful, False if chunk not found
        """
        chunk_path = f"sessions/{session_id}/transcription/chunks/{chunk_number}"

        with self._open_file("a") as f:
            if chunk_path not in f:
                return False

            chunk_group = f[chunk_path]

            # Update attributes
            for key, value in updates.items():
                chunk_group.attrs[key] = value

        self._log_operation(
            "update_chunk_metadata",
            entity_id=f"{session_id}_{chunk_number}",
            status="success",
        )

        return True

    def delete_chunk(self, session_id: str, chunk_number: int) -> bool:
        """Delete audio chunk.

        Args:
            session_id: Session UUID
            chunk_number: Chunk index

        Returns:
            True if deletion successful, False if chunk not found
        """
        chunk_path = f"sessions/{session_id}/transcription/chunks/{chunk_number}"

        with self._open_file("a") as f:
            if chunk_path not in f:
                return False

            del f[chunk_path]

        self._log_operation(
            "delete_chunk",
            entity_id=f"{session_id}_{chunk_number}",
            status="success",
        )

        return True

    def get_chunk_count(self, session_id: str) -> int:
        """Get total chunk count for session.

        Args:
            session_id: Session UUID

        Returns:
            Number of chunks
        """
        chunks_path = f"sessions/{session_id}/transcription/chunks"

        with self._open_file("r") as f:
            if chunks_path not in f:
                return 0

            return len(f[chunks_path].keys())

    # BaseRepository abstract methods (not used for audio chunks)
    def create(self, entity: Dict, **kwargs: Any) -> str:
        """Not used - use save_chunk instead."""
        raise NotImplementedError("Use save_chunk() instead")

    def read(self, entity_id: str) -> Dict | None:
        """Not used - use get_chunk instead."""
        raise NotImplementedError("Use get_chunk() instead")

    def update(self, entity_id: str, entity: Dict) -> bool:
        """Not used - use update_chunk_metadata instead."""
        raise NotImplementedError("Use update_chunk_metadata() instead")

    def delete(self, entity_id: str) -> bool:
        """Not used - use delete_chunk instead."""
        raise NotImplementedError("Use delete_chunk() instead")

    def list_all(self, limit: int | None = None) -> list[Dict]:
        """Not used - use list_chunks instead."""
        raise NotImplementedError("Use list_chunks() instead")

    def get_audio_data(self, session_id: str, chunk_number: int) -> bytes | None:
        """Retrieve raw audio bytes for a specific chunk.

        Args:
            session_id: Session UUID
            chunk_number: Chunk index

        Returns:
            Raw audio bytes if chunk exists, None otherwise
        """
        chunk_path = f"sessions/{session_id}/transcription/chunks/{chunk_number}"

        with self._open_file("r") as f:
            if chunk_path not in f:
                return None

            chunk_group = f[chunk_path]
            if "audio" not in chunk_group:
                return None

            return bytes(chunk_group["audio"][:])

    def get_audio_data_range(
        self,
        session_id: str,
        start_chunk: int,
        end_chunk: int,
    ) -> list[bytes]:
        """Retrieve audio bytes for a range of chunks.

        Optimized batch retrieval - single file open for all chunks.

        Args:
            session_id: Session UUID
            start_chunk: First chunk index (inclusive)
            end_chunk: Last chunk index (inclusive)

        Returns:
            List of audio bytes in chunk order (skips missing chunks)

        Raises:
            ValueError: If start_chunk > end_chunk
        """
        if start_chunk > end_chunk:
            raise ValueError(f"start_chunk ({start_chunk}) > end_chunk ({end_chunk})")

        chunks_path = f"sessions/{session_id}/transcription/chunks"
        audio_list: list[bytes] = []

        with self._open_file("r") as f:
            if chunks_path not in f:
                return audio_list

            for chunk_num in range(start_chunk, end_chunk + 1):
                chunk_path = f"{chunks_path}/{chunk_num}"
                if chunk_path in f and "audio" in f[chunk_path]:
                    audio_list.append(bytes(f[chunk_path]["audio"][:]))

        logger.debug(
            "AUDIO_RANGE_RETRIEVED",
            session_id=session_id,
            start_chunk=start_chunk,
            end_chunk=end_chunk,
            chunks_found=len(audio_list),
        )

        return audio_list
