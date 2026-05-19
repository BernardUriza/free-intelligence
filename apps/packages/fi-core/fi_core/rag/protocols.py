"""Protocol classes — the boundary between fi-core and the consumer's stack.

fi-core does NOT ship an Embedder or ChunkStore. Each consumer brings
its own:

  - AURITY: sentence-transformers on the clinic GPU + HDF5 append-only
  - Insult: Azure OpenAI ada-002 + Postgres pgvector

The chunking algorithm is the only thing both share at the byte level.
Everything else (embedding latency, dimensionality, storage shape) is
specific to the deployment. Using Protocol classes here means both
sides can type-check their compositions without inheriting from a
shared base class — duck-typed at definition time, structurally
matched at composition time.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fi_core.rag.types import Chunk, RetrievedChunk


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
