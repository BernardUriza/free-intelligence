"""Diarization data models.

Dataclasses for diarization workflow:
  - DiarizationSegment: Single transcribed segment with speaker label
  - DiarizationResult: Complete diarization result with metadata
  - DiarizationJob: Job state for HDF5-backed job management (inherits from Job)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from backend.models import Job, JobStatus, JobType


@dataclass
class DiarizationSegment:
    """Single diarized segment with speaker label.

    Input from TranscriptionService: start_time, end_time, text (raw)
    Output after diarization: same fields + speaker, improved_text
    """

    start_time: float  # Seconds in audio
    end_time: float  # Seconds in audio
    speaker: str  # PACIENTE | MEDICO | DESCONOCIDO
    text: str  # Transcribed text (raw from Whisper)
    improved_text: Optional[str] = None  # After LLM improvement (ortografía, gramática)
    confidence: Optional[float] = None  # Optional confidence score from LLM


@dataclass
class DiarizationResult:
    """Complete diarization result with metadata.

    Returned from DiarizationService.diarize_segments()
    """

    session_id: str
    audio_file_path: str
    audio_file_hash: str
    duration_sec: float
    language: str
    segments: list[DiarizationSegment]
    processing_time_sec: float
    created_at: str
    model_llm: str = "qwen2.5:7b-instruct-q4_0"  # Ollama model used


@dataclass
class DiarizationJob(Job):
    """Diarization job metadata for HDF5 storage.

    Inherits from Job and adds diarization-specific fields.
    Tracks async diarization job state and progress.

    Attributes:
        audio_file_path: Path to audio file
        audio_file_size: File size in bytes
        result_path: Path to result in corpus.h5 (optional)
        processed_chunks: Number of chunks processed
        total_chunks: Total number of chunks expected
        last_event: Last event description
    """

    audio_file_path: str = ""
    audio_file_size: int = 0
    result_path: Optional[str] = None
    processed_chunks: int = 0
    total_chunks: int = 0
    last_event: str = ""

    def __post_init__(self):
        """Ensure job_type is diarization."""
        super().__post_init__()
        if self.job_type != JobType.DIARIZATION:
            self.job_type = JobType.DIARIZATION

    @classmethod
    def create_for_session(
        cls,
        job_id: str,
        session_id: str,
        audio_file_path: str,
        audio_file_size: int,
        total_chunks: int = 0,
    ) -> DiarizationJob:
        """Create a new diarization job for a session.

        Args:
            job_id: Unique job identifier
            session_id: Parent session identifier
            audio_file_path: Path to audio file
            audio_file_size: File size in bytes
            total_chunks: Expected number of chunks (0 if unknown)

        Returns:
            DiarizationJob instance
        """
        base_job = Job.create_now(
            job_id=job_id,
            session_id=session_id,
            job_type=JobType.DIARIZATION,
        )

        return cls(
            job_id=base_job.job_id,
            session_id=base_job.session_id,
            job_type=base_job.job_type,
            status=base_job.status,
            created_at=base_job.created_at,
            updated_at=base_job.updated_at,
            audio_file_path=audio_file_path,
            audio_file_size=audio_file_size,
            total_chunks=total_chunks,
            last_event="JOB_CREATED",
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "audio_file_path": self.audio_file_path,
                "audio_file_size": self.audio_file_size,
                "result_path": self.result_path,
                "processed_chunks": self.processed_chunks,
                "total_chunks": self.total_chunks,
                "last_event": self.last_event,
            }
        )
        return base_dict

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiarizationJob:
        """Create DiarizationJob from dictionary.

        Args:
            data: Dictionary with job data

        Returns:
            DiarizationJob instance
        """
        # Convert string enums to enum instances (from base Job)
        if isinstance(data.get("job_type"), str):
            data["job_type"] = JobType(data["job_type"])
        if isinstance(data.get("status"), str):
            data["status"] = JobStatus(data["status"])

        # Create instance
        return cls(**data)
