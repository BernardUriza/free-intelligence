"""Repository for corpus data operations.

Handles all HDF5 operations for corpus documents, chunks, and metadata.
Centralizes data access logic that was previously scattered across multiple files.

Clean Code: Single Responsibility - this class only handles corpus data access,
not business logic or API concerns.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Union, cast

import h5py
import numpy as np
from backend.utils.common.logging.logger import get_logger
from backend.utils.common.types.type_defs import DiarizationChunkDict
from pathlib import Path

from .base_repository import BaseRepository
from .interfaces.icorpus_repository import ICorpusRepository

logger = get_logger(__name__)


class CorpusRepository(BaseRepository, ICorpusRepository):
    """Repository for corpus document management in HDF5.

    Responsibilities:
    - Store and retrieve corpus documents
    - Manage document versions and metadata
    - Handle chunk operations (add, update, list)
    - Enforce append-only semantics
    """

    # HDF5 group names
    DOCUMENTS_GROUP = "documents"
    CHUNKS_GROUP = "chunks"
    METADATA_GROUP = "metadata"
    SESSIONS_GROUP = "sessions"

    def __init__(self, h5_file_path: Union[str, Path]) -> None:
        """Initialize corpus repository.

        Args:
            h5_file_path: Path to HDF5 corpus file
        """
        super().__init__(h5_file_path)
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure required HDF5 group structure exists."""
        try:
            with self._open_file("a") as f:
                f.require_group(self.DOCUMENTS_GROUP)  # type: ignore[attr-defined]
                f.require_group(self.CHUNKS_GROUP)  # type: ignore[attr-defined]
                f.require_group(self.METADATA_GROUP)  # type: ignore[attr-defined]
            logger.info("CORPUS_STRUCTURE_READY", file_path=str(self.h5_file_path))
        except OSError as e:
            logger.error("CORPUS_STRUCTURE_INIT_FAILED", error=str(e))
            raise

    def create(  # type: ignore[override]
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any | None] | None = None,
    ) -> str:
        """Create new corpus document.

        Args:
            document_id: Unique document identifier
            content: Document content
            metadata: Optional metadata (author, source, tags, etc.)

        Returns:
            Document ID

        Raises:
            ValueError: If document_id is empty or content is invalid
            IOError: If HDF5 operation fails
        """
        if not document_id or not content:
            raise ValueError("document_id and content are required")

        try:
            with self._open_file("r+") as f:
                doc_group = f[self.DOCUMENTS_GROUP]

                # Append-only: check if document already exists
                if document_id in doc_group:  # type: ignore[operator]
                    raise ValueError(f"Document {document_id} already exists")

                # Create document dataset
                dataset = doc_group.create_dataset(  # type: ignore[attr-defined]
                    document_id,
                    data=content.encode("utf-8"),
                    dtype=h5py.string_dtype(encoding="utf-8"),  # type: ignore[attr-defined]
                )

                # Store metadata
                if metadata:
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            dataset.attrs[key] = value
                        elif isinstance(value, (list, dict)):
                            dataset.attrs[key] = json.dumps(value)

                dataset.attrs["created_at"] = datetime.now(UTC).isoformat()
                dataset.attrs["version"] = 1

            self._log_operation("create", document_id)
            return document_id

        except Exception as e:
            self._log_operation("create", document_id, status="failed", error=str(e))
            raise

    def read(self, document_id: str) -> dict[str, Any | None] | None:  # type: ignore[override]
        """Read corpus document.

        Args:
            document_id: Document identifier

        Returns:
            Document data with metadata, or None if not found
        """
        try:
            with self._open_file("r") as f:
                if document_id not in f[self.DOCUMENTS_GROUP]:  # type: ignore[operator]
                    return None

                dataset = f[self.DOCUMENTS_GROUP][document_id]  # type: ignore[index]
                content = (
                    dataset[()].decode("utf-8") if isinstance(dataset[()], bytes) else dataset[()]  # type: ignore[index]
                )

                # Extract metadata
                metadata = dict(dataset.attrs)  # type: ignore[attr-defined]
                return {
                    "document_id": document_id,
                    "content": content,
                    "metadata": metadata,
                }

        except Exception as e:
            logger.error("CORPUS_READ_FAILED", document_id=document_id, error=str(e))
            return None

    def update(  # type: ignore[override]
        self, document_id: str, content: str, metadata: dict[str, Any | None] | None = None
    ) -> bool:
        """Update corpus document (enforces append-only by creating new version).

        In append-only mode, updates create a new version of the document.

        Args:
            document_id: Document identifier
            content: New content
            metadata: Updated metadata

        Returns:
            True if update successful
        """
        try:
            with self._open_file("r+") as f:
                if document_id not in f[self.DOCUMENTS_GROUP]:  # type: ignore[operator]
                    return False

                dataset = f[self.DOCUMENTS_GROUP][document_id]  # type: ignore[index]
                current_version = int(dataset.attrs.get("version", 1))  # type: ignore[attr-defined]
                new_version = current_version + 1

                # Store new version info
                dataset.attrs["updated_at"] = datetime.now(UTC).isoformat()  # type: ignore[attr-defined]
                dataset.attrs["version"] = new_version  # type: ignore[attr-defined]
                dataset.attrs[f"version_{new_version}_content"] = content.encode("utf-8")  # type: ignore[attr-defined]

                if metadata:
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            dataset.attrs[f"version_{new_version}_{key}"] = value  # type: ignore[attr-defined]

            self._log_operation("update", document_id)
            return True

        except Exception as e:
            self._log_operation("update", document_id, status="failed", error=str(e))
            return False

    def delete(self, document_id: str) -> bool:  # type: ignore[override]
        """Delete corpus document (marks as deleted in append-only mode).

        Args:
            document_id: Document identifier

        Returns:
            True if deletion successful
        """
        try:
            with self._open_file("r+") as f:
                if document_id not in f[self.DOCUMENTS_GROUP]:  # type: ignore[operator]
                    return False

                dataset = f[self.DOCUMENTS_GROUP][document_id]  # type: ignore[index]
                dataset.attrs["deleted_at"] = datetime.now(UTC).isoformat()  # type: ignore[attr-defined]
                dataset.attrs["is_deleted"] = True  # type: ignore[attr-defined]

            self._log_operation("delete", document_id)
            return True

        except Exception as e:
            self._log_operation("delete", document_id, status="failed", error=str(e))
            return False

    def list_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        """List all documents in corpus.

        Args:
            limit: Maximum documents to return

        Returns:
            List of documents (metadata only)
        """
        try:
            with self._open_file("r") as f:
                docs_group = f[self.DOCUMENTS_GROUP]
                doc_ids = list(docs_group.keys())  # type: ignore[attr-defined]

                if limit:
                    doc_ids = doc_ids[:limit]

                results = []
                for doc_id in doc_ids:
                    doc_data = self.read(doc_id)
                    if doc_data:
                        metadata = doc_data.get("metadata") or {}
                        if not metadata.get("is_deleted", False):
                            results.append(doc_data)

                return results

        except Exception as e:
            logger.error("CORPUS_LIST_FAILED", error=str(e))
            return []

    def add_chunk(self, chunk: DiarizationChunkDict, document_id: str) -> bool:
        """Add diarization chunk to document.

        Args:
            chunk: Chunk data (from diarization)
            document_id: Parent document ID

        Returns:
            True if chunk added successfully
        """
        try:
            chunk_idx = chunk.get("chunk_idx", 0)
            chunk_id = f"{document_id}_chunk_{chunk_idx}"

            with self._open_file("r+") as f:
                chunks_group = f[self.CHUNKS_GROUP]
                chunk_group = chunks_group.create_group(chunk_id)  # type: ignore[attr-defined]

                # Store chunk data
                for key, value in chunk.items():
                    if isinstance(value, (str, int, float)):
                        chunk_group.attrs[key] = value

            self._log_operation("create_chunk", chunk_id)
            return True

        except Exception as e:
            logger.error("CHUNK_ADD_FAILED", document_id=document_id, error=str(e))
            return False

    def get_chunks(self, document_id: str) -> list[DiarizationChunkDict]:
        """Get all chunks for document.

        Args:
            document_id: Document identifier

        Returns:
            List of chunks
        """
        try:
            with self._open_file("r") as f:
                chunks_group = f[self.CHUNKS_GROUP]
                chunks = []

                for chunk_id in chunks_group:  # type: ignore[attr-defined]
                    if chunk_id.startswith(document_id):
                        chunk_group = chunks_group[chunk_id]  # type: ignore[index]
                        chunk_data: dict[str, Any] = {}
                        for key, value in chunk_group.attrs.items():  # type: ignore[attr-defined]
                            chunk_data[str(key)] = value
                        chunks.append(cast(DiarizationChunkDict, chunk_data))

                return sorted(chunks, key=lambda c: c.get("chunk_idx", 0))

        except Exception as e:
            logger.error("CHUNKS_READ_FAILED", document_id=document_id, error=str(e))
            return []

    # ========================================================================
    # Session Operations (for API access)
    # ========================================================================

    def get_session_metadata(self, session_id: str) -> dict[str, Any] | None:
        """Get session metadata from corpus.

        Args:
            session_id: Session identifier

        Returns:
            Session metadata dict or None if not found
        """
        try:
            with self._open_file("r") as f:
                session_path = f"{self.SESSIONS_GROUP}/{session_id}"
                if session_path not in f:
                    return None

                session_group = f[session_path]
                metadata = dict(session_group.attrs)

                # Check if there's a meta dataset
                if "meta" in session_group:
                    meta_ds = session_group["meta"]
                    if isinstance(meta_ds, h5py.Dataset):
                        meta_bytes = bytes(meta_ds[()])
                        meta_json = json.loads(meta_bytes.decode("utf-8"))
                        metadata.update(meta_json)

                logger.debug("SESSION_METADATA_READ", session_id=session_id)
                return metadata

        except Exception as e:
            logger.error("GET_SESSION_METADATA_FAILED", session_id=session_id, error=str(e))
            return None

    def update_session_metadata(self, session_id: str, updates: dict[str, Any]) -> bool:
        """Update session metadata in corpus (merge with existing).

        Args:
            session_id: Session identifier
            updates: Dictionary of metadata fields to update/add

        Returns:
            True if update successful, False otherwise
        """
        try:
            with self._open_file("a") as f:
                session_path = f"{self.SESSIONS_GROUP}/{session_id}"
                if session_path not in f:
                    logger.warning("SESSION_NOT_FOUND_FOR_UPDATE", session_id=session_id)
                    return False

                session_group = f[session_path]

                # Get existing metadata from meta dataset or create new
                existing_meta: dict[str, Any] = {}
                if "meta" in session_group:
                    meta_ds = session_group["meta"]
                    if isinstance(meta_ds, h5py.Dataset):
                        meta_bytes = bytes(meta_ds[()])
                        existing_meta = json.loads(meta_bytes.decode("utf-8"))
                    del session_group["meta"]

                # Merge updates into existing metadata
                existing_meta.update(updates)

                # Write updated metadata
                meta_bytes = json.dumps(existing_meta).encode("utf-8")
                session_group.create_dataset(
                    "meta",
                    data=np.frombuffer(meta_bytes, dtype=np.uint8),
                    compression="gzip",
                )

                logger.info(
                    "SESSION_METADATA_UPDATED",
                    session_id=session_id,
                    updated_keys=list(updates.keys()),
                )
                return True

        except Exception as e:
            logger.error("UPDATE_SESSION_METADATA_FAILED", session_id=session_id, error=str(e))
            return False

    def get_session_audio(self, session_id: str, audio_type: str = "full_audio.webm") -> bytes | None:
        """Get audio bytes from session.

        Args:
            session_id: Session identifier
            audio_type: Audio dataset name (default: full_audio.webm)

        Returns:
            Audio bytes or None if not found
        """
        try:
            with self._open_file("r") as f:
                audio_path = f"{self.SESSIONS_GROUP}/{session_id}/{audio_type}"
                if audio_path not in f:
                    return None

                audio_dataset = f[audio_path]
                audio_bytes = bytes(audio_dataset[()])

                logger.debug(
                    "SESSION_AUDIO_READ",
                    session_id=session_id,
                    audio_type=audio_type,
                    size_bytes=len(audio_bytes)
                )
                return audio_bytes

        except Exception as e:
            logger.error(
                "GET_SESSION_AUDIO_FAILED",
                session_id=session_id,
                audio_type=audio_type,
                error=str(e)
            )
            return None

    def get_session_transcription_chunks(self, session_id: str, task_type: str = "TRANSCRIPTION") -> list[dict[str, Any]]:
        """Get transcription chunks from session.

        Args:
            session_id: Session identifier
            task_type: Task type (default: TRANSCRIPTION)

        Returns:
            List of chunk dicts with metadata
        """
        try:
            with self._open_file("r") as f:
                chunks_path = f"{self.SESSIONS_GROUP}/{session_id}/tasks/{task_type}/chunks"
                if chunks_path not in f:
                    return []

                chunks_group = f[chunks_path]
                chunks = []

                for chunk_name in chunks_group.keys():
                    chunk_group = chunks_group[chunk_name]
                    chunk_data = {"chunk_name": chunk_name}

                    # Read attrs
                    for key, value in chunk_group.attrs.items():
                        chunk_data[key] = value

                    # Read transcript if exists
                    if "transcript" in chunk_group:
                        transcript_ds = chunk_group["transcript"]
                        if isinstance(transcript_ds, h5py.Dataset):
                            transcript_bytes = bytes(transcript_ds[()])
                            chunk_data["transcript"] = transcript_bytes.decode("utf-8")

                    chunks.append(chunk_data)

                logger.debug(
                    "SESSION_CHUNKS_READ",
                    session_id=session_id,
                    task_type=task_type,
                    chunk_count=len(chunks)
                )
                return chunks

        except Exception as e:
            logger.error(
                "GET_SESSION_CHUNKS_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e)
            )
            return []

    def get_session_workflow_state(self, session_id: str) -> dict[str, Any] | None:
        """Get workflow state from session.

        Args:
            session_id: Session identifier

        Returns:
            Workflow state dict or None if not found
        """
        try:
            with self._open_file("r") as f:
                workflow_path = f"{self.SESSIONS_GROUP}/{session_id}/workflow"
                if workflow_path not in f:
                    return None

                workflow_group = f[workflow_path]
                workflow_state = dict(workflow_group.attrs)

                # Check if there's a state dataset
                if "state" in workflow_group:
                    state_ds = workflow_group["state"]
                    if isinstance(state_ds, h5py.Dataset):
                        state_bytes = bytes(state_ds[()])
                        state_json = json.loads(state_bytes.decode("utf-8"))
                        workflow_state.update(state_json)

                logger.debug("WORKFLOW_STATE_READ", session_id=session_id)
                return workflow_state

        except Exception as e:
            logger.error("GET_WORKFLOW_STATE_FAILED", session_id=session_id, error=str(e))
            return None

    def list_all_sessions(
        self,
        limit: int | None = None,
        include_deleted: bool = False
    ) -> list[dict[str, Any]]:
        """List all sessions in corpus.

        Args:
            limit: Maximum sessions to return
            include_deleted: Include deleted sessions

        Returns:
            List of sessions with metadata
        """
        try:
            with self._open_file("r") as f:
                if self.SESSIONS_GROUP not in f:
                    return []

                sessions_group = f[self.SESSIONS_GROUP]
                session_ids = list(sessions_group.keys())

                if limit:
                    session_ids = session_ids[:limit]

                results = []
                for session_id in session_ids:
                    session_meta = self.get_session_metadata(session_id)
                    if session_meta:
                        is_deleted = session_meta.get("deleted_at") is not None
                        if include_deleted or not is_deleted:
                            results.append({
                                "session_id": session_id,
                                "metadata": session_meta
                            })

                logger.debug("SESSIONS_LIST_READ", count=len(results))
                return results

        except Exception as e:
            logger.error("LIST_SESSIONS_FAILED", error=str(e))
            return []

    def get_session_dataset(self, session_id: str, dataset_path: str) -> bytes | None:
        """Get raw bytes from session dataset (generic accessor).

        Args:
            session_id: Session identifier
            dataset_path: Relative path to dataset (e.g., "tasks/TRANSCRIPTION/webspeech_final")

        Returns:
            Dataset bytes or None if not found
        """
        try:
            with self._open_file("r") as f:
                full_path = f"{self.SESSIONS_GROUP}/{session_id}/{dataset_path}"
                if full_path not in f:
                    return None

                dataset = f[full_path]
                dataset_bytes = bytes(dataset[()])

                logger.debug(
                    "SESSION_DATASET_READ",
                    session_id=session_id,
                    dataset_path=dataset_path,
                    size_bytes=len(dataset_bytes)
                )
                return dataset_bytes

        except Exception as e:
            logger.error(
                "GET_SESSION_DATASET_FAILED",
                session_id=session_id,
                dataset_path=dataset_path,
                error=str(e)
            )
            return None

    def list_session_tasks(self, session_id: str) -> list[str]:
        """List all task types in session.

        Args:
            session_id: Session identifier

        Returns:
            List of task type names (e.g., ["TRANSCRIPTION", "DIARIZATION"])
        """
        try:
            with self._open_file("r") as f:
                tasks_path = f"{self.SESSIONS_GROUP}/{session_id}/tasks"
                if tasks_path not in f:
                    return []

                tasks_group = f[tasks_path]
                task_types = list(tasks_group.keys())

                logger.debug(
                    "SESSION_TASKS_LISTED",
                    session_id=session_id,
                    task_count=len(task_types)
                )
                return task_types

        except Exception as e:
            logger.error(
                "LIST_SESSION_TASKS_FAILED",
                session_id=session_id,
                error=str(e)
            )
            return []

    # =========================================================================
    # Private Helpers for list_all_sessions_with_metadata
    # =========================================================================

    def _extract_session_created_at(self, tasks: Any) -> str:
        """Extract created_at timestamp from session tasks.

        Priority:
        1. TRANSCRIPTION task metadata
        2. First chunk (chunk_0) created_at
        3. Fallback to epoch date

        Returns:
            ISO timestamp string
        """
        if "TRANSCRIPTION" not in tasks:
            return "2000-01-01T00:00:00+00:00"

        trans_task = tasks["TRANSCRIPTION"]

        # Try metadata first
        if "metadata" in trans_task:
            meta_ds = trans_task["metadata"]
            if isinstance(meta_ds, h5py.Dataset):
                meta_json = meta_ds[()].decode("utf-8")
                meta = json.loads(meta_json)
                if meta.get("created_at"):
                    return meta["created_at"]

        # Fallback: first chunk
        if "chunks" in trans_task and "chunk_0" in trans_task["chunks"]:
            chunk_0 = trans_task["chunks"]["chunk_0"]
            if "created_at" in chunk_0:
                created_at_ds = chunk_0["created_at"]
                if isinstance(created_at_ds, h5py.Dataset):
                    return created_at_ds[()].decode("utf-8")

        return "2000-01-01T00:00:00+00:00"

    def _extract_transcription_details(
        self, tasks: Any, session_id: str
    ) -> tuple[int, float, str]:
        """Extract transcription details from session tasks.

        Returns:
            Tuple of (chunk_count, duration_seconds, preview)
        """
        if "TRANSCRIPTION" not in tasks:
            return (0, 0.0, "")

        trans_task = tasks["TRANSCRIPTION"]
        if "chunks" not in trans_task:
            return (0, 0.0, "")

        chunks_group = trans_task["chunks"]
        chunk_count = len(chunks_group.keys())
        duration_seconds = 0.0
        preview = ""

        if chunk_count == 0:
            return (0, 0.0, "")

        try:
            # Get preview from first chunk
            if "chunk_0" in chunks_group:
                chunk_0 = chunks_group["chunk_0"]
                if "transcript" in chunk_0:
                    transcript_ds = chunk_0["transcript"]
                    if isinstance(transcript_ds, h5py.Dataset):
                        transcript = transcript_ds[()].decode("utf-8")
                        preview = transcript[:200]

            # Sum durations
            for i in range(chunk_count):
                chunk_key = f"chunk_{i}"
                if chunk_key in chunks_group:
                    chunk = chunks_group[chunk_key]
                    if "duration" in chunk:
                        duration_seconds += float(chunk["duration"][()])

        except Exception as e:
            logger.warning("SKIP_CHUNK_DATA", session_id=session_id, error=str(e))

        return (chunk_count, duration_seconds, preview)

    def _extract_doctor_name_from_diarization(self, tasks: Any, session_id: str) -> str:
        """Extract doctor name from diarization segments using regex.

        Searches first 5 segments for patterns like:
        - "soy el doctor [Name]"
        - "mi nombre es doctora [Name]"
        - "doctor [Name]"

        Returns:
            Doctor name or empty string
        """
        import re

        if "DIARIZATION" not in tasks:
            return ""

        diar_task = tasks["DIARIZATION"]
        if "segments" not in diar_task:
            return ""

        segments = diar_task["segments"]
        patterns = [
            r"(?:soy el|mi nombre es|me llamo)\s+doctor[a]?\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]+)",
            r"doctor[a]?\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]{3,})",
        ]
        common_words = {"que", "como", "por", "con", "para", "los", "las", "del", "una", "uno"}

        try:
            for seg_key in list(segments.keys())[:5]:
                segment = segments[seg_key]
                if "text" not in segment:
                    continue

                text_ds = segment["text"]
                if not isinstance(text_ds, h5py.Dataset):
                    continue

                text = text_ds[()].decode("utf-8").lower()

                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        name = match.group(1).capitalize()
                        if name.lower() not in common_words:
                            return name

        except Exception as e:
            logger.warning("SKIP_NAME_EXTRACTION", session_id=session_id, error=str(e))

        return ""

    # =========================================================================
    # Main Session Listing Method
    # =========================================================================

    def list_all_sessions_with_metadata(
        self, limit: int = 20, offset: int = 0, clinic_id: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """List all sessions with detailed metadata (for sessions list endpoint).

        Multi-Tenancy Support:
        - If clinic_id provided: Returns ONLY sessions from that clinic
        - If clinic_id is None: Returns ALL sessions (SUPERADMIN mode)

        Args:
            limit: Maximum number of sessions to return (default 20)
            offset: Number of sessions to skip (default 0)
            clinic_id: Filter sessions by clinic_id (None = all clinics)

        Returns:
            Tuple of (sessions list, total count)
        """
        try:
            with h5py.File(self.h5_file_path, "r") as f:
                if self.SESSIONS_GROUP not in f:
                    logger.warning("NO_SESSIONS_GROUP_IN_HDF5")
                    return ([], 0)

                sessions_group = f[self.SESSIONS_GROUP]

                # Phase 1: Collect session IDs with timestamps (for sorting)
                session_metadata_list: list[tuple[str, str]] = []

                for session_id in sessions_group.keys():
                    try:
                        session_group = sessions_group[session_id]
                        if "tasks" not in session_group:
                            continue

                        # Multi-tenancy filter
                        if clinic_id is not None:
                            session_clinic = session_group.attrs.get("clinic_id") if hasattr(session_group, "attrs") else None
                            if session_clinic != clinic_id:
                                continue

                        tasks = session_group["tasks"]
                        created_at = self._extract_session_created_at(tasks)
                        session_metadata_list.append((session_id, created_at))

                    except Exception as e:
                        logger.warning("SKIP_SESSION_METADATA", session_id=session_id, error=str(e))

                # Sort by created_at (newest first) and paginate
                session_metadata_list.sort(key=lambda x: x[1], reverse=True)
                paginated = session_metadata_list[offset : offset + limit]

                # Phase 2: Build detailed session info for paginated results
                sessions_list: list[dict[str, Any]] = []

                for session_id, created_at in paginated:
                    try:
                        session_group = sessions_group[session_id]
                        if "tasks" not in session_group:
                            continue

                        tasks = session_group["tasks"]

                        # Task flags
                        has_transcription = "TRANSCRIPTION" in tasks
                        has_diarization = "DIARIZATION" in tasks
                        has_soap = "SOAP_GENERATION" in tasks

                        # Transcription details
                        chunk_count, duration_seconds, preview = self._extract_transcription_details(
                            tasks, session_id
                        )

                        # Names from attrs or diarization
                        patient_name = session_group.attrs.get("patient_name", "Paciente") if hasattr(session_group, "attrs") else "Paciente"
                        doctor_name = session_group.attrs.get("doctor_name", "") if hasattr(session_group, "attrs") else ""

                        if has_diarization and (patient_name == "Paciente" or not doctor_name):
                            extracted_doctor = self._extract_doctor_name_from_diarization(tasks, session_id)
                            if extracted_doctor:
                                doctor_name = extracted_doctor

                        sessions_list.append({
                            "session_id": session_id,
                            "created_at": created_at,
                            "has_transcription": has_transcription,
                            "has_diarization": has_diarization,
                            "has_soap": has_soap,
                            "chunk_count": chunk_count,
                            "duration_seconds": duration_seconds,
                            "preview": preview,
                            "patient_name": patient_name,
                            "doctor_name": doctor_name,
                        })

                    except Exception as e:
                        logger.warning("SKIP_SESSION_DETAILS", session_id=session_id, error=str(e))

            total_count = len(session_metadata_list)
            logger.info(
                "SESSIONS_LIST_SUCCESS",
                total=total_count,
                returned=len(sessions_list),
                clinic_id_filter=clinic_id,
            )
            return (sessions_list, total_count)

        except Exception as e:
            logger.error("LIST_ALL_SESSIONS_FAILED", error=str(e), exc_info=True)
            return ([], 0)
