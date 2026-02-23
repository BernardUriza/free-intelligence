"""Corpus document CRUD operations.

Handles create, read, update (append-only versioned), soft-delete, and
listing of corpus documents inside an HDF5 file.

Author: Bernard Uriza Orozco
"""

from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import h5py
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

# HDF5 top-level group where documents live.
DOCUMENTS_GROUP = "documents"


class DocumentOperations:
    """Append-only document storage backed by HDF5.

    All state mutations create new versions rather than overwriting
    existing data, satisfying the event-sourcing / audit-trail
    requirement.
    """

    def __init__(
        self,
        open_file: Any,
        log_operation: Any,
    ) -> None:
        """Initialise with shared file helpers.

        Args:
            open_file: Callable context-manager that opens the HDF5 file.
            log_operation: Callable for audit-trail logging.
        """
        self._open_file = open_file
        self._log_operation = log_operation

    # -- CRUD ----------------------------------------------------------------

    def create(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any | None] | None = None,
    ) -> str:
        """Create a new corpus document.

        Args:
            document_id: Unique document identifier.
            content: Document content.
            metadata: Optional key/value metadata.

        Returns:
            The ``document_id``.

        Raises:
            ValueError: If ``document_id`` or ``content`` is empty, or the
                document already exists.
            IOError: If the HDF5 write fails.
        """
        if not document_id or not content:
            raise ValueError("document_id and content are required")

        try:
            with self._open_file("r+") as f:
                doc_group = f[DOCUMENTS_GROUP]

                if document_id in doc_group:
                    raise ValueError(f"Document {document_id} already exists")

                dataset = doc_group.create_dataset(
                    document_id,
                    data=content.encode("utf-8"),
                    dtype=h5py.string_dtype(encoding="utf-8"),
                )

                _store_metadata(dataset, metadata)
                dataset.attrs["created_at"] = datetime.now(timezone.utc).isoformat()
                dataset.attrs["version"] = 1

            self._log_operation("create", document_id)
            return document_id

        except Exception as e:
            self._log_operation("create", document_id, status="failed", error=str(e))
            raise

    def read(self, document_id: str) -> dict[str, Any | None] | None:
        """Read a single corpus document.

        Returns:
            ``{"document_id": …, "content": …, "metadata": …}`` or
            ``None`` if the document does not exist.
        """
        try:
            with self._open_file("r") as f:
                if document_id not in f[DOCUMENTS_GROUP]:
                    return None

                dataset = f[DOCUMENTS_GROUP][document_id]
                raw = dataset[()]
                content = raw.decode("utf-8") if isinstance(raw, bytes) else raw

                return {
                    "document_id": document_id,
                    "content": content,
                    "metadata": dict(dataset.attrs),
                }

        except Exception as e:
            logger.error("CORPUS_READ_FAILED", document_id=document_id, error=str(e))
            return None

    def update(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any | None] | None = None,
    ) -> bool:
        """Append a new version of an existing document.

        Does **not** overwrite old data — the new content is stored
        under a ``version_N_content`` attribute.

        Returns:
            ``True`` on success, ``False`` if the document is missing.
        """
        try:
            with self._open_file("r+") as f:
                if document_id not in f[DOCUMENTS_GROUP]:
                    return False

                dataset = f[DOCUMENTS_GROUP][document_id]
                current_version = int(dataset.attrs.get("version", 1))
                new_version = current_version + 1

                dataset.attrs["updated_at"] = datetime.now(timezone.utc).isoformat()
                dataset.attrs["version"] = new_version
                dataset.attrs[f"version_{new_version}_content"] = content.encode("utf-8")

                if metadata:
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            dataset.attrs[f"version_{new_version}_{key}"] = value

            self._log_operation("update", document_id)
            return True

        except Exception as e:
            self._log_operation("update", document_id, status="failed", error=str(e))
            return False

    def delete(self, document_id: str) -> bool:
        """Soft-delete a document (append-only: marks ``is_deleted``).

        Returns:
            ``True`` on success, ``False`` if the document is missing.
        """
        try:
            with self._open_file("r+") as f:
                if document_id not in f[DOCUMENTS_GROUP]:
                    return False

                dataset = f[DOCUMENTS_GROUP][document_id]
                dataset.attrs["deleted_at"] = datetime.now(timezone.utc).isoformat()
                dataset.attrs["is_deleted"] = True

            self._log_operation("delete", document_id)
            return True

        except Exception as e:
            self._log_operation("delete", document_id, status="failed", error=str(e))
            return False

    def list_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        """List non-deleted documents.

        Args:
            limit: Cap on the number of returned documents.

        Returns:
            List of document dicts (same shape as ``read``).
        """
        try:
            with self._open_file("r") as f:
                doc_ids = list(f[DOCUMENTS_GROUP].keys())

                if limit:
                    doc_ids = doc_ids[:limit]

                results: list[dict[str, Any]] = []
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


# -- private helpers ---------------------------------------------------------


def _store_metadata(dataset: Any, metadata: dict[str, Any | None] | None) -> None:
    """Persist metadata dict as HDF5 attributes."""
    if not metadata:
        return
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            dataset.attrs[key] = value
        elif isinstance(value, (list, dict)):
            dataset.attrs[key] = json.dumps(value)
