"""Repository for corpus data operations.

Handles all HDF5 operations for corpus documents, chunks, and metadata.
Centralizes data access logic that was previously scattered across multiple files.

Clean Code: Single Responsibility - this class only handles corpus data access,
not business logic or API concerns.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timezone

UTC = UTC
from pathlib import Path
from typing import Any, Optional

import h5py

from backend.logger import get_logger
from backend.type_defs import DiarizationChunkDict

from .base_repository import BaseRepository

logger = get_logger(__name__)


class CorpusRepository(BaseRepository):
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

    def __init__(self, h5_file_path: str | Path) -> None:
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

    def create(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Optional[Any]] = None,
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

                dataset.attrs["created_at"] = datetime.now(timezone.utc).isoformat()
                dataset.attrs["version"] = 1

            self._log_operation("create", document_id)
            return document_id

        except Exception as e:
            self._log_operation("create", document_id, status="failed", error=str(e))
            raise

    def read(self, document_id: str) -> dict[str, Optional[Any]]:
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

    def update(
        self, document_id: str, content: str, metadata: dict[str, Optional[Any]] = None
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
                dataset.attrs["updated_at"] = datetime.now(timezone.utc).isoformat()  # type: ignore[attr-defined]
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

    def delete(self, document_id: str) -> bool:
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
                dataset.attrs["deleted_at"] = datetime.now(timezone.utc).isoformat()  # type: ignore[attr-defined]
                dataset.attrs["is_deleted"] = True  # type: ignore[attr-defined]

            self._log_operation("delete", document_id)
            return True

        except Exception as e:
            self._log_operation("delete", document_id, status="failed", error=str(e))
            return False

    def list_all(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
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
                    if doc_data and not doc_data["metadata"].get("is_deleted", False):
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
            chunk_id = f"{document_id}_chunk_{chunk['chunk_idx']}"

            with self._open_file("r+") as f:
                chunks_group = f[self.CHUNKS_GROUP]
                chunk_group = chunks_group.create_group(chunk_id)  # type: ignore[attr-defined]

                # Store chunk data
                for key, value in chunk.items():
                    if isinstance(value, str):
                        chunk_group.attrs[key] = value
                    elif isinstance(value, (int, float)):
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

                for chunk_id in chunks_group.keys():  # type: ignore[attr-defined]
                    if chunk_id.startswith(document_id):
                        chunk_group = chunks_group[chunk_id]  # type: ignore[index]
                        chunk_data: DiarizationChunkDict = {}
                        for key, value in chunk_group.attrs.items():  # type: ignore[attr-defined]
                            chunk_data[key] = value
                        chunks.append(chunk_data)

                return sorted(chunks, key=lambda c: c.get("chunk_idx", 0))

        except Exception as e:
            logger.error("CHUNKS_READ_FAILED", document_id=document_id, error=str(e))
            return []
