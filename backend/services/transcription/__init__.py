"""Transcription service package.

Complete audio transcription solution with:
  - Session and file validation
  - Whisper model management (lazy loading, singleton)
  - Audio format conversion (ffmpeg)
  - Transcription and result assembly

Structure:
  - service.py: Main TranscriptionService class
  - whisper.py: Whisper model management
  - validators.py: Validation logic

Card: FI-BACKEND-FEAT-003
"""

from __future__ import annotations

from backend.services.transcription.service import TranscriptionService

__all__ = ["TranscriptionService"]
