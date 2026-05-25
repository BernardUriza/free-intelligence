"""HDF5-backed implementation of ``DocumentChunkStore``.

Generic, domain-agnostic chunk store backed by HDF5 file storage.
Designed for append-mostly workloads where the same machine reads and
writes (single-process locking). Maintains an in-memory cosine-
similarity index for sub-millisecond top-k retrieval over thousands
of chunks per namespace.

Use cases:
- Medical RAG (AURITY) — namespace = clinic_id, documents = patient
  records, chunks = paragraphs.
- Longitudinal mental-science (Insult Tier 2 future) — namespace =
  user_id, documents = session snapshots, chunks = signal
  extractions.
- Training corpus (Robo-Poet future) — namespace = corpus name,
  documents = source files, chunks = tokenized passages.

Storage layout::

    store.h5
    └── /namespaces/
        └── {namespace}/
            └── /documents/
                └── {document_id}/
                    ├── attrs: content, status, created_at,
                    │           indexed_at, attributes (JSON)
                    └── /chunks/
                        └── {chunk_id}/
                            ├── attrs: text, source_type, source_ref,
                            │           created_at
                            └── /embedding (float32 dataset)

The in-memory vector index mirrors ``/namespaces/{ns}/documents/{doc}/chunks``
for fast similarity search; it is rebuilt on instance construction and
mutated in-place on writes. Concurrency model: single-process,
single-writer. For multi-process access wrap construction in a file
lock (fi-core does not provide one — pick ``filelock`` or your
deployment's primitive).

Optional dependency: ``h5py >= 3.10``. Install via
``pip install fi-core[stores-hdf5]``.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import h5py
    import numpy as np
except ImportError as e:
    raise ImportError(
        "fi_core.stores.hdf5 requires h5py and numpy. "
        "Install via: pip install 'fi-core[stores-hdf5]'"
    ) from e

from fi_core.rag.types import (
    Chunk,
    ChunkWithEmbedding,
    DocumentMetadata,
    DocumentRecord,
    RetrievedChunk,
)


# HDF5 top-level group name for namespaces. All consumer data sits under here.
_NS_GROUP = "namespaces"
_DOCS_GROUP = "documents"
_CHUNKS_GROUP = "chunks"
_EMBEDDING_DATASET = "embedding"

# Document attribute keys (stored on each document HDF5 group as attrs).
_ATTR_CONTENT = "content"
_ATTR_STATUS = "status"
_ATTR_CREATED_AT = "created_at"
_ATTR_INDEXED_AT = "indexed_at"
_ATTR_ATTRIBUTES = "attributes"  # JSON-serialized free-form metadata

# Chunk attribute keys.
_CHUNK_TEXT = "text"
_CHUNK_SOURCE_TYPE = "source_type"
_CHUNK_SOURCE_REF = "source_ref"
_CHUNK_CREATED_AT = "created_at"


@dataclass
class _IndexEntry:
    """In-memory cosine-search index entry."""

    chunk_id: str
    document_id: str
    embedding: "np.ndarray"


@dataclass
class _NamespaceIndex:
    """Mutable per-namespace index used for similarity search."""

    entries: list[_IndexEntry] = field(default_factory=list)

    def add(self, entry: _IndexEntry) -> None:
        self.entries.append(entry)

    def remove_document(self, document_id: str) -> int:
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.document_id != document_id]
        return before - len(self.entries)


class HDF5ChunkStore:
    """HDF5-backed ``DocumentChunkStore`` implementation.

    Persists documents + chunks + embeddings to a single HDF5 file.
    Maintains an in-memory cosine-similarity index for fast top-k
    retrieval. Async API per the Protocol — internal h5py calls are
    dispatched to ``asyncio.to_thread`` so they don't block the event
    loop.

    Concurrency: single-writer. Multiple readers within the same
    process are safe. For cross-process safety, wrap construction in
    a file lock (fi-core does not provide one).
    """

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        # Touch + ensure top-level group exists before first read.
        with h5py.File(self.file_path, "a") as f:
            f.require_group(_NS_GROUP)
        # Per-namespace in-memory index. Rebuilt on construction.
        self._index: dict[str, _NamespaceIndex] = {}
        self._rebuild_full_index()

    # ------------------------------------------------------------------
    # Public Protocol methods (ChunkStore + DocumentChunkStore)
    # ------------------------------------------------------------------

    async def add(
        self,
        *,
        namespace: str,
        chunk: Chunk,
        embedding: list[float],
    ) -> None:
        """ChunkStore.add — chunk-only insert.

        For consumers that don't care about documents: synthesizes a
        per-chunk parent document so the underlying storage is still
        consistent. The synthesized document_id is derived from
        ``chunk.source_ref`` to make repeated calls idempotent on the
        same source.
        """
        document_id = f"_auto_{chunk.source_ref}"
        # Create-if-missing parent doc. Idempotent.
        await self._ensure_document_exists(
            namespace=namespace,
            document_id=document_id,
            content=chunk.text,
        )
        await self.save_chunks(
            namespace=namespace,
            document_id=document_id,
            chunks=[ChunkWithEmbedding(chunk=chunk, embedding=embedding)],
        )

    async def query(
        self,
        *,
        namespace: str,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """ChunkStore.query — cosine similarity top-k across namespace.

        Uses the in-memory index. O(N) per call where N is total chunks
        in the namespace. For >100k chunks consider sharding namespaces
        or migrating to a vector DB. ``filters`` restricts to chunks whose
        parent document's ``attributes`` contain the given pairs (flat
        containment, the HDF5 analogue of Postgres ``@>``).
        """
        return await asyncio.to_thread(self._query_sync, namespace, query_embedding, top_k, filters)

    async def create_document(
        self,
        *,
        namespace: str,
        document_id: str,
        content: str,
        metadata: DocumentMetadata | None = None,
    ) -> str:
        await asyncio.to_thread(
            self._create_document_sync, namespace, document_id, content, metadata
        )
        return document_id

    async def get_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> DocumentRecord | None:
        return await asyncio.to_thread(self._get_document_sync, namespace, document_id)

    async def list_documents(
        self,
        *,
        namespace: str,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[DocumentRecord]:
        return await asyncio.to_thread(self._list_documents_sync, namespace, status, limit)

    async def update_document(
        self,
        *,
        namespace: str,
        document_id: str,
        content: str | None = None,
        metadata: DocumentMetadata | None = None,
    ) -> bool:
        return await asyncio.to_thread(
            self._update_document_sync, namespace, document_id, content, metadata
        )

    async def delete_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> bool:
        deleted = await asyncio.to_thread(
            self._delete_document_sync, namespace, document_id
        )
        if deleted:
            idx = self._index.get(namespace)
            if idx:
                idx.remove_document(document_id)
        return deleted

    async def save_chunks(
        self,
        *,
        namespace: str,
        document_id: str,
        chunks: list[ChunkWithEmbedding],
    ) -> int:
        saved, new_entries = await asyncio.to_thread(
            self._save_chunks_sync, namespace, document_id, chunks
        )
        # Update in-memory index after the sync write succeeded.
        if new_entries:
            self._index.setdefault(namespace, _NamespaceIndex())
            for entry in new_entries:
                self._index[namespace].add(entry)
        return saved

    async def get_chunks_by_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> list[Chunk]:
        return await asyncio.to_thread(
            self._get_chunks_by_document_sync, namespace, document_id
        )

    async def delete_chunks_by_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> int:
        deleted = await asyncio.to_thread(
            self._delete_chunks_by_document_sync, namespace, document_id
        )
        if deleted:
            idx = self._index.get(namespace)
            if idx:
                idx.remove_document(document_id)
        return deleted

    async def reindex_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> bool:
        return await asyncio.to_thread(self._reindex_document_sync, namespace, document_id)

    # ------------------------------------------------------------------
    # Public sync API — for legacy callers stuck in sync FastAPI handlers
    # or framework code that can't easily await. The async methods above
    # are the canonical surface; these are escape hatches.
    #
    # All sync methods share the same signatures + semantics as their
    # async counterparts, minus the await. Same idempotency, same status
    # auto-promotion, same in-memory index mutation.
    # ------------------------------------------------------------------

    def create_document_sync(
        self,
        *,
        namespace: str,
        document_id: str,
        content: str,
        metadata: DocumentMetadata | None = None,
    ) -> str:
        """Sync variant of ``create_document``. See async docstring."""
        self._create_document_sync(namespace, document_id, content, metadata)
        return document_id

    def get_document_sync(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> DocumentRecord | None:
        """Sync variant of ``get_document``."""
        return self._get_document_sync(namespace, document_id)

    def list_documents_sync(
        self,
        *,
        namespace: str,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[DocumentRecord]:
        """Sync variant of ``list_documents``."""
        return self._list_documents_sync(namespace, status, limit)

    def update_document_sync(
        self,
        *,
        namespace: str,
        document_id: str,
        content: str | None = None,
        metadata: DocumentMetadata | None = None,
    ) -> bool:
        """Sync variant of ``update_document``."""
        return self._update_document_sync(namespace, document_id, content, metadata)

    def delete_document_sync(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> bool:
        """Sync variant of ``delete_document``. Mutates in-memory index."""
        deleted = self._delete_document_sync(namespace, document_id)
        if deleted:
            idx = self._index.get(namespace)
            if idx:
                idx.remove_document(document_id)
        return deleted

    def save_chunks_sync(
        self,
        *,
        namespace: str,
        document_id: str,
        chunks: list[ChunkWithEmbedding],
    ) -> int:
        """Sync variant of ``save_chunks``. Mutates in-memory index."""
        saved, new_entries = self._save_chunks_sync(namespace, document_id, chunks)
        if new_entries:
            self._index.setdefault(namespace, _NamespaceIndex())
            for entry in new_entries:
                self._index[namespace].add(entry)
        return saved

    def get_chunks_by_document_sync(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> list[Chunk]:
        """Sync variant of ``get_chunks_by_document``."""
        return self._get_chunks_by_document_sync(namespace, document_id)

    def delete_chunks_by_document_sync(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> int:
        """Sync variant of ``delete_chunks_by_document``. Mutates in-memory index."""
        deleted = self._delete_chunks_by_document_sync(namespace, document_id)
        if deleted:
            idx = self._index.get(namespace)
            if idx:
                idx.remove_document(document_id)
        return deleted

    def reindex_document_sync(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> bool:
        """Sync variant of ``reindex_document``."""
        return self._reindex_document_sync(namespace, document_id)

    def query_sync(
        self,
        *,
        namespace: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Sync variant of ``query``. Same cosine-similarity top-k."""
        return self._query_sync(namespace, query_embedding, top_k)

    # ------------------------------------------------------------------
    # Sync internals — never awaited directly, always via to_thread.
    # ------------------------------------------------------------------

    def _create_document_sync(
        self,
        namespace: str,
        document_id: str,
        content: str,
        metadata: DocumentMetadata | None,
    ) -> None:
        meta = metadata or DocumentMetadata(created_at=_now())
        if meta.created_at is None:
            meta = DocumentMetadata(
                status=meta.status,
                created_at=_now(),
                indexed_at=meta.indexed_at,
                attributes=meta.attributes,
            )

        with h5py.File(self.file_path, "a") as f:
            ns_group = f.require_group(f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}")
            if document_id in ns_group:
                raise ValueError(
                    f"Document {document_id!r} already exists in namespace {namespace!r}. "
                    f"Use update_document for upsert semantics."
                )
            doc_group = ns_group.create_group(document_id)
            doc_group.create_group(_CHUNKS_GROUP)
            doc_group.attrs[_ATTR_CONTENT] = content
            doc_group.attrs[_ATTR_STATUS] = meta.status
            doc_group.attrs[_ATTR_CREATED_AT] = _iso(meta.created_at)
            if meta.indexed_at is not None:
                doc_group.attrs[_ATTR_INDEXED_AT] = _iso(meta.indexed_at)
            doc_group.attrs[_ATTR_ATTRIBUTES] = json.dumps(meta.attributes)

    def _get_document_sync(
        self, namespace: str, document_id: str
    ) -> DocumentRecord | None:
        with h5py.File(self.file_path, "r") as f:
            path = f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}/{document_id}"
            if path not in f:
                return None
            doc_group = f[path]
            return _to_document_record(namespace, document_id, doc_group)

    def _list_documents_sync(
        self, namespace: str, status: str | None, limit: int | None
    ) -> list[DocumentRecord]:
        records: list[DocumentRecord] = []
        with h5py.File(self.file_path, "r") as f:
            ns_path = f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}"
            if ns_path not in f:
                return []
            docs_group = f[ns_path]
            for doc_id in docs_group:
                doc_group = docs_group[doc_id]
                if status is not None:
                    doc_status = doc_group.attrs.get(_ATTR_STATUS, "")
                    if doc_status != status:
                        continue
                records.append(_to_document_record(namespace, str(doc_id), doc_group))
                if limit is not None and len(records) >= limit:
                    break
        return records

    def _update_document_sync(
        self,
        namespace: str,
        document_id: str,
        content: str | None,
        metadata: DocumentMetadata | None,
    ) -> bool:
        with h5py.File(self.file_path, "a") as f:
            path = f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}/{document_id}"
            if path not in f:
                return False
            doc_group = f[path]
            if content is not None:
                doc_group.attrs[_ATTR_CONTENT] = content
            if metadata is not None:
                doc_group.attrs[_ATTR_STATUS] = metadata.status
                if metadata.created_at is not None:
                    doc_group.attrs[_ATTR_CREATED_AT] = _iso(metadata.created_at)
                if metadata.indexed_at is not None:
                    doc_group.attrs[_ATTR_INDEXED_AT] = _iso(metadata.indexed_at)
                doc_group.attrs[_ATTR_ATTRIBUTES] = json.dumps(metadata.attributes)
        return True

    def _delete_document_sync(self, namespace: str, document_id: str) -> bool:
        with h5py.File(self.file_path, "a") as f:
            path = f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}/{document_id}"
            if path not in f:
                return False
            del f[path]
        return True

    def _save_chunks_sync(
        self,
        namespace: str,
        document_id: str,
        chunks: list[ChunkWithEmbedding],
    ) -> tuple[int, list[_IndexEntry]]:
        if not chunks:
            return 0, []

        new_entries: list[_IndexEntry] = []
        saved = 0
        with h5py.File(self.file_path, "a") as f:
            doc_path = f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}/{document_id}"
            if doc_path not in f:
                raise ValueError(
                    f"Document {document_id!r} does not exist in namespace "
                    f"{namespace!r}. Call create_document first."
                )
            doc_group = f[doc_path]
            chunks_group = doc_group.require_group(_CHUNKS_GROUP)

            for ce in chunks:
                chunk_id = _chunk_id_from(ce.chunk)
                if chunk_id in chunks_group:
                    # Idempotent on (doc_id, source_ref, text). Skip.
                    continue
                chunk_group = chunks_group.create_group(chunk_id)
                chunk_group.attrs[_CHUNK_TEXT] = ce.chunk.text
                chunk_group.attrs[_CHUNK_SOURCE_TYPE] = ce.chunk.source_type
                chunk_group.attrs[_CHUNK_SOURCE_REF] = ce.chunk.source_ref
                chunk_group.attrs[_CHUNK_CREATED_AT] = _iso(
                    ce.chunk.created_at or _now()
                )
                vec = np.asarray(ce.embedding, dtype=np.float32)
                chunk_group.create_dataset(
                    _EMBEDDING_DATASET, data=vec, compression="gzip"
                )
                new_entries.append(
                    _IndexEntry(
                        chunk_id=chunk_id, document_id=document_id, embedding=vec
                    )
                )
                saved += 1

            # Update document indexed_at + status on first non-empty save.
            if saved > 0:
                doc_group.attrs[_ATTR_INDEXED_AT] = _iso(_now())
                current_status = doc_group.attrs.get(_ATTR_STATUS, "")
                if current_status == "pending":
                    doc_group.attrs[_ATTR_STATUS] = "indexed"

        return saved, new_entries

    def _get_chunks_by_document_sync(
        self, namespace: str, document_id: str
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        with h5py.File(self.file_path, "r") as f:
            path = f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}/{document_id}/{_CHUNKS_GROUP}"
            if path not in f:
                return []
            chunks_group = f[path]
            for chunk_id in chunks_group:
                chunk_group = chunks_group[chunk_id]
                chunks.append(_to_chunk(chunk_group))
        return chunks

    def _delete_chunks_by_document_sync(
        self, namespace: str, document_id: str
    ) -> int:
        with h5py.File(self.file_path, "a") as f:
            chunks_path = (
                f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}/{document_id}/{_CHUNKS_GROUP}"
            )
            if chunks_path not in f:
                return 0
            count = len(f[chunks_path])
            del f[chunks_path]
            # Re-create empty chunks group so subsequent writes work.
            doc_path = f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}/{document_id}"
            f[doc_path].create_group(_CHUNKS_GROUP)
        return count

    def _reindex_document_sync(self, namespace: str, document_id: str) -> bool:
        with h5py.File(self.file_path, "r") as f:
            doc_path = f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}/{document_id}"
            if doc_path not in f:
                return False
            chunks_path = f"{doc_path}/{_CHUNKS_GROUP}"
            if chunks_path not in f:
                return True
            # Drop existing entries for this doc, re-load from disk.
            idx = self._index.setdefault(namespace, _NamespaceIndex())
            idx.remove_document(document_id)
            chunks_group = f[chunks_path]
            for chunk_id in chunks_group:
                chunk_group = chunks_group[chunk_id]
                if _EMBEDDING_DATASET not in chunk_group:
                    continue
                vec = np.asarray(chunk_group[_EMBEDDING_DATASET][:], dtype=np.float32)
                idx.add(
                    _IndexEntry(
                        chunk_id=str(chunk_id), document_id=document_id, embedding=vec
                    )
                )
        return True

    def _query_sync(
        self,
        namespace: str,
        query_embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        idx = self._index.get(namespace)
        if not idx or not idx.entries:
            return []
        entries = idx.entries
        if filters:
            # Restrict to chunks whose parent document's attributes match BEFORE
            # top-k (post-filtering would starve the floor).
            allowed = self._documents_matching(namespace, filters)
            entries = [e for e in entries if e.document_id in allowed]
            if not entries:
                return []
        q = np.asarray(query_embedding, dtype=np.float32)
        q_norm = float(np.linalg.norm(q))
        if q_norm == 0.0:
            return []
        embeddings = np.stack([e.embedding for e in entries])
        norms = np.linalg.norm(embeddings, axis=1)
        # Avoid division by zero for any zero-vector chunk.
        norms[norms == 0.0] = 1.0
        sims = (embeddings @ q) / (norms * q_norm)
        # Argpartition gets top-k unsorted; sort just those.
        k = min(top_k, len(sims))
        top_unsorted = np.argpartition(-sims, k - 1)[:k]
        top_sorted = top_unsorted[np.argsort(-sims[top_unsorted])]

        results: list[RetrievedChunk] = []
        # Hydrate chunks from disk (in-memory index only carries embeddings).
        with h5py.File(self.file_path, "r") as f:
            for i in top_sorted:
                entry = entries[int(i)]
                chunk_path = (
                    f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}/"
                    f"{entry.document_id}/{_CHUNKS_GROUP}/{entry.chunk_id}"
                )
                if chunk_path not in f:
                    # Index drift — skip silently. Caller can call reindex.
                    continue
                chunk = _to_chunk(f[chunk_path])
                results.append(
                    RetrievedChunk(chunk=chunk, similarity=float(sims[int(i)]))
                )
        return results

    def _documents_matching(self, namespace: str, filters: dict[str, Any]) -> set[str]:
        """Document ids in ``namespace`` whose attributes contain every key/value
        in ``filters`` (flat equality — the HDF5 analogue of Postgres ``@>``)."""
        matched: set[str] = set()
        docs_path = f"{_NS_GROUP}/{namespace}/{_DOCS_GROUP}"
        with h5py.File(self.file_path, "r") as f:
            if docs_path not in f:
                return matched
            docs_group = f[docs_path]
            for doc_id in docs_group:
                raw = docs_group[doc_id].attrs.get(_ATTR_ATTRIBUTES, "{}")
                try:
                    attrs = json.loads(raw)
                except (TypeError, ValueError):
                    attrs = {}
                if isinstance(attrs, dict) and all(attrs.get(k) == v for k, v in filters.items()):
                    matched.add(doc_id)
        return matched

    # ------------------------------------------------------------------
    # Index bootstrap
    # ------------------------------------------------------------------

    def _rebuild_full_index(self) -> None:
        """Load all embeddings from disk into the in-memory index.

        Called once on construction. For large stores this can be slow
        (1-2 seconds per 10k chunks); consumers that need lazy loading
        should subclass and override.
        """
        with h5py.File(self.file_path, "r") as f:
            if _NS_GROUP not in f:
                return
            ns_root = f[_NS_GROUP]
            for namespace in ns_root:
                docs_path = f"{namespace}/{_DOCS_GROUP}"
                if docs_path not in ns_root:
                    continue
                docs_group = ns_root[docs_path]
                ns_idx = _NamespaceIndex()
                for doc_id in docs_group:
                    chunks_path = f"{doc_id}/{_CHUNKS_GROUP}"
                    if chunks_path not in docs_group:
                        continue
                    chunks_group = docs_group[chunks_path]
                    for chunk_id in chunks_group:
                        chunk_group = chunks_group[chunk_id]
                        if _EMBEDDING_DATASET not in chunk_group:
                            continue
                        vec = np.asarray(
                            chunk_group[_EMBEDDING_DATASET][:], dtype=np.float32
                        )
                        ns_idx.add(
                            _IndexEntry(
                                chunk_id=str(chunk_id),
                                document_id=str(doc_id),
                                embedding=vec,
                            )
                        )
                if ns_idx.entries:
                    self._index[str(namespace)] = ns_idx

    async def _ensure_document_exists(
        self, *, namespace: str, document_id: str, content: str
    ) -> None:
        """For ChunkStore.add — synthesize parent document if missing."""
        existing = await self.get_document(namespace=namespace, document_id=document_id)
        if existing is None:
            try:
                await self.create_document(
                    namespace=namespace, document_id=document_id, content=content
                )
            except ValueError:
                # Race condition on concurrent ChunkStore.add — re-check.
                pass


