"""Transcription Service - Public API.

Main classes:
    from backend.core.services.transcription import TranscriptionService, ChunkProcessingResult
"""

from backend.core.services.transcription.services.transcription_service import (
    ChunkProcessingResult,
    TranscriptionService,
)

__all__ = ["TranscriptionService", "ChunkProcessingResult"]
