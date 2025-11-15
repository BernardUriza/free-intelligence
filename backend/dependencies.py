"""Dependency Injection providers for FastAPI.

Provides service layer instances with proper DI.
Dependencies are cached within request scope by FastAPI.

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Clean Architecture Refactor
"""

from __future__ import annotations

from backend.services.session_service import SessionService
from backend.services.transcription_service import TranscriptionService


def get_transcription_service() -> TranscriptionService:
    """Provide TranscriptionService instance.

    FastAPI will cache this within the request scope.

    Returns:
        TranscriptionService instance
    """
    return TranscriptionService()


def get_session_service() -> SessionService:
    """Provide SessionService instance.

    FastAPI will cache this within the request scope.

    Returns:
        SessionService instance
    """
    return SessionService()
