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
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fi_core.rag.chunking import ChunkConfig, ChunkingStrategy, chunk_document
from fi_core.rag.protocols import ChunkStore, Embedder
from fi_core.rag.types import Chunk, RetrievedChunk


@dataclass
class StoreBackedRetriever:
    """Persistent RAG over an Embedder + a ChunkStore.

    ``min_similarity`` is a default floor applied to retrieval results (0.0 = no
    floor; let the store's ``top_k`` decide). Per-call ``min_similarity`` on
    :meth:`retrieve` overrides it.
    """

    embedder: Embedder
    store: ChunkStore
    min_similarity: float = 0.0

    async def retrieve(
        self,
        query: str,
        *,
        namespace: str,
        top_k: int = 5,
        min_similarity: float | None = None,
    ) -> list[RetrievedChunk]:
        """Embed ``query`` and return the top-k most similar chunks in ``namespace``.

        Empty/blank query → empty list (no embedder call). Results keep the
        store's similarity-descending order; a positive floor drops weak hits."""
        if not query or not query.strip():
            return []
        query_embedding = await self.embedder.embed(query)
        hits = await self.store.query(namespace=namespace, query_embedding=query_embedding, top_k=top_k)
        floor = self.min_similarity if min_similarity is None else min_similarity
        if floor > 0:
            return [h for h in hits if h.similarity >= floor]
        return list(hits)

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

        Returns the number of chunks stored. ``source_ref`` traces a recalled
        chunk back to its origin (filename, url, ...). Idempotency is the store's
        responsibility (re-ingesting the same source must not duplicate)."""
        if not text or not text.strip():
            return 0
        pieces = chunk_document(text, strategy or ChunkingStrategy("paragraph_aware"), config or ChunkConfig())
        now = datetime.now(tz=UTC)
        count = 0
        for piece in pieces:
            embedding = await self.embedder.embed(piece)
            await self.store.add(
                namespace=namespace,
                chunk=Chunk(text=piece, source_type=source_type, source_ref=source_ref, created_at=now),
                embedding=embedding,
            )
            count += 1
        return count


__all__ = ["StoreBackedRetriever"]
