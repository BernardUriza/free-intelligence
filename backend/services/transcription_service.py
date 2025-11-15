"""Transcription Service - Business logic layer.

Handles audio transcription workflows including:
- Chunk validation
- Task creation
- Worker dispatch
- Status tracking

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Clean Architecture Refactor
"""

from __future__ import annotations

from typing import Optional

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import (
    ensure_task_exists,
    get_task_chunks,
    get_task_metadata,
    update_task_metadata,
)

logger = get_logger(__name__)


class ChunkProcessingResult:
    """Result of chunk processing."""

    def __init__(
        self,
        session_id: str,
        chunk_number: int,
        task_id: str,
        status: str,
        total_chunks: int,
        processed_chunks: int,
    ):
        self.session_id = session_id
        self.chunk_number = chunk_number
        self.task_id = task_id
        self.status = status
        self.total_chunks = total_chunks
        self.processed_chunks = processed_chunks


class TranscriptionService:
    """Service for audio transcription business logic."""

    async def process_chunk(
        self,
        session_id: str,
        chunk_number: int,
        audio_bytes: bytes,
        timestamp_start: Optional[float] = None,
        timestamp_end: Optional[float] = None,
    ) -> ChunkProcessingResult:
        """Process audio chunk for transcription.

        Business logic:
        1. Validate input
        2. Ensure TRANSCRIPTION task exists
        3. Store audio in HDF5 (NOT in Celery message!)
        4. Update metadata
        5. Dispatch Celery worker (with references only)
        6. Return processing result

        Args:
            session_id: Session UUID
            chunk_number: Sequential chunk index
            audio_bytes: Raw audio data
            timestamp_start: Optional chunk start time
            timestamp_end: Optional chunk end time

        Returns:
            ChunkProcessingResult with task info

        Raises:
            ValueError: If audio is empty or invalid
        """
        # 1. Business validation
        if not audio_bytes or len(audio_bytes) == 0:
            raise ValueError("Audio data cannot be empty")

        if chunk_number < 0:
            raise ValueError(f"Invalid chunk number: {chunk_number}")

        audio_size = len(audio_bytes)
        logger.info(
            "CHUNK_PROCESSING_STARTED",
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=audio_size,
        )

        # 2. Ensure TRANSCRIPTION task exists
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            allow_existing=True,
        )

        # 3. Store audio in HDF5 FIRST (before Celery dispatch)
        # This avoids serializing large binary blobs through Redis
        from backend.storage.task_repository import (
            add_audio_to_chunk,
            create_empty_chunk,
        )

        try:
            # First, create empty chunk structure
            create_empty_chunk(
                session_id=session_id,
                task_type=TaskType.TRANSCRIPTION,
                chunk_idx=chunk_number,
            )

            # Then add audio to it
            add_audio_to_chunk(
                session_id=session_id,
                task_type=TaskType.TRANSCRIPTION,
                chunk_idx=chunk_number,
                audio_bytes=audio_bytes,
            )
            logger.info(
                "AUDIO_STORED_IN_HDF5",
                session_id=session_id,
                chunk_number=chunk_number,
                audio_size=audio_size,
            )
        except Exception as e:
            logger.error(
                "AUDIO_STORAGE_FAILED",
                session_id=session_id,
                chunk_number=chunk_number,
                error=str(e),
            )
            raise

        # 4. Update metadata
        metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)
        if not metadata:
            metadata = {
                "job_id": session_id,
                "total_chunks": 0,
                "processed_chunks": 0,
            }

        # Check if this is a new chunk
        existing_chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)
        chunk_numbers = {c.get("chunk_number", -1) for c in existing_chunks}

        if chunk_number not in chunk_numbers:
            metadata["total_chunks"] = metadata.get("total_chunks", 0) + 1
            update_task_metadata(session_id, TaskType.TRANSCRIPTION, metadata)

        logger.info(
            "TASK_METADATA_UPDATED",
            session_id=session_id,
            chunk_number=chunk_number,
            total_chunks=metadata["total_chunks"],
        )

        # 5. Dispatch Celery worker (with REFERENCES ONLY, no large audio blobs!)
        # Use Deepgram instead of Whisper for faster, cloud-based transcription
        from backend.workers.deepgram_transcription_task import (
            deepgram_transcribe_chunk,
        )

        task = deepgram_transcribe_chunk.delay(  # type: ignore[attr-defined]
            session_id=session_id,
            chunk_number=chunk_number,
            language="es",  # Default to Spanish; can be made configurable
            # IMPORTANT: Only send references, not audio_bytes!
            # Audio is already in HDF5, worker will read from there
        )

        logger.info(
            "WORKER_DISPATCHED",
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=task.id,
        )

        # 6. Return result
        return ChunkProcessingResult(
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=task.id,
            status="pending",
            total_chunks=metadata["total_chunks"],
            processed_chunks=metadata.get("processed_chunks", 0),
        )

    async def get_transcription_status(
        self,
        session_id: str,
    ) -> dict:
        """Get transcription status for session.

        Args:
            session_id: Session UUID

        Returns:
            dict with status, chunks, and metadata

        Raises:
            ValueError: If session not found
        """
        from backend.storage.task_repository import task_exists

        if not task_exists(session_id, TaskType.TRANSCRIPTION):
            raise ValueError(f"Transcription task not found for session {session_id}")

        # Get metadata
        metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}

        # Get chunks
        chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)

        # Calculate stats
        total_chunks = len(chunks)
        processed_chunks = sum(1 for c in chunks if c.get("status") == "completed")
        progress_percent = int(processed_chunks / total_chunks * 100) if total_chunks > 0 else 0

        # Determine status
        if processed_chunks == 0:
            status = "pending"
        elif processed_chunks < total_chunks:
            status = "in_progress"
        else:
            status = "completed"

        return {
            "session_id": session_id,
            "job_id": metadata.get("job_id", session_id),
            "status": status,
            "total_chunks": total_chunks,
            "processed_chunks": processed_chunks,
            "progress_percent": progress_percent,
            "chunks": chunks,
            "created_at": metadata.get("created_at"),
            "updated_at": metadata.get("updated_at"),
        }
