"""Protocol classes — the boundary between fi-core and the consumer's stack.

fi-core ships Protocols + reference implementations. Each consumer
either uses a provided implementation (from ``fi_core.stores`` or
``fi_core.embeddings`` under optional-deps install extras), or brings
its own.

Two layers of Protocol:

  - ``Embedder`` / ``ChunkStore`` — minimum interface for plain RAG:
    embed text → store chunks with embeddings → query by similarity.
    Sufficient for simple consumers that don't need document lifecycle.

  - ``DocumentChunkStore`` (extends ``ChunkStore``) — adds parent
    document concept + lifecycle status + bulk operations. Used by
    AURITY (medical RAG with document CRUD), Insult Tier 2 (mental-
    science longitudinal layer), Robo-Poet (training corpus reader).
    Implementations are free to support only the base ``ChunkStore``
    if they don't need document semantics.

Using Protocol classes (not abstract base classes) means both sides
can type-check their compositions without inheriting from a shared
base — duck-typed at definition time, structurally matched at
composition time.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fi_core.rag.types import (
    Chunk,
    ChunkWithEmbedding,
    DocumentMetadata,
    DocumentRecord,
    RetrievedChunk,
)


@runtime_checkable
class Embedder(Protocol):
    """Anything that turns text into a fixed-dim vector.

    Implementations:
    - AURITY: ``MonitorClientEmbedder`` wraps the Cloudflare-tunneled
      GPU service (sentence-transformers, 384 dims).
    - Insult: ``AzureOpenAIEmbedder`` calls Azure OpenAI's ada-002
      deployment (1536 dims).

    The dimension is NOT part of the protocol — store and embedder must
    agree on it at composition time. fi-core doesn't enforce.
    """

    async def embed(self, text: str) -> list[float]:
        """Return the embedding vector for `text`.

        Implementations should raise on failure (let the caller decide
        whether to retry, fall back, or skip). Returning empty / zero
        vectors silently is a footgun.
        """
        ...


@runtime_checkable
class ChunkStore(Protocol):
    """Anything that persists embedded chunks and answers similarity queries.

    Implementations:
    - AURITY: ``HDF5DocumentStore`` (per-document group, append-only).
    - Insult: ``PgVectorStore`` (single table, ivfflat index, per-user filter).

    Both ``add`` and ``query`` are async because realistic implementations
    talk to remote stores (database, file lock, etc.). Pure in-memory
    implementations can ``async def`` and immediately return.
    """

    async def add(self, *, namespace: str, chunk: Chunk, embedding: list[float]) -> None:
        """Persist one chunk + its precomputed embedding under `namespace`.

        `namespace` is the per-tenant scope — user_id for Insult,
        document filename for AURITY. The store decides how to use it
        (column filter, separate index, separate file).

        Should be idempotent on (namespace, chunk.source_ref, chunk.text)
        — re-running an ingest pipeline should never duplicate chunks.
        """
        ...

    async def query(
        self,
        *,
        namespace: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Return the top-k chunks closest to `query_embedding` in `namespace`.

        Results sorted by similarity descending (most similar first).
        Returns empty list when the namespace has no chunks, NOT an error.
        """
        ...


