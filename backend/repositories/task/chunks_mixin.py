"""Task Chunks Mixin - Audio chunk management.

Handles chunk lifecycle:
- Get chunks for a task
- Batch update chunk datasets
- Get audio bytes from chunks

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor from monolithic task_repository.py)
"""

from __future__ import annotations

import time
from typing import Any

import h5py

from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class TaskChunksMixin:
    """Mixin for task chunk operations.

    Requires _HDF5Base as base class (provides h5_file_path, TASKS_GROUP, serializers).
    """

    def get_task_chunks(self, session_id: str, task_type: str) -> list[dict[str, Any]]:
        """Get task chunks.

        Args:
            session_id: Session identifier
            task_type: Task type

        Returns:
            List of chunk dicts (empty list if no chunks)
        """
        try:
            with h5py.File(self.h5_file_path, "r") as f:
                chunks_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}/chunks"
                if chunks_path not in f:
                    return []

                chunks_group = f[chunks_path]
                chunks = []

                for chunk_id in chunks_group.keys():
                    chunk_attrs = dict(chunks_group[chunk_id].attrs)
                    chunk_data = {
                        "id": chunk_id,
                        **{key: self._deserialize_value(val) for key, val in chunk_attrs.items()},
                    }
                    chunks.append(chunk_data)

                return chunks

        except Exception as e:
            logger.error(
                "GET_TASK_CHUNKS_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            return []

    def batch_update_chunk_datasets(
        self,
        session_id: str,
        task_type: str,
        chunk_idx: int,
        updates: dict[str, Any],
        max_retries: int = 5,
        initial_backoff: float = 0.1,
    ) -> bool:
        """Atomically update multiple chunk fields with retry logic.

        Fixes HDF5 SWMR race condition where concurrent readers can block writes.

        Args:
            session_id: Session identifier
            task_type: Task type
            chunk_idx: Chunk index
            updates: Dict of fields to update (transcript, language, confidence, etc.)
            max_retries: Maximum retry attempts on lock failure
            initial_backoff: Initial backoff delay in seconds (exponential backoff)

        Returns:
            True on success, False on failure (after all retries)
        """
        chunk_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}/chunks/chunk_{chunk_idx}"

        for attempt in range(max_retries):
            try:
                with h5py.File(self.h5_file_path, "a") as f:
                    if chunk_path not in f:
                        logger.warning(
                            "BATCH_UPDATE_CHUNK_NOT_FOUND",
                            session_id=session_id,
                            task_type=task_type,
                            chunk_idx=chunk_idx,
                        )
                        return False

                    chunk_group = f[chunk_path]

                    # Update all fields atomically
                    serialized = {
                        key: self._serialize_value(val) for key, val in updates.items()
                    }
                    for key, value in serialized.items():
                        chunk_group.attrs[key] = value

                    logger.info(
                        "BATCH_UPDATE_CHUNK_SUCCESS",
                        session_id=session_id,
                        task_type=task_type,
                        chunk_idx=chunk_idx,
                        fields_updated=list(updates.keys()),
                        attempt=attempt + 1,
                    )
                    return True

            except (OSError, BlockingIOError) as e:
                if attempt < max_retries - 1:
                    backoff = initial_backoff * (2**attempt)
                    logger.warning(
                        "BATCH_UPDATE_RETRY",
                        session_id=session_id,
                        chunk_idx=chunk_idx,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        backoff_seconds=backoff,
                        error=str(e),
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "BATCH_UPDATE_FAILED_ALL_RETRIES",
                        session_id=session_id,
                        chunk_idx=chunk_idx,
                        attempts=max_retries,
                        error=str(e),
                    )
                    return False

            except Exception as e:
                logger.error(
                    "BATCH_UPDATE_UNEXPECTED_ERROR",
                    session_id=session_id,
                    chunk_idx=chunk_idx,
                    error=str(e),
                    exc_info=True,
                )
                return False

        return False

    def save_chunk_audio(
        self,
        session_id: str,
        task_type: str,
        chunk_idx: int,
        audio_bytes: bytes,
        filename: str = "audio.webm",
    ) -> bool:
        """Save audio bytes for a specific chunk.

        Args:
            session_id: Session identifier
            task_type: Task type
            chunk_idx: Chunk index
            audio_bytes: Raw audio data to save
            filename: Audio filename (default: audio.webm)

        Returns:
            True on success, False on failure
        """
        chunk_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}/chunks/chunk_{chunk_idx}"
        audio_dataset_path = f"{filename}"

        try:
            with h5py.File(self.h5_file_path, "a") as f:
                # Ensure chunk group exists
                if chunk_path not in f:
                    f.create_group(chunk_path)

                chunk_group = f[chunk_path]

                # Delete existing audio if present
                if audio_dataset_path in chunk_group:
                    del chunk_group[audio_dataset_path]

                # Save audio bytes as dataset
                chunk_group.create_dataset(
                    audio_dataset_path,
                    data=audio_bytes,
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "CHUNK_AUDIO_SAVED",
                    session_id=session_id,
                    task_type=task_type,
                    chunk_idx=chunk_idx,
                    audio_size_bytes=len(audio_bytes),
                )
                return True

        except Exception as e:
            logger.error(
                "SAVE_CHUNK_AUDIO_FAILED",
                session_id=session_id,
                task_type=task_type,
                chunk_idx=chunk_idx,
                error=str(e),
                exc_info=True,
            )
            return False

    def get_chunk_audio_bytes(
        self, session_id: str, task_type: str, chunk_idx: int
    ) -> bytes | None:
        """Get audio bytes from chunk.

        Args:
            session_id: Session identifier
            task_type: Task type
            chunk_idx: Chunk index

        Returns:
            Audio bytes or None if not found
        """
        try:
            chunk_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}/chunks/chunk_{chunk_idx}"
            audio_dataset_path = f"{chunk_path}/audio.webm"

            with h5py.File(self.h5_file_path, "r") as f:
                if audio_dataset_path not in f:
                    logger.warning(
                        "CHUNK_AUDIO_NOT_FOUND",
                        session_id=session_id,
                        task_type=task_type,
                        chunk_idx=chunk_idx,
                    )
                    return None

                audio_dataset = f[audio_dataset_path]
                audio_bytes = bytes(audio_dataset[()])

                logger.debug(
                    "CHUNK_AUDIO_READ",
                    session_id=session_id,
                    task_type=task_type,
                    chunk_idx=chunk_idx,
                    audio_size_bytes=len(audio_bytes),
                )
                return audio_bytes

        except Exception as e:
            logger.error(
                "GET_CHUNK_AUDIO_FAILED",
                session_id=session_id,
                task_type=task_type,
                chunk_idx=chunk_idx,
                error=str(e),
                exc_info=True,
            )
            return None
