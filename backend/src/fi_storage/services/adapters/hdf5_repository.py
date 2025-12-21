"""HDF5 Audio Repository - Concrete Implementation.

Implements AudioRepositoryPort using HDF5 for storage.
Uses session-specific HDF5 files (not global corpus.h5).

Thread-safety: Uses session locks from backend.src.fi_storage.infrastructure.hdf5.session_locks
"""

from __future__ import annotations

import h5py
import numpy as np
from collections.abc import Sequence
from datetime import UTC

from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_storage.infrastructure.hdf5.session_h5_manager import (
    get_session_h5_path,
)

from ..domain import AudioChunk, AudioFormat, CheckpointRange, SessionId
from ..ports.audio_repository import (
    AudioRepositoryPort,
    SessionNotFoundError,
    StorageError,
)

logger = get_logger(__name__)


class HDF5AudioRepository(AudioRepositoryPort):
    """HDF5-based audio repository implementation.

    Reads/writes audio chunks from session-specific HDF5 files.
    Path pattern: storage/sessions/{session_id}.h5

    HDF5 Structure:
        /sessions/{session_id}/tasks/TRANSCRIPTION/chunks/chunk_{N}/audio.webm
        /sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm
        /sessions/{session_id}/tasks/TRANSCRIPTION/metadata
    """

    TASK_TYPE = "TRANSCRIPTION"
    AUDIO_FILENAME = "audio.webm"
    FULL_AUDIO_FILENAME = "full_audio.webm"

    def get_available_chunk_indices(self, session_id: SessionId) -> Sequence[int]:
        """Get all chunk indices from HDF5."""
        h5_path = get_session_h5_path(str(session_id))

        if not h5_path.exists():
            logger.warning("SESSION_H5_NOT_FOUND", session_id=str(session_id))
            raise SessionNotFoundError(session_id)

        chunk_indices: list[int] = []

        with h5py.File(h5_path, "r") as f:
            chunks_group_path = f"/sessions/{session_id}/tasks/{self.TASK_TYPE}/chunks"

            if chunks_group_path not in f:
                logger.debug("NO_CHUNKS_GROUP", session_id=str(session_id))
                return []

            chunks_group = f[chunks_group_path]

            for key in chunks_group:
                if key.startswith("chunk_"):
                    try:
                        chunk_num = int(key.split("_")[1])
                        chunk_indices.append(chunk_num)
                    except (ValueError, IndexError):
                        logger.warning("INVALID_CHUNK_KEY", key=key)
                        continue

        chunk_indices.sort()

        logger.debug(
            "CHUNKS_DISCOVERED",
            session_id=str(session_id),
            count=len(chunk_indices),
            indices=chunk_indices[:10],  # Log first 10
        )

        return chunk_indices

    def get_chunks_in_range(
        self, session_id: SessionId, range_: CheckpointRange
    ) -> Sequence[AudioChunk]:
        """Get audio chunks within the checkpoint range."""
        h5_path = get_session_h5_path(str(session_id))

        if not h5_path.exists():
            raise SessionNotFoundError(session_id)

        chunks: list[AudioChunk] = []

        with h5py.File(h5_path, "r") as f:
            available_indices = self.get_available_chunk_indices(session_id)

            for chunk_idx in available_indices:
                if not range_.contains(chunk_idx):
                    continue

                chunk_path = (
                    f"/sessions/{session_id}/tasks/{self.TASK_TYPE}/chunks/chunk_{chunk_idx}"
                )

                if chunk_path not in f:
                    logger.warning("CHUNK_PATH_MISSING", chunk_idx=chunk_idx)
                    continue

                chunk_group = f[chunk_path]

                # Try both "audio" and "audio.webm" keys
                audio_key = None
                for key in ["audio", "audio.webm", self.AUDIO_FILENAME]:
                    if key in chunk_group:
                        audio_key = key
                        break

                if audio_key is None:
                    logger.warning("CHUNK_NO_AUDIO", chunk_idx=chunk_idx)
                    continue

                audio_data = chunk_group[audio_key][()]
                audio_bytes = self._to_bytes(audio_data)

                if len(audio_bytes) == 0:
                    logger.warning("CHUNK_AUDIO_EMPTY", chunk_idx=chunk_idx)
                    continue

                # Detect format from content
                audio_format = self._detect_format(audio_bytes)

                try:
                    chunk = AudioChunk(
                        index=chunk_idx,
                        audio_bytes=audio_bytes,
                        format=audio_format,
                    )
                    chunks.append(chunk)
                except ValueError as e:
                    logger.warning("INVALID_CHUNK", chunk_idx=chunk_idx, error=str(e))
                    continue

        logger.info(
            "CHUNKS_LOADED",
            session_id=str(session_id),
            range_start=range_.start_index,
            range_end=range_.end_index,
            chunks_found=len(chunks),
        )

        return sorted(chunks, key=lambda c: c.index)

    def get_existing_full_audio(self, session_id: SessionId) -> bytes | None:
        """Get existing concatenated audio from previous checkpoint."""
        h5_path = get_session_h5_path(str(session_id))

        if not h5_path.exists():
            return None

        with h5py.File(h5_path, "r") as f:
            full_audio_path = (
                f"/sessions/{session_id}/tasks/{self.TASK_TYPE}/{self.FULL_AUDIO_FILENAME}"
            )

            if full_audio_path not in f:
                return None

            audio_data = f[full_audio_path][()]
            audio_bytes = self._to_bytes(audio_data)

            if len(audio_bytes) == 0:
                return None

            logger.debug(
                "EXISTING_AUDIO_FOUND",
                session_id=str(session_id),
                size_bytes=len(audio_bytes),
            )

            return audio_bytes

    def save_full_audio(self, session_id: SessionId, audio_bytes: bytes) -> None:
        """Save concatenated audio to HDF5."""
        h5_path = get_session_h5_path(str(session_id))

        if not h5_path.exists():
            raise StorageError(f"Session H5 file not found: {h5_path}")

        try:
            with h5py.File(h5_path, "a") as f:
                full_audio_path = (
                    f"/sessions/{session_id}/tasks/{self.TASK_TYPE}/{self.FULL_AUDIO_FILENAME}"
                )

                # Delete existing if present
                if full_audio_path in f:
                    del f[full_audio_path]

                # Create parent groups if needed
                parent_path = f"/sessions/{session_id}/tasks/{self.TASK_TYPE}"
                if parent_path not in f:
                    f.create_group(parent_path)

                # Save as binary dataset
                f.create_dataset(
                    full_audio_path,
                    data=np.frombuffer(audio_bytes, dtype=np.uint8),
                )

            logger.info(
                "FULL_AUDIO_SAVED",
                session_id=str(session_id),
                size_bytes=len(audio_bytes),
            )

        except Exception as e:
            logger.error("FULL_AUDIO_SAVE_FAILED", error=str(e))
            raise StorageError(f"Failed to save full audio: {e}") from e

    def update_checkpoint_metadata(self, session_id: SessionId, checkpoint_idx: int) -> None:
        """Update task metadata with new checkpoint index."""
        from datetime import datetime

        h5_path = get_session_h5_path(str(session_id))

        if not h5_path.exists():
            raise StorageError(f"Session H5 file not found: {h5_path}")

        try:
            with h5py.File(h5_path, "a") as f:
                metadata_path = f"/sessions/{session_id}/tasks/{self.TASK_TYPE}/metadata"

                if metadata_path in f:
                    metadata_group = f[metadata_path]
                    metadata_group.attrs["last_checkpoint_idx"] = checkpoint_idx
                    metadata_group.attrs["last_checkpoint_at"] = datetime.now(UTC).isoformat()

            logger.info(
                "CHECKPOINT_METADATA_UPDATED",
                session_id=str(session_id),
                checkpoint_idx=checkpoint_idx,
            )

        except Exception as e:
            logger.error("METADATA_UPDATE_FAILED", error=str(e))
            raise StorageError(f"Failed to update metadata: {e}") from e

    @staticmethod
    def _to_bytes(data) -> bytes:
        """Convert HDF5 data to bytes."""
        if hasattr(data, "tobytes"):
            return data.tobytes()
        if isinstance(data, bytes):
            return data
        return bytes(data)

    @staticmethod
    def _detect_format(audio_bytes: bytes) -> AudioFormat:
        """Detect audio format from magic bytes."""
        if len(audio_bytes) < 4:
            return AudioFormat.WAV  # Default

        header = audio_bytes[:4]

        if header == b"RIFF":
            return AudioFormat.WAV
        if header == bytes([0x1A, 0x45, 0xDF, 0xA3]):
            return AudioFormat.WEBM
        if header == b"OggS":
            return AudioFormat.OGG
        if header[:3] == b"ID3" or (header[0] == 0xFF and header[1] in (0xFA, 0xFB)):
            return AudioFormat.MP3

        return AudioFormat.WAV  # Default fallback
