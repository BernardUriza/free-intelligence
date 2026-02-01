"""FastAPI Dependency Injection providers for Transcription service.

Provides dependency injection for routers using FastAPI Depends().
Direct repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Updated: 2026-01-31 (Type-safe config validation with Pydantic)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

from backend.domain.session import ISessionRepository
from backend.repositories.hdf5_session_repository import HDF5SessionRepository
from backend.repositories.interfaces import ITaskRepository
from backend.repositories.task_repository import HDF5TaskRepository
from backend.services.transcription.services.di_transcription_service import DITranscriptionService
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger
from backend.config import CORPUS_PATH


class TranscriptionConfig(BaseModel):
    """Type-safe transcription configuration with validation.

    Validation Rules:
        - max_audio_duration: Must be > 0 (seconds)
        - max_chunk_size: Must be > 0 (bytes)
        - language: Must be non-empty string
        - model_name: Must be non-empty string

    Immutability:
        - frozen=True prevents accidental modification after initialization
    """

    max_audio_duration: int = Field(
        gt=0,
        default=7200,  # 2 hours
        description="Maximum audio duration in seconds",
    )
    max_chunk_size: int = Field(
        gt=0,
        default=10485760,  # 10MB
        description="Maximum audio chunk size in bytes",
    )
    language: str = Field(
        min_length=2,
        max_length=10,
        default="es",
        description="Audio language code (ISO 639-1)",
    )
    model_name: str = Field(
        min_length=1,
        default="whisper-large-v3",
        description="Transcription model name",
    )
    enable_diarization: bool = Field(
        default=True,
        description="Enable speaker diarization",
    )
    min_speakers: int = Field(
        ge=1,
        le=10,
        default=1,
        description="Minimum number of speakers",
    )
    max_speakers: int = Field(
        ge=1,
        le=10,
        default=5,
        description="Maximum number of speakers",
    )

    model_config = ConfigDict(frozen=True)


def get_transcription_config() -> TranscriptionConfig:
    """Get transcription configuration from environment variables.

    Environment Variables:
        MAX_AUDIO_DURATION=7200 → Maximum audio duration (seconds)
        MAX_CHUNK_SIZE=10485760 → Maximum chunk size (bytes)
        AUDIO_LANGUAGE=es → Audio language code
        WHISPER_MODEL=whisper-large-v3 → Model name
        ENABLE_DIARIZATION=true → Enable speaker diarization
        MIN_SPEAKERS=1 → Minimum speakers
        MAX_SPEAKERS=5 → Maximum speakers

    Returns:
        TranscriptionConfig instance (immutable, validated)

    Raises:
        ValidationError: If configuration is invalid (e.g., max_audio_duration <= 0)
    """
    return TranscriptionConfig(
        max_audio_duration=int(os.getenv("MAX_AUDIO_DURATION", "7200")),
        max_chunk_size=int(os.getenv("MAX_CHUNK_SIZE", "10485760")),
        language=os.getenv("AUDIO_LANGUAGE", "es"),
        model_name=os.getenv("WHISPER_MODEL", "whisper-large-v3"),
        enable_diarization=os.getenv("ENABLE_DIARIZATION", "true").lower() == "true",
        min_speakers=int(os.getenv("MIN_SPEAKERS", "1")),
        max_speakers=int(os.getenv("MAX_SPEAKERS", "5")),
    )


def get_task_repository() -> ITaskRepository:
    """Get task repository - direct instantiation (Phase 4A).

    Returns:
        ITaskRepository instance (HDF5TaskRepository)

    Note:
        No longer uses service locator (get_container).
        Direct instantiation enables better testability and explicit dependencies.
        Referential integrity (Fix #5) is OPTIONAL - only enabled when session_repository
        is explicitly injected (not needed for most operations).
    """
    return HDF5TaskRepository(CORPUS_PATH)


def get_session_repository() -> ISessionRepository:
    """Get session repository - direct instantiation (Phase 4A).

    Returns:
        ISessionRepository instance (HDF5SessionRepository with typed dataclasses from Fix #3)

    Note:
        Migrated from legacy SessionRepository to HDF5SessionRepository (Phase 3/4A).
        Now uses typed dataclasses (SessionHDF5Metadata) instead of Dict[str, Any].
        Cascade delete (Fix #5) is OPTIONAL - only enabled when task_repository
        is explicitly injected (not needed for most operations).
    """
    return HDF5SessionRepository(CORPUS_PATH)


def get_transcription_logger() -> ILogger:
    """Get logger for transcription service.

    Returns:
        ILogger instance
    """
    return get_logger("transcription")


def get_transcription_service() -> DITranscriptionService:
    """Get transcription service with injected dependencies.

    FastAPI provider for DITranscriptionService.

    Returns:
        DITranscriptionService instance with task_repository, session_repository, logger, and config

    Type-Safe Config:
        Config is validated via Pydantic (fail-fast on invalid values like negative max_audio_duration).
    """
    return DITranscriptionService(
        task_repository=get_task_repository(),
        session_repository=get_session_repository(),
        logger=get_transcription_logger(),
        config=get_transcription_config(),
    )
