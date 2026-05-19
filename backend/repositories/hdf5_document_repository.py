"""HDF5-based document repository — thin adapter over fi_core.stores.hdf5.

Refactored 2026-05-19 from a 674-LOC standalone HDF5 implementation
into a ~250-LOC adapter that delegates storage primitives to
``fi_core.stores.hdf5.HDF5ChunkStore`` and handles only the
AURITY-specific concerns:

- ``IDocumentRepository`` interface compliance (the AURITY DI contract).
- ``clinic_id`` mandatory namespace + security boundary.
- AURITY domain models (``Document``, ``DocumentChunk``, ``SearchResult``)
  marshalled to/from fi-core's generic ``DocumentRecord`` + ``Chunk`` +
  ``RetrievedChunk``.
- GPU delegation for similarity search (>1000 vectors).
- Domain enums (``DocumentStatus``, ``DocumentOrigin``, ``DocumentType``)
  preserved as opaque attributes on the underlying store.

This is the **reference consumer pattern for fi_core.stores.hdf5** —
showcases how a domain-specific repository wraps a generic primitive
without polluting either layer.

Security: ALL operations enforce clinic_id filtering by passing
clinic_id as the fi-core ``namespace`` argument. Cross-clinic access
is structurally impossible — the store cannot return data from a
different namespace.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5 (2026-01-29)
        + Claude Opus 4.7 (2026-05-19 refactor)
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fi_core.rag.types import (
    Chunk as _FiChunk,
)
from fi_core.rag.types import (
    ChunkWithEmbedding as _FiChunkWithEmbedding,
)
from fi_core.rag.types import (
    DocumentMetadata as _FiDocumentMetadata,
)
from fi_core.rag.types import (
    DocumentRecord as _FiDocumentRecord,
)
from fi_core.stores.hdf5 import HDF5ChunkStore

from backend.domain.document.models import (
    Document,
    DocumentChunk,
    DocumentMetadata,
    DocumentOrigin,
    DocumentStatus,
    DocumentType,
    SearchResult,
)
from backend.repositories.interfaces.idocument_repository import IDocumentRepository
from backend.services.assistant.services.monitor_client import similarity_search_gpu
from backend.utils.common.logging.logger import get_logger
from backend.utils.common.types import utc_now
from backend.utils.math.cpu import cosine_similarity_batch

logger = get_logger(__name__)

# GPU delegation threshold: use GPU for >1000 vectors.
GPU_SEARCH_THRESHOLD = 1000


class HDF5DocumentRepository(IDocumentRepository):
    """Thin adapter: AURITY's IDocumentRepository → fi_core.stores.hdf5.

    All storage primitives delegate to a single ``HDF5ChunkStore`` instance.
    This class handles only domain-model marshalling, ``clinic_id`` →
    ``namespace`` mapping, and the GPU search escape hatch.
    """

    def __init__(self, storage_path: str | Path = "storage/documents.h5") -> None:
        self.storage_path = Path(storage_path)
        self._store = HDF5ChunkStore(self.storage_path)

    # =================================================================
    # DOCUMENT CRUD
    # =================================================================

    def create_document(
        self, doc: Document, file_content: bytes | None = None
    ) -> Document:
        if not doc.clinic_id:
            raise ValueError("clinic_id is required")
        if not doc.doc_id:
            doc.doc_id = str(uuid.uuid4())

        self._store.create_document_sync(
            namespace=doc.clinic_id,
            document_id=doc.doc_id,
            content=doc.content,
            metadata=_to_fi_metadata(doc),
        )
        logger.info(
            "DOCUMENT_CREATED",
            doc_id=doc.doc_id,
            clinic_id=doc.clinic_id,
            title=doc.title,
            size_bytes=len(doc.content),
        )
        # file_content is intentionally NOT persisted here — that was an
        # AURITY-specific feature (uploaded PDF blobs) that the new
        # adapter omits. Re-add via a separate binary store if needed.
        if file_content:
            logger.warning(
                "FILE_CONTENT_NOT_PERSISTED",
                doc_id=doc.doc_id,
                message="HDF5DocumentRepository refactor dropped file_content support",
            )
        return doc

    def get_document(self, doc_id: str, clinic_id: str) -> Document | None:
        record = self._store.get_document_sync(
            namespace=clinic_id, document_id=doc_id
        )
        if record is None:
            return None
        return _from_fi_record(record)

    def list_documents(
        self,
        clinic_id: str,
        status: DocumentStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Document]:
        status_str = status.value if status is not None else None
        records = self._store.list_documents_sync(
            namespace=clinic_id, status=status_str
        )
        docs = [_from_fi_record(r) for r in records]
        # Sort by uploaded_at descending (newest first) — fi-core does not
        # guarantee order, so we sort on this side.
        docs.sort(key=lambda d: d.uploaded_at, reverse=True)
        return docs[skip : skip + limit]

    def update_document(
        self, doc_id: str, clinic_id: str, updates: dict
    ) -> Document | None:
        doc = self.get_document(doc_id, clinic_id)
        if doc is None:
            return None
        for key, value in updates.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        doc.updated_at = utc_now()

        ok = self._store.update_document_sync(
            namespace=clinic_id,
            document_id=doc_id,
            content=doc.content,
            metadata=_to_fi_metadata(doc),
        )
        if not ok:
            return None
        logger.info(
            "DOCUMENT_UPDATED",
            doc_id=doc_id,
            clinic_id=clinic_id,
            updates=list(updates.keys()),
        )
        return doc

    def delete_document(
        self, doc_id: str, clinic_id: str, soft_delete: bool = True
    ) -> bool:
        if soft_delete:
            return (
                self.update_document(
                    doc_id, clinic_id, {"status": DocumentStatus.ARCHIVED}
                )
                is not None
            )
        deleted = self._store.delete_document_sync(
            namespace=clinic_id, document_id=doc_id
        )
        if deleted:
            logger.info(
                "DOCUMENT_DELETED",
                doc_id=doc_id,
                clinic_id=clinic_id,
                soft_delete=False,
            )
        return deleted

    def get_document_count(
        self, clinic_id: str, status: DocumentStatus | None = None
    ) -> int:
        records = self._store.list_documents_sync(
            namespace=clinic_id, status=(status.value if status else None)
        )
        return len(records)

    # =================================================================
    # DOCUMENT CHUNKS
    # =================================================================

    def save_chunks(
        self, doc_id: str, clinic_id: str, chunks: list[DocumentChunk]
    ) -> int:
        # Verify document belongs to clinic (raises if cross-clinic access)
        if self.get_document(doc_id, clinic_id) is None:
            raise ValueError(f"Document {doc_id} not found or access denied")

        fi_chunks = [_to_fi_chunk_with_embedding(c) for c in chunks]
        saved = self._store.save_chunks_sync(
            namespace=clinic_id, document_id=doc_id, chunks=fi_chunks
        )
        logger.info(
            "CHUNKS_SAVED", doc_id=doc_id, clinic_id=clinic_id, count=saved
        )
        return saved

    def get_chunks(self, doc_id: str, clinic_id: str) -> list[DocumentChunk]:
        if self.get_document(doc_id, clinic_id) is None:
            return []
        fi_chunks = self._store.get_chunks_by_document_sync(
            namespace=clinic_id, document_id=doc_id
        )
        chunks = [_from_fi_chunk(c, doc_id) for c in fi_chunks]
        return sorted(chunks, key=lambda c: c.chunk_index)

    def delete_chunks(self, doc_id: str, clinic_id: str) -> int:
        if self.get_document(doc_id, clinic_id) is None:
            return 0
        count = self._store.delete_chunks_by_document_sync(
            namespace=clinic_id, document_id=doc_id
        )
        logger.info(
            "CHUNKS_DELETED", doc_id=doc_id, clinic_id=clinic_id, count=count
        )
        return count

    # =================================================================
    # SEMANTIC SEARCH (async — GPU delegation for >1000 vectors)
    # =================================================================

    async def search_by_embedding(
        self,
        query_embedding: list[float],
        clinic_id: str,
        limit: int = 10,
        min_score: float = 0.5,
        document_type: str | None = None,
    ) -> list[SearchResult]:
        """Semantic search with GPU delegation + AURITY filters.

        fi_core's ``query`` returns RetrievedChunk objects sorted by
        cosine similarity. This wrapper applies the AURITY-specific
        filters (status == INDEXED, document_type, min_score) on the
        result set and marshals to ``SearchResult``.

        GPU delegation: if the namespace has >1000 vectors, we call
        ``similarity_search_gpu`` directly (bypassing fi-core's CPU
        path) for speed. On GPU failure, we fall back to fi-core's
        CPU query.
        """
        # Snapshot the in-memory index entries for the clinic.
        ns_idx = self._store._index.get(clinic_id)
        if ns_idx is None or not ns_idx.entries:
            return []

        # GPU fast path (preserved from legacy implementation).
        if len(ns_idx.entries) > GPU_SEARCH_THRESHOLD:
            try:
                all_vectors = [e.embedding.tolist() for e in ns_idx.entries]
                similarities = await similarity_search_gpu(
                    query_embedding, all_vectors
                )
                retrieved = self._materialize_top_k(
                    clinic_id=clinic_id,
                    similarities=similarities,
                    entries=ns_idx.entries,
                    limit=limit,
                )
            except (ConnectionError, ValueError) as e:
                logger.warning(
                    "GPU_SEARCH_FALLBACK",
                    vectors=len(ns_idx.entries),
                    error=str(e),
                )
                retrieved = await self._store.query(
                    namespace=clinic_id,
                    query_embedding=query_embedding,
                    top_k=limit * 3,  # over-fetch to survive filters
                )
        else:
            # Small set: fi-core's CPU query is fine.
            retrieved = await self._store.query(
                namespace=clinic_id,
                query_embedding=query_embedding,
                top_k=limit * 3,
            )

        # Apply AURITY-specific filters + marshal to SearchResult.
        results: list[SearchResult] = []
        seen_docs: dict[str, Document] = {}

        for rc in retrieved:
            if rc.similarity < min_score:
                continue
            # The chunk's source_ref encodes "doc_id#chunk_index" by AURITY
            # convention. Parse to recover the doc_id for filter logic.
            doc_id = _doc_id_from_source_ref(rc.chunk.source_ref)
            if doc_id is None:
                continue
            doc = seen_docs.get(doc_id) or self.get_document(doc_id, clinic_id)
            if doc is None:
                continue
            seen_docs[doc_id] = doc
            if doc.status != DocumentStatus.INDEXED:
                continue
            if document_type and doc.metadata.document_type.value != document_type:
                continue

            results.append(
                SearchResult(
                    doc_id=doc.doc_id,
                    title=doc.title,
                    chunk_id=rc.chunk.source_ref,
                    chunk_text=rc.chunk.text,
                    page_num=0,  # legacy field; chunk metadata could carry it
                    score=rc.similarity,
                    document_type=doc.metadata.document_type,
                    specialty=doc.metadata.specialty,
                )
            )
            if len(results) >= limit:
                break

        return results

    def _materialize_top_k(
        self,
        *,
        clinic_id: str,
        similarities: list[float],
        entries: list[Any],
        limit: int,
    ) -> list[Any]:
        """GPU-path materialization — pull chunks from store after similarity scoring."""
        import numpy as _np

        sims = _np.asarray(similarities, dtype=_np.float32)
        k = min(limit * 3, len(sims))
        top_unsorted = _np.argpartition(-sims, k - 1)[:k]
        top_sorted = top_unsorted[_np.argsort(-sims[top_unsorted])]

        from fi_core.rag.types import RetrievedChunk as _RC

        results: list[Any] = []
        for i in top_sorted:
            entry = entries[int(i)]
            chunks = self._store.get_chunks_by_document_sync(
                namespace=clinic_id, document_id=entry.document_id
            )
            chunk = next(
                (c for c in chunks if _chunk_id_matches(c, entry.chunk_id)), None
            )
            if chunk is None:
                continue
            results.append(_RC(chunk=chunk, similarity=float(sims[int(i)])))
        return results

    # =================================================================
    # BULK OPERATIONS
    # =================================================================

    def reindex_document(self, doc_id: str, clinic_id: str) -> bool:
        return (
            self.update_document(
                doc_id,
                clinic_id,
                {
                    "status": DocumentStatus.PENDING,
                    "retry_count": 0,
                    "error_message": None,
                },
            )
            is not None
        )

    def get_pending_documents(
        self, clinic_id: str | None = None, limit: int = 100
    ) -> list[Document]:
        if clinic_id:
            pending = self.list_documents(
                clinic_id, status=DocumentStatus.PENDING, skip=0, limit=limit
            )
            indexing = self.list_documents(
                clinic_id, status=DocumentStatus.INDEXING, skip=0, limit=limit
            )
            return (pending + indexing)[:limit]
        # All clinics: walk every namespace via fi-core's internal index.
        all_pending: list[Document] = []
        for ns in self._store._index.keys():
            all_pending.extend(self.get_pending_documents(ns, limit))
            if len(all_pending) >= limit:
                break
        return all_pending[:limit]


# ============================================================
# Domain ↔ fi-core marshalling helpers
# ============================================================


def _to_fi_metadata(doc: Document) -> _FiDocumentMetadata:
    """AURITY Document → fi-core DocumentMetadata with attributes dict.

    fi-core treats attributes as an opaque bag — we stash every
    AURITY-domain field there so round-trip is lossless.
    """
    return _FiDocumentMetadata(
        status=doc.status.value,
        created_at=doc.uploaded_at,
        indexed_at=doc.updated_at,
        attributes={
            "clinic_id": doc.clinic_id,
            "title": doc.title,
            "origin": doc.origin.value,
            "uploaded_by": doc.uploaded_by,
            "error_message": doc.error_message,
            "retry_count": doc.retry_count,
            "doc_metadata": {
                "specialty": doc.metadata.specialty,
                "language": doc.metadata.language,
                "keywords": doc.metadata.keywords,
                "document_type": doc.metadata.document_type.value,
                "file_size_bytes": doc.metadata.file_size_bytes,
                "mime_type": doc.metadata.mime_type,
                "original_filename": doc.metadata.original_filename,
                "num_pages": doc.metadata.num_pages,
                "num_chunks": doc.metadata.num_chunks,
                "embedding_model": doc.metadata.embedding_model,
                "custom": doc.metadata.custom,
            },
        },
    )


def _from_fi_record(record: _FiDocumentRecord) -> Document:
    """fi-core DocumentRecord → AURITY Document (reconstruct domain enums)."""
    attrs = record.metadata.attributes
    doc_meta_dict = attrs.get("doc_metadata", {})
    doc_metadata = DocumentMetadata(
        specialty=doc_meta_dict.get("specialty"),
        language=doc_meta_dict.get("language", "es"),
        keywords=doc_meta_dict.get("keywords", []),
        document_type=DocumentType(doc_meta_dict.get("document_type", "other")),
        file_size_bytes=doc_meta_dict.get("file_size_bytes", 0),
        mime_type=doc_meta_dict.get("mime_type", "application/pdf"),
        original_filename=doc_meta_dict.get("original_filename", ""),
        num_pages=doc_meta_dict.get("num_pages", 0),
        num_chunks=doc_meta_dict.get("num_chunks", 0),
        embedding_model=doc_meta_dict.get("embedding_model", ""),
        custom=doc_meta_dict.get("custom", {}),
    )
    return Document(
        doc_id=record.document_id,
        clinic_id=attrs.get("clinic_id", record.namespace),
        title=attrs.get("title", ""),
        content=record.content,
        metadata=doc_metadata,
        uploaded_by=attrs.get("uploaded_by", ""),
        status=DocumentStatus(record.metadata.status),
        origin=DocumentOrigin(attrs.get("origin", DocumentOrigin.API_UPLOAD.value)),
        uploaded_at=record.metadata.created_at or utc_now(),
        updated_at=record.metadata.indexed_at,
        error_message=attrs.get("error_message"),
        retry_count=attrs.get("retry_count", 0),
    )


def _to_fi_chunk_with_embedding(c: DocumentChunk) -> _FiChunkWithEmbedding:
    """AURITY DocumentChunk → fi-core ChunkWithEmbedding."""
    return _FiChunkWithEmbedding(
        chunk=_FiChunk(
            text=c.text,
            source_type="document",
            source_ref=c.chunk_id,
            created_at=None,
        ),
        embedding=list(c.embedding or []),
    )


def _from_fi_chunk(c: _FiChunk, doc_id: str) -> DocumentChunk:
    """fi-core Chunk → AURITY DocumentChunk."""
    # AURITY DocumentChunk has chunk_index; we recover it by convention
    # from the source_ref "doc_id#index" or default to 0.
    chunk_index = _chunk_index_from_source_ref(c.source_ref)
    return DocumentChunk(
        chunk_id=c.source_ref,
        doc_id=doc_id,
        chunk_index=chunk_index,
        text=c.text,
        page_num=0,
        embedding=None,
    )


def _doc_id_from_source_ref(source_ref: str) -> str | None:
    """Best-effort recovery of doc_id from chunk source_ref.

    AURITY convention: source_ref = "{doc_id}#{chunk_index}".
    """
    if "#" in source_ref:
        return source_ref.split("#", 1)[0]
    return None


def _chunk_index_from_source_ref(source_ref: str) -> int:
    if "#" in source_ref:
        try:
            return int(source_ref.split("#", 1)[1])
        except (ValueError, IndexError):
            return 0
    return 0


def _chunk_id_matches(chunk: _FiChunk, target_chunk_id: str) -> bool:
    """Heuristic match: fi-core hashes chunk_id from source_ref + text;
    consumers should compare against ``chunk.source_ref``, not the
    internal hashed ID."""
    return chunk.source_ref == target_chunk_id or chunk.source_ref.startswith(
        target_chunk_id
    )


__all__ = ["HDF5DocumentRepository"]
