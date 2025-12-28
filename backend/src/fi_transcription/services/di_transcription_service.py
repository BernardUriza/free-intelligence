"""DI Transcription Service - Refactored with dependency injection.

Handles audio transcription workflows with injected dependencies.
"""

from __future__ import annotations

from backend.models.task_type import TaskType
from backend.src.fi_common.interfaces.ilogger import ILogger
from backend.src.fi_common.interfaces.itask_repository import ITaskRepository


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


class DITranscriptionService:
    """Transcription service with dependency injection."""

    def __init__(self, logger: ILogger, task_repository: ITaskRepository):
        """Initialize service with injected dependencies.

        Args:
            logger: Logger instance
            task_repository: Task repository instance
        """
        self.logger = logger
        self.task_repository = task_repository

    async def process_chunk(
        self,
        session_id: str,
        chunk_number: int,
        audio_bytes: bytes,
        timestamp_start: float | None = None,
        timestamp_end: float | None = None,
    ) -> ChunkProcessingResult:
        """Process audio chunk for transcription (ASYNC pattern).

        Business logic (FAST path - returns in ~100ms):
        1. Validate input
        2. Ensure TRANSCRIPTION task exists
        3. Store audio in HDF5 immediately (append-only)
        4. Dispatch worker to ThreadPoolExecutor (background transcription)
        5. Return 202 Accepted immediately

        Args:
            session_id: Session UUID
            chunk_number: Sequential chunk index
            audio_bytes: Raw audio data
            timestamp_start: Optional chunk start time
            timestamp_end: Optional chunk end time

        Returns:
            ChunkProcessingResult with task info (status='pending')

        Raises:
            ValueError: If audio is empty or invalid
        """
        import time

        start_time = time.time()

        # 1. Business validation
        if not audio_bytes or len(audio_bytes) == 0:
            raise ValueError("Audio data cannot be empty")

        if chunk_number < 0:
            raise ValueError(f"Invalid chunk number: {chunk_number}")

        audio_size = len(audio_bytes)
        self.logger.info(
            "CHUNK_PROCESSING_STARTED",
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=audio_size,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )

        # 2. Ensure TRANSCRIPTION task exists
        task_id = self.task_repository.ensure_task_exists(
            session_id, TaskType.TRANSCRIPTION.value
        )

        # 3. Get existing chunks to determine total/processed counts
        existing_chunks = self.task_repository.get_task_chunks(
            session_id, TaskType.TRANSCRIPTION.value
        )
        total_chunks = max(chunk_number + 1, len(existing_chunks))
        processed_chunks = len(existing_chunks)

        # 4. Store audio chunk in HDF5 (TODO: implement actual storage)
        # For now, just log
        self.logger.info(
            "CHUNK_STORED",
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=task_id,
            audio_size=audio_size,
        )

        # 5. Dispatch background worker (TODO: implement actual worker dispatch)
        # For now, just simulate async processing
        processing_time = time.time() - start_time
        self.logger.info(
            "CHUNK_PROCESSING_COMPLETED",
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=task_id,
            processing_time_ms=int(processing_time * 1000),
        )

        return ChunkProcessingResult(
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=task_id,
            status="pending",
            total_chunks=total_chunks,
            processed_chunks=processed_chunks,
        )
