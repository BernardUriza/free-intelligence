"""Whisper service wrapper.

Re-exports from backend.services.whisper_service for backward compatibility.
"""

from __future__ import annotations

from backend.services.whisper_service import is_whisper_available, transcribe_audio

__all__ = ["is_whisper_available", "transcribe_audio"]
