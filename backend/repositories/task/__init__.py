"""Task Repository Package - HDF5-based task management.

Provides HDF5TaskRepository for task lifecycle management:
- Task creation and metadata storage
- Task chunks management
- Diarization segments
- SOAP notes
- Clinical orders
- Transcription data

Architecture:
- Uses mixin pattern for separation of concerns
- Each mixin handles a specific domain
- Base class provides HDF5 utilities and serialization

Example:
    >>> from backend.repositories.task import HDF5TaskRepository
    >>> repo = HDF5TaskRepository("/data/tasks.h5")
    >>> repo.ensure_task_exists("session-123", "TRANSCRIPTION")

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor from monolithic task_repository.py)
"""

from .repository import HDF5TaskRepository

__all__ = ["HDF5TaskRepository"]
