"""Store-backed retrieval — the PERSISTENT half of RAG (embed query → store → chunks).

The in-memory retrievers in :mod:`fi_core.rag.retrieval` rank text the agent
already holds. This closes the classic document-RAG loop over a vector store:

- ``retrieve(query)`` embeds the query and runs the store's similarity search.
- ``ingest(text)`` chunks a document, embeds each chunk, and persists them.

It glues an :class:`~fi_core.rag.protocols.Embedder` + a
:class:`~fi_core.rag.protocols.ChunkStore` (the HDF5 or pgvector reference impls,
or any Protocol implementation) into one object. fi-core stays backend-agnostic:
you pass the embedder and the store — this module imports neither a model nor a
database, so it carries no optional deps of its own.

This is also the ONE write path: :class:`~fi_core.rag.store_service.RagStore`
embeds through :meth:`StoreBackedRetriever.embed_chunks` and persists through
:meth:`StoreBackedRetriever.replace_document`, so a contextualizer wired here
reaches every ingest and a re-ingest replaces on every face.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fi_core.rag.chunking import ChunkConfig, ChunkingStrategy, chunk_document
from fi_core.rag.contextual import Contextualizer
from fi_core.rag.protocols import ChunkStore, DocumentChunkStore, Embedder
from fi_core.rag.types import Chunk, ChunkWithEmbedding, DocumentMetadata, RetrievedChunk


@dataclass
class StoreBackedRetriever:
    """Persistent RAG over an Embedder + a ChunkStore.

    ``min_similarity`` is a default floor applied to retrieval results (0.0 = no
    floor; let the store's ``top_k`` decide). Per-call ``min_similarity`` on
    :meth:`retrieve` overrides it.

    ``contextualizer`` enables Contextual Retrieval: each chunk is embedded with
    an LLM-generated situating context prepended, while the ORIGINAL chunk text
    is what gets stored — so recall improves and citations stay faithful.
    """

    embedder: Embedder
    store: ChunkStore
    min_similarity: float = 0.0
    contextualizer: Contextualizer | None = None

    async def retrieve(
        self,
        query: str,
        *,
        namespace: str,
        top_k: int = 5,
        min_similarity: float | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Embed ``query`` and return the top-k most similar chunks in ``namespace``.

        Empty/blank query → empty list (no embedder call). Results keep the
        store's similarity-descending order; a positive floor drops weak hits.
        ``filters`` restricts to chunks whose parent document's attributes match
        (forwarded to the store)."""
        if not query or not query.strip():
            return []
        query_embedding = await self.embedder.embed(query)
        hits = await self.store.query(
            namespace=namespace, query_embedding=query_embedding, top_k=top_k, filters=filters
        )
        floor = self.min_similarity if min_similarity is None else min_similarity
        if floor > 0:
            return [h for h in hits if h.similarity >= floor]
        return list(hits)

    async def embed_chunks(
        self,
        pieces: list[str],
        *,
        document: str,
        source_ref: str,
        source_type: str = "document",
        created_at: datetime | None = None,
    ) -> list[ChunkWithEmbedding]:
        """Embed each piece of ``document`` and pair it with its :class:`Chunk`.

        With a contextualizer set, the EMBEDDING is computed over
        ``"<context>\\n\\n<chunk>"`` while the returned Chunk keeps the plain
        piece — the store never sees the context, so a citation quotes the
        source verbatim. An empty context leaves that chunk plain."""
        out: list[ChunkWithEmbedding] = []
        for piece in pieces:
            to_embed = piece
            if self.contextualizer is not None:
                context = await self.contextualizer.contextualize(document=document, chunk=piece)
                if context:
                    to_embed = f"{context}\n\n{piece}"
            embedding = await self.embedder.embed(to_embed)
            chunk = Chunk(text=piece, source_type=source_type, source_ref=source_ref, created_at=created_at)
            out.append(ChunkWithEmbedding(chunk, embedding))
        return out

    async def replace_document(
        self,
        *,
        namespace: str,
        document_id: str,
        content: str,
        chunks: list[ChunkWithEmbedding],
        attributes: dict[str, Any] | None = None,
    ) -> int:
        """Persist ``chunks`` as THE chunks of ``document_id`` on a DocumentChunkStore.

        An existing document has its chunks deleted and its content updated
        before the new chunks are saved; a new one is created. ``attributes=None``
        keeps the attributes an existing document already carries; a dict
        replaces them. Returns the number of chunks saved."""
        store = self._document_store()
        existing = await store.get_document(namespace=namespace, document_id=document_id)
        if existing is not None:
            keep = getattr(getattr(existing, "metadata", None), "attributes", None) or {}
            md = DocumentMetadata(attributes=attributes if attributes is not None else keep)
            await store.delete_chunks_by_document(namespace=namespace, document_id=document_id)
            await store.update_document(namespace=namespace, document_id=document_id, content=content, metadata=md)
        else:
            await store.create_document(
                namespace=namespace, document_id=document_id, content=content,
                metadata=DocumentMetadata(attributes=attributes or {}),
            )
        return await store.save_chunks(namespace=namespace, document_id=document_id, chunks=chunks) if chunks else 0

    async def ingest(
        self,
        text: str,
        *,
        namespace: str,
        source_ref: str,
        source_type: str = "document",
        strategy: ChunkingStrategy | None = None,
        config: ChunkConfig | None = None,
    ) -> int:
        """Chunk ``text``, embed each chunk, and persist them under ``namespace``.

        Returns the number of chunks stored; blank text (or text that chunks to
        nothing) returns 0 without touching the store. ``source_ref`` traces a
        recalled chunk back to its origin (filename, url, ...).

        On a :class:`~fi_core.rag.protocols.DocumentChunkStore`, ``source_ref``
        IS the document id: re-ingesting a corrected text under the same
        ``source_ref`` REPLACES its chunks (content updated, attributes kept),
        so the previous version stops being retrievable.

        A plain :class:`~fi_core.rag.protocols.ChunkStore` has no document
        concept, so it CANNOT replace a source_ref's chunks: ``add`` only dedupes
        identical text, and an edited text lands beside the old one. Use a
        DocumentChunkStore when documents get corrected."""
        if not text or not text.strip():
            return 0
        pieces = chunk_document(text, strategy or ChunkingStrategy("paragraph_aware"), config or ChunkConfig())
        if not pieces:
            return 0
        chunks = await self.embed_chunks(
            pieces, document=text, source_ref=source_ref, source_type=source_type, created_at=datetime.now(tz=UTC)
        )
        if isinstance(self.store, DocumentChunkStore):
            return await self.replace_document(
                namespace=namespace, document_id=source_ref, content=text, chunks=chunks
            )
        for ce in chunks:
            await self.store.add(namespace=namespace, chunk=ce.chunk, embedding=ce.embedding)
        return len(chunks)

    def _document_store(self) -> DocumentChunkStore:
        if not isinstance(self.store, DocumentChunkStore):
            raise TypeError(
                f"{type(self.store).__name__} is a plain ChunkStore (add/query); "
                "replacing a document's chunks needs a DocumentChunkStore"
            )
        return self.store


__all__ = ["StoreBackedRetriever"]
