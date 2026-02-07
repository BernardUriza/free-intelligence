"""HDF5 Task Repository - Combined implementation.

Combines all mixins into the final HDF5TaskRepository class.
This is the main entry point for task storage operations.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor from monolithic task_repository.py)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from backend.repositories.interfaces.itask_repository import ITaskRepository

from .base import HDF5Base
from .chunks_mixin import TaskChunksMixin
from .diarization_mixin import DiarizationMixin
from .metadata_mixin import TaskMetadataMixin
from .orders_mixin import OrdersMixin
from .soap_mixin import SOAPMixin
from .transcription_mixin import TranscriptionMixin

if TYPE_CHECKING:
    from backend.domain.session import ISessionRepository


class HDF5TaskRepository(
    HDF5Base,
    TaskMetadataMixin,
    TaskChunksMixin,
    DiarizationMixin,
    SOAPMixin,
    OrdersMixin,
    TranscriptionMixin,
    ITaskRepository,
):
    """HDF5-based implementation of ITaskRepository.

    Storage-agnostic interface - internal HDF5 structure is an implementation detail.
    Tasks are stored with metadata and optional chunks, organized by session and type.
    Structure may change without affecting domain layer.

    This class combines multiple mixins for:
    - Task metadata (CRUD, progress)
    - Audio chunks (batch updates, audio bytes)
    - Diarization (speaker segments)
    - SOAP notes (clinical data)
    - Orders (clinical orders)
    - Transcription (WebSpeech, full text, full audio)

    Example:
        >>> repo = HDF5TaskRepository("/data/tasks.h5")
        >>> repo.ensure_task_exists("session-123", "TRANSCRIPTION")
        >>> repo.save_task_metadata("session-123", "TRANSCRIPTION", {"status": "pending"})
    """

    def __init__(
        self,
        h5_file_path: str | Path,
        session_repository: "ISessionRepository | None" = None,
    ):
        """Initialize task repository.

        Args:
            h5_file_path: Path to HDF5 database file
            session_repository: Optional session repository for referential integrity
        """
        super().__init__(h5_file_path, session_repository)
