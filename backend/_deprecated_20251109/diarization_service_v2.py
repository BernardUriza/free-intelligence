"""Parallel diarization service (v2) - compatibility wrapper.

This module provides a parallel/optimized version of diarization.
For now, it falls back to the standard diarization service (v1).

TODO: Implement actual parallel processing with chunking and optimization.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from backend.services.diarization_service import diarize_audio


async def diarize_audio_parallel(
    audio_path: str,
    session_id: str,
    language: str = "es",
    persist: bool = True,
    progress_callback: Optional[Callable[[int, int, int, str], None]] = None,
) -> dict[str, Any]:
    """Diarize audio in parallel - falls back to v1 for now.

    Args:
        audio_path: Path to audio file
        session_id: Session identifier
        language: Language code (default: 'es')
        persist: Whether to persist result to storage
        progress_callback: Callback for progress updates

    Returns:
        Diarization result dict

    Note:
        This is a v2 wrapper that currently falls back to v1 (diarize_audio).
        Future optimization: implement actual parallel processing with:
        - Audio chunking
        - Parallel processing
        - Merged result aggregation
    """
    # TODO: Implement actual parallel diarization
    # For now, fall back to v1
    return await diarize_audio(
        audio_path=audio_path,
        session_id=session_id,
        language=language,
        persist=persist,
        progress_callback=progress_callback,
    )


__all__ = ["diarize_audio_parallel"]
