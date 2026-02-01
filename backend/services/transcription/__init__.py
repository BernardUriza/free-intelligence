"""Transcription Service - Public API.

Main classes:
    from backend.services.transcription import TranscriptionService, ChunkProcessingResult
"""

from backend.services.transcription.services.transcription_service import (
    ChunkProcessingResult,
    TranscriptionService,
)

__all__ = ["TranscriptionService", "ChunkProcessingResult"]
