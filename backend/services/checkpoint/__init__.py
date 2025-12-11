"""Checkpoint Service - Clean Architecture Implementation.

This package provides audio checkpoint functionality using Clean Architecture
(Hexagonal Architecture) principles:

Layers:
- domain/: Immutable value objects and domain logic
- ports/: Abstract interfaces (protocols)
- adapters/: Concrete implementations (HDF5, FFmpeg)
- usecases/: Application business logic

Usage:
    from backend.services.checkpoint import create_checkpoint_service

    # Create service with default adapters
    service = create_checkpoint_service()

    # Execute checkpoint
    from backend.services.checkpoint import CheckpointRequest, AudioFormat
    request = CheckpointRequest(
        session_id="abc123",
        last_checkpoint_idx=-1,
        new_checkpoint_idx=5,
        output_format=AudioFormat.WEBM,
    )
    result = service.execute(request)

Benefits:
- Testability: Ports can be mocked for unit tests
- Flexibility: Swap implementations without changing business logic
- Maintainability: Clear separation of concerns
- Robustness: Immutable objects prevent state corruption
"""

# Domain exports
# Adapter exports (for direct use if needed)
from .adapters import FFmpegConcatenator, HDF5AudioRepository
from .domain import (
    AudioChunk,
    AudioFormat,
    CheckpointRange,
    CheckpointResult,
    SessionId,
)

# Port exports (for type hints and testing)
from .ports import AudioConcatenatorPort, AudioRepositoryPort

# Use case exports
from .usecases import CheckpointUseCase
from .usecases.checkpoint_use_case import (
    CheckpointError,
    CheckpointRequest,
    NoChunksToProcessError,
    TooManyChunksError,
)


def create_checkpoint_service() -> CheckpointUseCase:
    """Factory function to create a CheckpointUseCase with default adapters.

    Returns:
        Configured CheckpointUseCase ready for use

    Example:
        service = create_checkpoint_service()
        result = service.execute(request)
    """
    repository = HDF5AudioRepository()
    concatenator = FFmpegConcatenator()
    return CheckpointUseCase(
        audio_repository=repository,
        audio_concatenator=concatenator,
    )


__all__ = [
    # Domain
    "AudioChunk",
    "AudioFormat",
    "CheckpointRange",
    "CheckpointResult",
    "SessionId",
    # Ports
    "AudioConcatenatorPort",
    "AudioRepositoryPort",
    # Use cases
    "CheckpointUseCase",
    "CheckpointRequest",
    "CheckpointError",
    "NoChunksToProcessError",
    "TooManyChunksError",
    # Adapters
    "FFmpegConcatenator",
    "HDF5AudioRepository",
    # Factory
    "create_checkpoint_service",
]
