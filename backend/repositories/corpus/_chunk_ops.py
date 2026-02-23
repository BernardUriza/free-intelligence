"""Corpus diarization-chunk operations.

Handles adding and retrieving diarization chunks associated with
corpus documents in HDF5.

Author: Bernard Uriza Orozco
"""

from __future__ import annotations

from typing import Any, cast

from backend.utils.common.logging.logger import get_logger
from backend.utils.common.types.type_defs import DiarizationChunkDict

logger = get_logger(__name__)

# HDF5 top-level group where chunks live.
CHUNKS_GROUP = "chunks"


class ChunkOperations:
    """Read/write diarization chunks for corpus documents."""

    def __init__(
        self,
        open_file: Any,
        log_operation: Any,
    ) -> None:
        self._open_file = open_file
        self._log_operation = log_operation

    def add_chunk(self, chunk: DiarizationChunkDict, document_id: str) -> bool:
        """Append a diarization chunk to a document.

        Args:
            chunk: Chunk data dict.
            document_id: Parent document ID.

        Returns:
            ``True`` on success.
        """
        try:
            chunk_idx = chunk.get("chunk_idx", 0)
            chunk_id = f"{document_id}_chunk_{chunk_idx}"

            with self._open_file("r+") as f:
                chunks_group = f[CHUNKS_GROUP]
                chunk_group = chunks_group.create_group(chunk_id)

                for key, value in chunk.items():
                    if isinstance(value, (str, int, float)):
                        chunk_group.attrs[key] = value

            self._log_operation("create_chunk", chunk_id)
            return True

        except Exception as e:
            logger.error("CHUNK_ADD_FAILED", document_id=document_id, error=str(e))
            return False

    def get_chunks(self, document_id: str) -> list[DiarizationChunkDict]:
        """Retrieve all chunks belonging to *document_id*, sorted by index.

        Returns:
            Sorted list of chunk dicts.
        """
        try:
            with self._open_file("r") as f:
                chunks_group = f[CHUNKS_GROUP]
                chunks: list[DiarizationChunkDict] = []

                for chunk_id in chunks_group:
                    if not chunk_id.startswith(document_id):
                        continue

                    chunk_group = chunks_group[chunk_id]
                    chunk_data: dict[str, Any] = {}
                    for key, value in chunk_group.attrs.items():
                        chunk_data[str(key)] = value
                    chunks.append(cast(DiarizationChunkDict, chunk_data))

                return sorted(chunks, key=lambda c: c.get("chunk_idx", 0))

        except Exception as e:
            logger.error("CHUNKS_READ_FAILED", document_id=document_id, error=str(e))
            return []