@runtime_checkable
class DocumentChunkStore(ChunkStore, Protocol):
    """Extends ChunkStore with parent-document lifecycle + bulk operations.

    Implementations of this protocol model chunks as children of a
    parent document. The document carries its own lifecycle status
    ("pending", "indexed", "failed", etc.) and free-form attributes
    in ``DocumentMetadata.attributes``. Bulk operations and cascading
    deletes operate at document granularity.

    Use cases:
    - AURITY: medical documents with clinic_id attribute, chunks are
      paragraphs of patient records.
    - Insult Tier 2 (future): "documents" are sessions, chunks are
      vulnerability snapshots / fact extractions over time.
    - Robo-Poet (future): training corpus reader — iterates documents
      and consumes their chunks as training tokens.

    Implementations that only need the chunk-level operations should
    implement only ``ChunkStore`` instead.
    """

    async def create_document(
        self,
        *,
        namespace: str,
        document_id: str,
        content: str,
        metadata: DocumentMetadata | None = None,
    ) -> str:
        """Create a document record under ``namespace``.

        Returns the document_id on success. Raises if a document with
        the same (namespace, document_id) already exists — callers
        that want upsert semantics should call ``update_document``
        after catching the duplicate exception.

        ``content`` is the full document text. Implementations may
        persist it directly, defer chunking until ``save_chunks``,
        or both — fi-core does not prescribe. ``metadata.attributes``
        is stored as-is.
        """
        ...

    async def get_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> DocumentRecord | None:
        """Return the document record, or ``None`` if not found.

        ``chunk_count`` in the returned record reflects the current
        number of chunks saved under this document. Implementations
        may compute it on read or cache it on write — fi-core does
        not prescribe.
        """
        ...

    async def list_documents(
        self,
        *,
        namespace: str,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[DocumentRecord]:
        """List documents in ``namespace``, optionally filtered by status.

        ``status=None`` returns all documents regardless of state.
        ``limit=None`` returns all matches. Implementations may order
        by ``created_at`` descending by default — fi-core does not
        prescribe, but consumers should not rely on insertion order.
        """
        ...

    async def update_document(
        self,
        *,
        namespace: str,
        document_id: str,
        content: str | None = None,
        metadata: DocumentMetadata | None = None,
    ) -> bool:
        """Update content and/or metadata of an existing document.

        Both arguments are optional — pass only what you want to
        change. Returns ``True`` if the document existed and was
        updated, ``False`` if it did not exist.

        Updating content does NOT invalidate existing chunks —
        callers are responsible for calling ``delete_chunks_by_document``
        + ``save_chunks`` if a re-chunk is needed.
        """
        ...

    async def delete_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> bool:
        """Delete a document and ALL its chunks (cascading).

        Returns ``True`` if the document existed and was deleted,
        ``False`` if it did not exist. The cascade is mandatory —
        leaving orphaned chunks behind would corrupt the vector
        index.
        """
        ...

    async def save_chunks(
        self,
        *,
        namespace: str,
        document_id: str,
        chunks: list[ChunkWithEmbedding],
    ) -> int:
        """Bulk-insert chunks under a document. Returns number saved.

        Implementations should be idempotent on
        ``(namespace, document_id, chunk.source_ref, chunk.text)`` —
        re-running an ingest pipeline must not duplicate chunks.
        Raises if the parent document does not exist.

        After successful save, implementations SHOULD update the
        document's ``indexed_at`` timestamp and ``status`` (typically
        to "indexed"). Consumers that want a different lifecycle should
        call ``update_document`` themselves.
        """
        ...

    async def get_chunks_by_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> list[Chunk]:
        """Return all chunks under a document.

        Order is not guaranteed unless the implementation document
        specifies otherwise. For ordered iteration (e.g. training
        corpus reads), consumers should sort by ``Chunk.source_ref``
        or similar deterministic key on their side.

        Returns empty list when the document has no chunks, NOT an error.
        """
        ...

    async def delete_chunks_by_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> int:
        """Delete all chunks under a document. Returns count deleted.

        Does NOT delete the parent document — use ``delete_document``
        for cascading delete. After this call, the document record
        still exists with ``chunk_count == 0``.
        """
        ...

    async def reindex_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> bool:
        """Rebuild the in-memory vector index for a document.

        Implementations that maintain an in-memory cache of embeddings
        for fast similarity search should reload it from persistent
        storage when this is called. Useful after bulk migrations or
        out-of-band writes that bypass ``save_chunks``.

        Returns ``True`` if the document existed and was reindexed,
        ``False`` if it did not exist. Implementations that don't
        maintain an in-memory index may treat this as a no-op and
        return ``True``.
        """
        ...
