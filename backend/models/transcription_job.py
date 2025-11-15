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

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.models.job import Job, JobStatus, JobType


@dataclass
class ChunkMetadata:
    """Metadata for a single audio chunk.

    This tracks the processing state of each chunk within a TranscriptionJob.
    """

    chunk_number: int
    status: str  # Union[pending, processing, completed] | failed
    audio_size_bytes: int
    audio_hash: Optional[str] = None
    transcript: Optional[str] = None
    duration: Optional[float] = None
    language: Optional[str] = None
    confidence: Optional[float] = None  # 0-1 (normalized avg_logprob)
    audio_quality: Optional[float] = None  # 0-1 (heuristic: words/second)
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    created_at: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
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

    chunks: list[ChunkMetadata] = field(default_factory=list)
    total_chunks: int = 0
    processed_chunks: int = 0
    audio_file_path: Optional[str] = None
    audio_duration: Optional[float] = None
    primary_language: str = "es"  # Default to Spanish

    def __post_init__(self):
        """Ensure job_type is transcription."""
        super().__post_init__()
        if self.job_type != JobType.TRANSCRIPTION:
            self.job_type = JobType.TRANSCRIPTION

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
            job_id=job_id,
            session_id=session_id,
            job_type=JobType.TRANSCRIPTION,
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

    def get_chunk(self, chunk_number: int) -> Optional[ChunkMetadata]:
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

        # Convert string enums to enum instances (from base Job)
        if isinstance(data.get("job_type"), str):
            data["job_type"] = JobType(data["job_type"])
        if isinstance(data.get("status"), str):
            data["status"] = JobStatus(data["status"])

        # Create instance
        return cls(chunks=chunks, **data)
