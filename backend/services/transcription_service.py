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

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import (
    ensure_task_exists,
    get_task_chunks,
    get_task_metadata,
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

        Worker executes independently:
        - Transcribes audio (10-15s with Deepgram/Whisper)
        - Updates HDF5 with transcript + metadata
        - No blocking of HTTP request

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
        logger.info(
            "CHUNK_PROCESSING_STARTED",
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=audio_size,
            timestamp=start_time,
        )
        logger.debug(
            "AUDIO_VALIDATION_OK",
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=audio_size,
        )

        # 2. Ensure TRANSCRIPTION task exists
        logger.debug(
            "ENSURING_TRANSCRIPTION_TASK",
            session_id=session_id,
        )
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            allow_existing=True,
        )
        logger.debug(
            "TRANSCRIPTION_TASK_EXISTS",
            session_id=session_id,
        )

        # 3. Save audio to HDF5 IMMEDIATELY (fast path - no transcription yet)
        import hashlib

        from backend.models.task_type import CHUNK_DURATION_SECONDS
        from backend.storage.task_repository import (
            add_audio_to_chunk,
            append_chunk_to_task,
            update_task_metadata,
        )

        audio_hash = hashlib.sha256(audio_bytes).hexdigest()

        # Calculate timestamps
        timestamp_start = chunk_number * CHUNK_DURATION_SECONDS
        timestamp_end = timestamp_start + CHUNK_DURATION_SECONDS

        # Append chunk with placeholder transcript (worker will update later)
        append_chunk_to_task(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            transcript="",  # Empty - worker will fill this
            audio_hash=audio_hash,
            duration=0.0,  # Worker will update
            language="es",
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            confidence=0.0,  # Worker will update
            audio_quality=0.9,
        )

        # Save audio bytes to HDF5 (colocated with chunk)
        add_audio_to_chunk(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            audio_bytes=audio_bytes,
        )

        logger.info(
            "AUDIO_SAVED_TO_HDF5",
            session_id=session_id,
            chunk_number=chunk_number,
            audio_size=audio_size,
        )

        # 4. Update task metadata (track total chunks)
        metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}
        total_chunks = max(metadata.get("total_chunks", 0), chunk_number + 1)
        processed_chunks = metadata.get("processed_chunks", 0)

        update_task_metadata(
            session_id,
            TaskType.TRANSCRIPTION,
            {
                "total_chunks": total_chunks,
                "processed_chunks": processed_chunks,
                "status": "in_progress" if processed_chunks > 0 else "pending",
            },
        )

        # 5. Dispatch worker to background (fire-and-forget)
        from backend.utils.stt_load_balancer import get_stt_load_balancer
        from backend.workers.executor_pool import spawn_worker
        from backend.workers.sync_workers import transcribe_chunk_worker

        # Use load balancer to select provider intelligently (policy-driven)
        load_balancer = get_stt_load_balancer()
        stt_provider, decision_reason = load_balancer.select_provider_for_file(
            audio_size_bytes=len(audio_bytes),
            chunk_number=chunk_number,
            session_id=session_id,
        )

        spawn_worker(
            transcribe_chunk_worker,
            session_id=session_id,
            chunk_number=chunk_number,
            stt_provider=stt_provider,
        )

        logger.info(
            "WORKER_DISPATCHED",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=stt_provider,
            decision_reason=decision_reason,
            audio_size_mb=len(audio_bytes) / (1024 * 1024),
        )

        # 6. Return result IMMEDIATELY (202 Accepted pattern)
        metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}
        elapsed = time.time() - start_time
        result = ChunkProcessingResult(
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=session_id,  # Use session_id since we use ThreadPoolExecutor now
            status="pending",
            total_chunks=metadata.get("total_chunks", 0),
            processed_chunks=metadata.get("processed_chunks", 0),
        )

        logger.info(
            "CHUNK_ACCEPTED",
            session_id=session_id,
            chunk_number=chunk_number,
            total_chunks=result.total_chunks,
            duration_ms=int(elapsed * 1000),
            status="pending",
            note="Worker dispatched - transcription will complete asynchronously",
        )

        return result

    async def transcribe_audio_sync(
        self,
        audio_bytes: bytes,
    ) -> dict:
        """Async audio transcription for chat mode (runs in thread pool).

        NOTE: This uses asyncio.to_thread() to run blocking STT in a thread pool.
        This prevents blocking the event loop during transcription (10-15s).
        Medical mode should use process_chunk() with workers instead.

        Args:
            audio_bytes: Raw audio data

        Returns:
            dict with keys:
                - text: Transcription text
                - provider: STT provider used (deepgram, azure_whisper)
                - confidence: Confidence score (0.0-1.0)
                - duration: Audio duration in seconds
                - language: Detected language
        """
        import asyncio
        import os
        import tempfile

        from backend.providers.stt import get_stt_provider
        from backend.utils.stt_load_balancer import get_stt_load_balancer

        # Get load balancer and select provider
        balancer = get_stt_load_balancer()
        provider_name, decision_reason = balancer.select_provider_for_file(
            audio_size_bytes=len(audio_bytes),
            chunk_number=0,  # Chat doesn't use chunk numbers for routing
            session_id="chat",  # Placeholder
        )

        logger.info(
            "SYNC_TRANSCRIPTION_START",
            provider=provider_name,
            audio_size_kb=len(audio_bytes) / 1024,
            decision_reason=decision_reason,
        )

        # Write audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # Get provider config from policy
            provider_config = balancer.policy.get("stt", {}).get("providers", {}).get(provider_name, {})

            # Transcribe in thread pool (blocking call)
            def _do_transcribe():
                provider = get_stt_provider(provider_name, config=provider_config)
                return provider.transcribe(tmp_path, language="es")

            response = await asyncio.to_thread(_do_transcribe)

            logger.info(
                "SYNC_TRANSCRIPTION_SUCCESS",
                provider=provider_name,
                transcript_length=len(response.text),
                confidence=response.confidence,
            )

            return {
                "text": response.text,
                "provider": response.provider,
                "confidence": response.confidence,
                "duration": response.duration,
                "language": response.language,
            }

        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

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
