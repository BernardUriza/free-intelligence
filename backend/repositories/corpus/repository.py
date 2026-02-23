"""Corpus repository — composed facade over specialised delegates.

Extends ``BaseRepository`` and implements ``ICorpusRepository`` by
delegating to four single-responsibility classes:

* ``DocumentOperations`` — document CRUD
* ``ChunkOperations``    — diarization chunk I/O
* ``SessionReader``      — per-session reads / writes
* ``SessionListing``     — session enumeration and paginated listing

Author: Bernard Uriza Orozco
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union

from backend.utils.common.logging.logger import get_logger
from backend.utils.common.types.type_defs import DiarizationChunkDict

from ..base_repository import BaseRepository
from ..interfaces.icorpus_repository import ICorpusRepository
from ._chunk_ops import ChunkOperations
from ._document_ops import DocumentOperations
from ._session_listing import SessionListing
from ._session_reader import SessionReader

logger = get_logger(__name__)


class CorpusRepository(BaseRepository, ICorpusRepository):
    """HDF5-backed corpus repository.

    Thin facade that wires shared infrastructure (``_open_file``,
    ``_log_operation``) into four delegate objects.  Every public
    method is a one-line delegation.
    """

    # HDF5 top-level groups
    DOCUMENTS_GROUP = "documents"
    CHUNKS_GROUP = "chunks"
    METADATA_GROUP = "metadata"
    SESSIONS_GROUP = "sessions"

    def __init__(self, h5_file_path: Union[str, Path]) -> None:
        super().__init__(h5_file_path)
        self._ensure_structure()

        # -- compose delegates -----------------------------------------------
        self._docs = DocumentOperations(self._open_file, self._log_operation)
        self._chunks = ChunkOperations(self._open_file, self._log_operation)
        self._sessions = SessionReader(self._open_file, self._log_operation)
        self._listing = SessionListing(
            open_file=self._open_file,
            log_operation=self._log_operation,
            h5_file_path=self.h5_file_path,
            get_session_metadata=self._sessions.get_session_metadata,
        )

    # -- structure -----------------------------------------------------------

    def _ensure_structure(self) -> None:
        """Ensure the required HDF5 top-level groups exist."""
        try:
            with self._open_file("a") as f:
                f.require_group(self.DOCUMENTS_GROUP)  # type: ignore[attr-defined]
                f.require_group(self.CHUNKS_GROUP)  # type: ignore[attr-defined]
                f.require_group(self.METADATA_GROUP)  # type: ignore[attr-defined]
            logger.info("CORPUS_STRUCTURE_READY", file_path=str(self.h5_file_path))
        except OSError as e:
            logger.error("CORPUS_STRUCTURE_INIT_FAILED", error=str(e))
            raise

    # ========================================================================
    # Document operations (delegate → DocumentOperations)
    # ========================================================================

    def create(  # type: ignore[override]
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any | None] | None = None,
    ) -> str:
        return self._docs.create(document_id, content, metadata)

    def read(self, document_id: str) -> dict[str, Any | None] | None:  # type: ignore[override]
        return self._docs.read(document_id)

    def update(  # type: ignore[override]
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any | None] | None = None,
    ) -> bool:
        return self._docs.update(document_id, content, metadata)

    def delete(self, document_id: str) -> bool:
        return self._docs.delete(document_id)

    def list_all(self, limit: int | None = None) -> list[dict[str, Any]]:  # type: ignore[override]
        return self._docs.list_all(limit)

    # ========================================================================
    # Chunk operations (delegate → ChunkOperations)
    # ========================================================================

    def add_chunk(self, chunk: DiarizationChunkDict, document_id: str) -> bool:
        return self._chunks.add_chunk(chunk, document_id)

    def get_chunks(self, document_id: str) -> list[DiarizationChunkDict]:
        return self._chunks.get_chunks(document_id)

    # ========================================================================
    # Session read / write (delegate → SessionReader)
    # ========================================================================

    def get_session_metadata(self, session_id: str) -> dict[str, Any] | None:
        return self._sessions.get_session_metadata(session_id)

    def update_session_metadata(
        self, session_id: str, updates: dict[str, Any]
    ) -> bool:
        return self._sessions.update_session_metadata(session_id, updates)

    def get_session_audio(
        self, session_id: str, audio_type: str = "full_audio.webm"
    ) -> bytes | None:
        return self._sessions.get_session_audio(session_id, audio_type)

    def get_session_transcription_chunks(
        self, session_id: str, task_type: str = "TRANSCRIPTION"
    ) -> list[dict[str, Any]]:
        return self._sessions.get_session_transcription_chunks(session_id, task_type)

    def get_session_workflow_state(
        self, session_id: str
    ) -> dict[str, Any] | None:
        return self._sessions.get_session_workflow_state(session_id)

    def get_session_dataset(
        self, session_id: str, dataset_path: str
    ) -> bytes | None:
        return self._sessions.get_session_dataset(session_id, dataset_path)

    def list_session_tasks(self, session_id: str) -> list[str]:
        return self._sessions.list_session_tasks(session_id)

    # ========================================================================
    # Session listing (delegate → SessionListing)
    # ========================================================================

    def list_all_sessions(
        self,
        limit: int | None = None,
        include_deleted: bool = False,
    ) -> list[dict[str, Any]]:
        return self._listing.list_all_sessions(limit, include_deleted)

    def list_all_sessions_with_metadata(
        self,
        limit: int = 20,
        offset: int = 0,
        clinic_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        return self._listing.list_all_sessions_with_metadata(limit, offset, clinic_id)
