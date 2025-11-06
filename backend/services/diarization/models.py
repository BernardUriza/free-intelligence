"""Diarization data models.

Dataclasses for diarization workflow:
  - DiarizationSegment: Single transcribed segment with speaker label
  - DiarizationResult: Complete diarization result with metadata
  - DiarizationJob: Job state for HDF5-backed job management
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


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
class DiarizationJob:
    """Diarization job metadata for HDF5 storage.

    Tracks async diarization job state and progress.
    """

    job_id: str  # UUID v4
    session_id: str  # Session identifier
    audio_file_path: str  # Path to audio file
    audio_file_size: int  # File size in bytes
    status: str  # pending | in_progress | completed | failed
    progress_percent: int  # 0-100
    created_at: str  # ISO 8601 timestamp
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result_path: Optional[str] = None  # Path to result in corpus.h5
    # Additional progress fields
    processed_chunks: int = 0  # Chunks processed
    total_chunks: int = 0  # Total chunks
    last_event: str = ""  # Last event description
    updated_at: str = ""  # Last update timestamp
    # Result cache
    result_data: Optional[dict[str, Any]] = None  # Cached diarization result
