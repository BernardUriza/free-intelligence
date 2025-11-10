"""Compatibility wrapper for diarization service.

This module provides backward compatibility for code that imports from
the old 'backend.services.diarization_service' location. The actual
service is in backend.services.diarization.service.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from backend.services.diarization.service import DiarizationService

# Create a singleton service instance
_service_instance: Optional[DiarizationService] = None


def get_service() -> DiarizationService:
    """Get or create the singleton DiarizationService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DiarizationService()
    return _service_instance


async def diarize_audio(
    audio_path: str,
    session_id: str,
    language: str = "es",
    persist: bool = True,
    progress_callback: Optional[Callable[[int, int, int, str], None]] = None,
) -> dict[str, Any]:
    """Diarize audio file - wrapper around DiarizationService.

    Args:
        audio_path: Path to audio file
        session_id: Session identifier
        language: Language code (default: 'es')
        persist: Whether to persist result to storage
        progress_callback: Callback for progress updates

    Returns:
        Diarization result dict
    """
    service = get_service()
    return await service.diarize(
        audio_path=audio_path,
        session_id=session_id,
        language=language,
        persist=persist,
        progress_callback=progress_callback,
    )


__all__ = ["diarize_audio", "DiarizationService", "get_service"]
