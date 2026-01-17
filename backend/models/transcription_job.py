"""TranscriptionJob model for chunk-based transcription.

Philosophy:
  1 Session → 1 TranscriptionJob
    ├─ Processes N chunks sequentially
    ├─ Tracks progress (X/N chunks)
    ├─ Persists in /sessions/{session_id}/jobs/transcription/{job_id}.json
    └─ Dual write to production + ml_ready paths

Storage locations:
  - Job metadata: /sessions/{session_id}/jobs/transcription/{job_id}.json
  - Production data: /sessions/{session_id}/production/chunks/chunk_{N}/
  - ML data: /sessions/{session_id}/ml_ready/text/chunks/chunk_{N}/

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Architecture unification
"""

from __future__ import annotations

from typing import Any

from backend.models.job import Job, JobStatus, JobType


class ChunkMetadata:
    """Metadata for a single audio chunk.

    This tracks the processing state of each chunk within a TranscriptionJob.
    """

    __slots__ = (
        "audio_hash",
        "audio_quality",
        "audio_size_bytes",
        "chunk_number",
        "confidence",
        "created_at",
        "duration",
        "error_message",
        "language",
        "status",
        "timestamp_end",
        "timestamp_start",
        "transcript",
    )

    def __init__(
        self,
        *,
        chunk_number: int,
        status: str,
        audio_size_bytes: int,
        audio_hash: str | None = None,
        transcript: str | None = None,
        duration: float | None = None,
        language: str | None = None,
        confidence: float | None = None,
        audio_quality: float | None = None,
        timestamp_start: float | None = None,
        timestamp_end: float | None = None,
        created_at: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.chunk_number = chunk_number
        self.status = status
        self.audio_size_bytes = audio_size_bytes
        self.audio_hash = audio_hash
        self.transcript = transcript
        self.duration = duration
        self.language = language
        self.confidence = confidence
        self.audio_quality = audio_quality
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end
        self.created_at = created_at
        self.error_message = error_message


class TranscriptionJob(Job):
    """Transcription job for processing audio chunks.

    A TranscriptionJob processes multiple audio chunks sequentially for a single session.
    Each chunk is transcribed using Whisper ASR and appended to HDF5 (dual write).

    Attributes:
        chunks: List of chunk metadata (ordered by chunk_number)
        total_chunks: Total number of chunks expected
        processed_chunks: Number of chunks successfully processed
        audio_file_path: Path to full audio file (optional, for end-of-session)
        audio_duration: Total duration of audio (seconds)
        primary_language: Primary language detected (es, en, etc.)
    """

    __slots__ = (
        "audio_duration",
        "audio_file_path",
        "chunks",
        "primary_language",
        "processed_chunks",
        "total_chunks",
    )

    def __init__(
        self,
        *,
        # Base Job fields
        job_id: str,
        session_id: str,
        job_type: JobType | str,
        status: JobStatus | str,
        created_at: str,
        started_at: str | None = None,
        completed_at: str | None = None,
        updated_at: str = "",
        error_message: str | None = None,
        depends_on: list[str] | None = None,
        progress_percent: int = 0,
        result_data: dict[str, Any] | None = None,
        # TranscriptionJob fields
        chunks: list[ChunkMetadata] | None = None,
        total_chunks: int = 0,
        processed_chunks: int = 0,
        audio_file_path: str | None = None,
        audio_duration: float | None = None,
        primary_language: str = "es",
    ) -> None:
        super().__init__(
            job_id=job_id,
            session_id=session_id,
            job_type=job_type,
            status=status,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            updated_at=updated_at,
            error_message=error_message,
            depends_on=depends_on,
            progress_percent=progress_percent,
            result_data=result_data,
        )

        if self.job_type != JobType.TRANSCRIPTION:
            self.job_type = JobType(str(JobType.TRANSCRIPTION))

        self.chunks = list(chunks or [])
        self.total_chunks = total_chunks
        self.processed_chunks = processed_chunks
        self.audio_file_path = audio_file_path
        self.audio_duration = audio_duration
        self.primary_language = primary_language

    @classmethod
    def create_for_session(
        cls,
        job_id: str,
        session_id: str,
        total_chunks: int = 0,
    ) -> TranscriptionJob:
        """Create a new transcription job for a session.

        Args:
            job_id: Unique job identifier
            session_id: Parent session identifier
            total_chunks: Expected number of chunks (0 if unknown)

        Returns:
            TranscriptionJob instance
        """
        base_job = Job.create_now(
            job_id=job_id, session_id=session_id, job_type=JobType.TRANSCRIPTION
        )

        return cls(
            job_id=base_job.job_id,
            session_id=base_job.session_id,
            job_type=base_job.job_type,
            status=base_job.status,
            created_at=base_job.created_at,
            updated_at=base_job.updated_at,
            total_chunks=total_chunks,
        )

    def add_chunk(self, chunk: ChunkMetadata) -> None:
        """Add a new chunk to the job.

        Args:
            chunk: Chunk metadata to add
        """
        # Check if chunk already exists
        existing_idx = next(
            (i for i, c in enumerate(self.chunks) if c.chunk_number == chunk.chunk_number),
            None,
        )

        if existing_idx is not None:
            # Update existing chunk
            self.chunks[existing_idx] = chunk
        else:
            # Add new chunk
            self.chunks.append(chunk)
            self.chunks.sort(key=lambda c: c.chunk_number)

        # Update total_chunks if needed
        if chunk.chunk_number + 1 > self.total_chunks:
            self.total_chunks = chunk.chunk_number + 1

    def mark_chunk_completed(
        self,
        chunk_number: int,
        transcript: str,
        duration: float,
        language: str,
        audio_hash: str,
        confidence: float,
        audio_quality: float,
        timestamp_start: float,
        timestamp_end: float,
        created_at: str,
    ) -> None:
        """Mark a chunk as completed with results.

        Args:
            chunk_number: Chunk index
            transcript: Transcribed text
            duration: Audio duration (seconds)
            language: Detected language
            audio_hash: SHA256 hash
            confidence: Transcription confidence (0-1)
            audio_quality: Audio quality score (0-1)
            timestamp_start: Start time (seconds)
            timestamp_end: End time (seconds)
            created_at: Creation timestamp
        """
        chunk_idx = next(
            (i for i, c in enumerate(self.chunks) if c.chunk_number == chunk_number),
            None,
        )

        if chunk_idx is not None:
            chunk = self.chunks[chunk_idx]
            chunk.status = "completed"
            chunk.transcript = transcript
            chunk.duration = duration
            chunk.language = language
            chunk.audio_hash = audio_hash
            chunk.confidence = confidence
            chunk.audio_quality = audio_quality
            chunk.timestamp_start = timestamp_start
            chunk.timestamp_end = timestamp_end
            chunk.created_at = created_at

            # Update job progress
            self.processed_chunks = sum(1 for c in self.chunks if c.status == "completed")
            if self.total_chunks > 0:
                self.progress_percent = int((self.processed_chunks / self.total_chunks) * 100)

    def mark_chunk_failed(self, chunk_number: int, error_message: str) -> None:
        """Mark a chunk as failed.

        Args:
            chunk_number: Chunk index
            error_message: Error description
        """
        chunk_idx = next(
            (i for i, c in enumerate(self.chunks) if c.chunk_number == chunk_number),
            None,
        )

        if chunk_idx is not None:
            self.chunks[chunk_idx].status = "failed"
            self.chunks[chunk_idx].error_message = error_message

    def get_chunk(self, chunk_number: int) -> ChunkMetadata | None:
        """Get chunk metadata by number.

        Args:
            chunk_number: Chunk index

        Returns:
            ChunkMetadata if found, None otherwise
        """
        return next(
            (c for c in self.chunks if c.chunk_number == chunk_number),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "chunks": [
                    {
                        "chunk_number": c.chunk_number,
                        "status": c.status,
                        "audio_size_bytes": c.audio_size_bytes,
                        "audio_hash": c.audio_hash,
                        "transcript": c.transcript,
                        "duration": c.duration,
                        "language": c.language,
                        "confidence": c.confidence,
                        "audio_quality": c.audio_quality,
                        "timestamp_start": c.timestamp_start,
                        "timestamp_end": c.timestamp_end,
                        "created_at": c.created_at,
                        "error_message": c.error_message,
                    }
                    for c in self.chunks
                ],
                "total_chunks": self.total_chunks,
                "processed_chunks": self.processed_chunks,
                "audio_file_path": self.audio_file_path,
                "audio_duration": self.audio_duration,
                "primary_language": self.primary_language,
            }
        )
        return base_dict

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranscriptionJob:
        """Create TranscriptionJob from dictionary.

        Args:
            data: Dictionary with job data

        Returns:
            TranscriptionJob instance
        """
        # Extract chunk data
        chunks_data = data.pop("chunks", [])
        chunks = [ChunkMetadata(**chunk_data) for chunk_data in chunks_data]

        # Create instance (base Job handles enum coercion)
        return cls(chunks=chunks, **data)
