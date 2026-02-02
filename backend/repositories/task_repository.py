"""Task Repository - HDF5-based task management.

Handles task lifecycle:
- Task creation and metadata storage
- Task chunks management
- Task status tracking

Clean Architecture:
- Implements ITaskRepository interface
- Isolated from business logic
- HDF5 as implementation detail
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import h5py
from backend.domain.session import ISessionRepository
from backend.utils.coder.utils.exceptions import SessionNotFoundError
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class HDF5TaskRepository(ITaskRepository):
    """HDF5-based implementation of ITaskRepository (Fix #1).

    Storage-agnostic interface - internal HDF5 structure is an implementation detail.
    Tasks are stored with metadata and optional chunks, organized by session and type.
    Structure may change without affecting domain layer.
    """

    TASKS_GROUP = "tasks"

    def __init__(
        self,
        h5_file_path: str | Path,
        session_repository: ISessionRepository | None = None,
    ):
        """Initialize task repository.

        Args:
            h5_file_path: Path to HDF5 database file
            session_repository: Optional session repository for referential integrity (Fix #5)
        """
        self.h5_file_path = Path(h5_file_path)
        self.session_repository = session_repository
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure required HDF5 structure exists."""
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                f.require_group(self.TASKS_GROUP)
            logger.info("TASK_REPOSITORY_STRUCTURE_READY", file_path=str(self.h5_file_path))
        except OSError as e:
            logger.error("TASK_REPOSITORY_STRUCTURE_INIT_FAILED", error=str(e))
            raise

    def get_task_metadata(self, session_id: str, task_type: str) -> dict[str, Any] | None:
        """Get task metadata.

        Args:
            session_id: Session identifier
            task_type: Task type (e.g., "transcription", "soap_generation")

        Returns:
            Task metadata dict or None if task doesn't exist
        """
        try:
            with h5py.File(self.h5_file_path, "r") as f:
                task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"
                if task_path not in f:
                    return None

                task_group = f[task_path]
                metadata = dict(task_group.attrs)

                # Deserialize JSON values
                return {
                    key: self._deserialize_value(val) for key, val in metadata.items()
                }

        except Exception as e:
            logger.error(
                "GET_TASK_METADATA_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            return None

    def task_exists(self, session_id: str, task_type: str) -> bool:
        """Check if task exists.

        Args:
            session_id: Session identifier
            task_type: Task type

        Returns:
            True if task exists
        """
        try:
            with h5py.File(self.h5_file_path, "r") as f:
                task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"
                return task_path in f
        except Exception as e:
            logger.error(
                "TASK_EXISTS_CHECK_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            return False

    def ensure_task_exists(
        self, session_id: str, task_type: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """Ensure task exists, create if not (Fix #5 - with referential integrity).

        Args:
            session_id: Session identifier
            task_type: Task type
            metadata: Optional initial metadata

        Returns:
            Task identifier (f"{session_id}/{task_type}")

        Raises:
            SessionNotFoundError: If session_repository is injected and session doesn't exist
        """
        # REFERENTIAL INTEGRITY: Validate session exists BEFORE creating task
        if self.session_repository is not None:
            if not self.session_repository.exists(session_id):
                logger.error(
                    "TASK_CREATE_SESSION_NOT_FOUND",
                    session_id=session_id,
                    task_type=task_type,
                    message="Cannot create task for non-existent session",
                )
                raise SessionNotFoundError(
                    f"Session {session_id} not found. Cannot create task {task_type}."
                )

        try:
            with h5py.File(self.h5_file_path, "a") as f:
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)
                task_group = session_group.require_group(task_type)

                # Set metadata if provided and task was just created
                if metadata and len(task_group.attrs) == 0:
                    serialized = {
                        key: self._serialize_value(val) for key, val in metadata.items()
                    }
                    for key, value in serialized.items():
                        task_group.attrs[key] = value

                    logger.info(
                        "TASK_CREATED",
                        session_id=session_id,
                        task_type=task_type,
                    )

            return f"{session_id}/{task_type}"

        except Exception as e:
            logger.error(
                "ENSURE_TASK_EXISTS_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            raise

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

    def save_task_metadata(
        self, session_id: str, task_type: str, metadata: dict[str, Any]
    ) -> None:
        """Save task metadata.

        Args:
            session_id: Session identifier
            task_type: Task type
            metadata: Metadata to save (merged with existing)
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"

                # Ensure task exists
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)
                task_group = session_group.require_group(task_type)

                # Update metadata
                serialized = {key: self._serialize_value(val) for key, val in metadata.items()}
                for key, value in serialized.items():
                    task_group.attrs[key] = value

                logger.info(
                    "TASK_METADATA_SAVED",
                    session_id=session_id,
                    task_type=task_type,
                )

        except Exception as e:
            logger.error(
                "SAVE_TASK_METADATA_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            raise

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
        import time

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

    def save_diarization_segments(
        self, session_id: str, segments: list[dict[str, Any]]
    ) -> None:
        """Save diarization segments to HDF5.

        Args:
            session_id: Session identifier
            segments: List of segment dicts with speaker, text, timestamps
        """
        try:
            task_path = f"{self.TASKS_GROUP}/{session_id}/DIARIZATION"
            segments_dataset_path = f"{task_path}/segments"

            segments_json = json.dumps(segments, ensure_ascii=False, indent=2)

            with h5py.File(self.h5_file_path, "a") as f:
                # Ensure task group exists
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)
                task_group = session_group.require_group("DIARIZATION")

                # Delete existing segments if present
                if "segments" in task_group:
                    del task_group["segments"]

                # Create new segments dataset
                task_group.create_dataset(
                    "segments",
                    data=segments_json.encode("utf-8"),
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "DIARIZATION_SEGMENTS_SAVED",
                    session_id=session_id,
                    segment_count=len(segments),
                    path=segments_dataset_path,
                )

        except Exception as e:
            logger.error(
                "SAVE_DIARIZATION_SEGMENTS_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def get_diarization_segments(self, session_id: str) -> list[dict[str, Any]]:
        """Get diarization segments from HDF5.

        Args:
            session_id: Session identifier

        Returns:
            List of segment dicts or empty list if not found
        """
        try:
            segments_path = f"{self.TASKS_GROUP}/{session_id}/DIARIZATION/segments"

            with h5py.File(self.h5_file_path, "r") as f:
                if segments_path not in f:
                    logger.warning(
                        "DIARIZATION_SEGMENTS_NOT_FOUND",
                        session_id=session_id,
                    )
                    return []

                segments_data = f[segments_path][()]
                segments_json = bytes(segments_data).decode("utf-8")
                segments = json.loads(segments_json)

                logger.debug(
                    "DIARIZATION_SEGMENTS_READ",
                    session_id=session_id,
                    segment_count=len(segments),
                )
                return segments

        except Exception as e:
            logger.error(
                "GET_DIARIZATION_SEGMENTS_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return []

    def get_soap_data(self, session_id: str) -> dict[str, Any] | None:
        """Get SOAP note from HDF5.

        Args:
            session_id: Session identifier

        Returns:
            SOAP note dict or None if not found
        """
        try:
            task_path = f"{self.TASKS_GROUP}/{session_id}/SOAP_GENERATION"
            soap_dataset_path = f"{task_path}/soap_note"

            with h5py.File(self.h5_file_path, "r") as f:
                if soap_dataset_path not in f:
                    return None

                soap_data = f[soap_dataset_path][()]
                soap_json = bytes(soap_data).decode("utf-8")
                return json.loads(soap_json)

        except Exception as e:
            logger.error(
                "GET_SOAP_DATA_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return None

    def save_soap_data(
        self, session_id: str, soap_data: dict[str, Any], task_type: str = "SOAP_GENERATION"
    ) -> None:
        """Save SOAP note to HDF5.

        Args:
            session_id: Session identifier
            soap_data: SOAP note dict (subjective, objective, assessment, plan)
            task_type: Task type (default: SOAP_GENERATION)
        """
        try:
            task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"
            soap_dataset_path = f"{task_path}/soap_note"

            soap_json = json.dumps(soap_data, ensure_ascii=False, indent=2)

            with h5py.File(self.h5_file_path, "a") as f:
                # Ensure task group exists
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)
                task_group = session_group.require_group(task_type)

                # Delete existing SOAP note if present
                if "soap_note" in task_group:
                    del task_group["soap_note"]

                # Create new SOAP note dataset
                task_group.create_dataset(
                    "soap_note",
                    data=soap_json.encode("utf-8"),
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "SOAP_NOTE_SAVED",
                    session_id=session_id,
                    path=soap_dataset_path,
                )

        except Exception as e:
            logger.error(
                "SAVE_SOAP_DATA_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def create_order(self, session_id: str, order_data: dict[str, Any]) -> None:
        """Create order for session.

        Args:
            session_id: Session identifier
            order_data: Order dict (type, description, details, source)
        """
        try:
            orders_path = f"{self.TASKS_GROUP}/{session_id}/orders"

            with h5py.File(self.h5_file_path, "a") as f:
                # Ensure session group exists
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)

                # Get or create orders list
                if "orders" in session_group:
                    orders_data = session_group["orders"][()]
                    orders_json = bytes(orders_data).decode("utf-8")
                    orders = json.loads(orders_json)
                else:
                    orders = []

                # Append new order
                orders.append(order_data)

                # Save updated orders list
                orders_json = json.dumps(orders, ensure_ascii=False, indent=2)

                if "orders" in session_group:
                    del session_group["orders"]

                session_group.create_dataset(
                    "orders",
                    data=orders_json.encode("utf-8"),
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "ORDER_CREATED",
                    session_id=session_id,
                    order_type=order_data.get("type"),
                    description=order_data.get("description"),
                    total_orders=len(orders),
                )

        except Exception as e:
            logger.error(
                "CREATE_ORDER_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def get_orders(self, session_id: str) -> list[dict[str, Any]]:
        """Get orders for session.

        Args:
            session_id: Session identifier

        Returns:
            List of order dicts or empty list if none
        """
        try:
            orders_path = f"{self.TASKS_GROUP}/{session_id}/orders"

            with h5py.File(self.h5_file_path, "r") as f:
                if orders_path not in f:
                    logger.debug(
                        "ORDERS_NOT_FOUND",
                        session_id=session_id,
                    )
                    return []

                orders_data = f[orders_path][()]
                orders_json = bytes(orders_data).decode("utf-8")
                orders = json.loads(orders_json)

                logger.debug(
                    "ORDERS_READ",
                    session_id=session_id,
                    order_count=len(orders),
                )
                return orders

        except Exception as e:
            logger.error(
                "GET_ORDERS_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return []

    def add_webspeech_transcripts(
        self, session_id: str, transcripts: list[str], task_type: str = "TRANSCRIPTION"
    ) -> None:
        """Save webspeech transcripts to HDF5.

        Args:
            session_id: Session identifier
            transcripts: List of transcript strings from WebSpeech
            task_type: Task type (default: TRANSCRIPTION)
        """
        try:
            task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"
            webspeech_path = f"{task_path}/webspeech_final"

            transcripts_json = json.dumps(transcripts, ensure_ascii=False, indent=2)

            with h5py.File(self.h5_file_path, "a") as f:
                # Ensure task group exists
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)
                task_group = session_group.require_group(task_type)

                # Delete existing webspeech if present
                if "webspeech_final" in task_group:
                    del task_group["webspeech_final"]

                # Create new webspeech dataset
                task_group.create_dataset(
                    "webspeech_final",
                    data=transcripts_json.encode("utf-8"),
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "WEBSPEECH_TRANSCRIPTS_SAVED",
                    session_id=session_id,
                    count=len(transcripts),
                    path=webspeech_path,
                )

        except Exception as e:
            logger.error(
                "ADD_WEBSPEECH_TRANSCRIPTS_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def add_full_transcription(
        self, session_id: str, full_text: str, task_type: str = "TRANSCRIPTION"
    ) -> None:
        """Save full concatenated transcription to HDF5.

        Args:
            session_id: Session identifier
            full_text: Full concatenated transcript text
            task_type: Task type (default: TRANSCRIPTION)
        """
        try:
            task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"
            full_text_path = f"{task_path}/full_transcription"

            with h5py.File(self.h5_file_path, "a") as f:
                # Ensure task group exists
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)
                task_group = session_group.require_group(task_type)

                # Delete existing full_transcription if present
                if "full_transcription" in task_group:
                    del task_group["full_transcription"]

                # Create new full_transcription dataset
                task_group.create_dataset(
                    "full_transcription",
                    data=full_text.encode("utf-8"),
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "FULL_TRANSCRIPTION_SAVED",
                    session_id=session_id,
                    length=len(full_text),
                    path=full_text_path,
                )

        except Exception as e:
            logger.error(
                "ADD_FULL_TRANSCRIPTION_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def add_full_audio(
        self, session_id: str, audio_bytes: bytes, filename: str = "full_audio.webm",
        task_type: str = "TRANSCRIPTION"
    ) -> None:
        """Save full concatenated audio to HDF5.

        Args:
            session_id: Session identifier
            audio_bytes: Full concatenated audio bytes
            filename: Audio filename (default: full_audio.webm)
            task_type: Task type (default: TRANSCRIPTION)
        """
        try:
            task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"
            audio_path = f"{task_path}/{filename}"

            with h5py.File(self.h5_file_path, "a") as f:
                # Ensure task group exists
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)
                task_group = session_group.require_group(task_type)

                # Delete existing full audio if present
                if filename in task_group:
                    del task_group[filename]

                # Create new full audio dataset
                task_group.create_dataset(
                    filename,
                    data=audio_bytes,
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "FULL_AUDIO_SAVED",
                    session_id=session_id,
                    audio_size_bytes=len(audio_bytes),
                    path=audio_path,
                )

        except Exception as e:
            logger.error(
                "ADD_FULL_AUDIO_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def update_order(
        self, session_id: str, order_id: str, updated_data: dict[str, Any]
    ) -> None:
        """Update an existing order.

        Args:
            session_id: Session identifier
            order_id: Order ID to update
            updated_data: Dict with updated fields (type, description, details)

        Raises:
            ValueError: If order not found
        """
        try:
            orders_path = f"{self.TASKS_GROUP}/{session_id}/orders"

            with h5py.File(self.h5_file_path, "a") as f:
                if orders_path not in f:
                    raise ValueError(f"No orders found for session {session_id}")

                orders_data = f[orders_path][()]
                orders_json = bytes(orders_data).decode("utf-8")
                orders = json.loads(orders_json)

                # Find and update order
                order_found = False
                for order in orders:
                    if str(order.get("order_id")) == str(order_id):
                        order.update(updated_data)
                        order_found = True
                        break

                if not order_found:
                    raise ValueError(f"Order {order_id} not found in session {session_id}")

                # Save updated orders list
                updated_json = json.dumps(orders, ensure_ascii=False, indent=2)

                # Delete and recreate dataset
                session_group = f[f"{self.TASKS_GROUP}/{session_id}"]
                del session_group["orders"]
                session_group.create_dataset(
                    "orders",
                    data=updated_json.encode("utf-8"),
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "ORDER_UPDATED",
                    session_id=session_id,
                    order_id=order_id,
                )

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "UPDATE_ORDER_FAILED",
                session_id=session_id,
                order_id=order_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def delete_order(self, session_id: str, order_id: str) -> None:
        """Delete an order.

        Args:
            session_id: Session identifier
            order_id: Order ID to delete

        Raises:
            ValueError: If order not found
        """
        try:
            orders_path = f"{self.TASKS_GROUP}/{session_id}/orders"

            with h5py.File(self.h5_file_path, "a") as f:
                if orders_path not in f:
                    raise ValueError(f"No orders found for session {session_id}")

                orders_data = f[orders_path][()]
                orders_json = bytes(orders_data).decode("utf-8")
                orders = json.loads(orders_json)

                # Filter out deleted order
                original_count = len(orders)
                orders = [o for o in orders if str(o.get("order_id")) != str(order_id)]

                if len(orders) == original_count:
                    raise ValueError(f"Order {order_id} not found in session {session_id}")

                # Save updated orders list
                updated_json = json.dumps(orders, ensure_ascii=False, indent=2)

                # Delete and recreate dataset
                session_group = f[f"{self.TASKS_GROUP}/{session_id}"]
                del session_group["orders"]
                session_group.create_dataset(
                    "orders",
                    data=updated_json.encode("utf-8"),
                    dtype=h5py.special_dtype(vlen=bytes),
                )

                logger.info(
                    "ORDER_DELETED",
                    session_id=session_id,
                    order_id=order_id,
                    remaining_orders=len(orders),
                )

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "DELETE_ORDER_FAILED",
                session_id=session_id,
                order_id=order_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def delete_by_session(self, session_id: str) -> int:
        """Delete all tasks for a session (Fix #5 - cascade delete).

        Args:
            session_id: Session identifier

        Returns:
            Number of task types deleted

        Purpose:
            Enables cascade delete when session is removed.
            Prevents orphaned tasks with invalid session_id references.
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                session_tasks_path = f"{self.TASKS_GROUP}/{session_id}"

                if session_tasks_path not in f:
                    logger.debug(
                        "DELETE_BY_SESSION_NO_TASKS",
                        session_id=session_id,
                        message="No tasks found for session (already deleted or never created)",
                    )
                    return 0

                # Count task types before deletion
                session_group = f[session_tasks_path]
                task_types_count = len(session_group.keys())

                # Delete entire session group (all task types)
                del f[session_tasks_path]

                logger.info(
                    "DELETE_BY_SESSION_SUCCESS",
                    session_id=session_id,
                    task_types_deleted=task_types_count,
                )

                return task_types_count

        except Exception as e:
            logger.error(
                "DELETE_BY_SESSION_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def delete_task(self, session_id: str, task_type: str) -> bool:
        """Delete task and all chunks (stub implementation).

        Args:
            session_id: Session UUID
            task_type: Task type

        Returns:
            True if deletion successful, False if task not found

        Raises:
            IOError: If delete operation fails
        """
        # TODO: Implement delete logic (delete task group from HDF5)
        logger.warning(
            "DELETE_TASK_NOT_IMPLEMENTED",
            session_id=session_id,
            task_type=task_type,
            hint="Stub implementation - no actual deletion performed",
        )
        return False

    def get_task_progress(self, session_id: str, task_type: str) -> dict[str, Any]:
        """Get task progress summary (stub implementation).

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
            FileNotFoundError: If task not found
        """
        # TODO: Implement progress calculation from HDF5 task metadata
        try:
            metadata = self.get_task_metadata(session_id, task_type)
            status = metadata.get("status", "unknown") if metadata else "not_found"

            return {
                "status": status,
                "total_chunks": 0,
                "processed_chunks": 0,
                "progress_percent": 0.0,
                "estimated_completion": None,
            }
        except Exception as e:
            logger.error(
                "GET_TASK_PROGRESS_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            raise FileNotFoundError(f"Task not found: {session_id}/{task_type}") from e

    @staticmethod
    def _serialize_value(value: Any) -> str | int | float | bool:
        """Serialize Python value to HDF5-compatible type."""
        if isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, (list, dict)) or value is None:
            return json.dumps(value)
        else:
            return str(value)

    @staticmethod
    def _deserialize_value(value: Any) -> Any:
        """Deserialize HDF5 attr value to Python type."""
        if not isinstance(value, (str, bytes)):
            return value

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        if isinstance(value, str):
            if value.startswith(("{", "[")):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            elif value == "null":
                return None

        return value