# ----------------------------------------------------------------------
# Internal converters / helpers
# ----------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _to_chunk(chunk_group: Any) -> Chunk:
    """Reconstruct a Chunk dataclass from an HDF5 group."""
    return Chunk(
        text=str(chunk_group.attrs.get(_CHUNK_TEXT, "")),
        source_type=str(chunk_group.attrs.get(_CHUNK_SOURCE_TYPE, "")),
        source_ref=str(chunk_group.attrs.get(_CHUNK_SOURCE_REF, "")),
        created_at=_parse_iso(chunk_group.attrs.get(_CHUNK_CREATED_AT)),
    )


def _to_document_record(
    namespace: str, document_id: str, doc_group: Any
) -> DocumentRecord:
    """Reconstruct a DocumentRecord from an HDF5 document group."""
    raw_attrs = doc_group.attrs.get(_ATTR_ATTRIBUTES, "{}")
    try:
        attributes = json.loads(raw_attrs) if raw_attrs else {}
    except (ValueError, TypeError):
        attributes = {}

    metadata = DocumentMetadata(
        status=str(doc_group.attrs.get(_ATTR_STATUS, "pending")),
        created_at=_parse_iso(doc_group.attrs.get(_ATTR_CREATED_AT)),
        indexed_at=_parse_iso(doc_group.attrs.get(_ATTR_INDEXED_AT)),
        attributes=attributes,
    )
    chunk_count = (
        len(doc_group[_CHUNKS_GROUP]) if _CHUNKS_GROUP in doc_group else 0
    )
    return DocumentRecord(
        document_id=document_id,
        namespace=namespace,
        content=str(doc_group.attrs.get(_ATTR_CONTENT, "")),
        metadata=metadata,
        chunk_count=chunk_count,
    )


def _chunk_id_from(chunk: Chunk) -> str:
    """Deterministic chunk_id from (source_ref, text-hash-prefix).

    Idempotency contract: re-running an ingest with the same Chunk
    must produce the same chunk_id so the HDF5 create_group call
    short-circuits.
    """
    text_hash = format(abs(hash(chunk.text)) % (1 << 32), "08x")
    safe_source_ref = chunk.source_ref.replace("/", "_").replace(":", "_")
    return f"{safe_source_ref}_{text_hash}"
