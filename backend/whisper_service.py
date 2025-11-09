"""Whisper service wrapper.

Re-exports from backend.services.whisper_service for backward compatibility.
"""

from __future__ import annotations

from backend.services.whisper_service import *  # type: ignore[import]  # noqa: F403

__all__ = ["get_whisper_model", "is_whisper_available", "transcribe_audio"]
