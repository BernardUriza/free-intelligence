"""``fi_core.rag.protocols.Embedder`` adapter over the local MiniLM model.

``fi_core.memory.PgMemoryStore`` accepts an optional ``embedder`` at
construction and uses it to populate the inline ``embedding`` column on
``principal_facts`` (on save/add/consolidate) and to embed the query for
``semantic_search``. The Protocol it expects is::

    async def embed(self, text: str) -> list[float]

The bot already ships the embedding model (``all-MiniLM-L6-v2``, 384d,
normalized) in ``core/vectors.EmbeddingModel`` — a thread-safe lazy
singleton that ``connection.py`` pre-warms at boot. This class is the
thin async bridge: ``sentence-transformers`` ``encode`` is sync CPU work,
so we hand it to a worker thread via ``asyncio.to_thread`` to keep the
event loop (Discord gateway heartbeat) responsive.

Kept deliberately small and dependency-light so it satisfies
``isinstance(MiniLMEmbedder(), fi_core.rag.protocols.Embedder)`` via the
``@runtime_checkable`` Protocol without importing fi-core at all.
"""

from __future__ import annotations

import asyncio


class MiniLMEmbedder:
    """Async ``Embedder`` backed by the shared MiniLM singleton (384d).

    Structural match for ``fi_core.rag.protocols.Embedder`` — no nominal
    inheritance, the Protocol is duck-typed. Reuses
    ``core/vectors.get_embedding_model()`` so there is exactly ONE model
    instance in the process (the same one ``connection.py`` pre-warms at
    boot and the consolidator's deep-memory path used historically).
    """

    EMBEDDING_DIM = 384

    async def embed(self, text: str) -> list[float]:
        """Return the 384-dim normalized embedding for ``text``.

        Runs the blocking ``sentence-transformers`` encode in a thread so
        the event loop is never stalled. Raises ``ValueError`` on empty
        input to match the fail-loud contract the Protocol callers expect
        (``PgMemoryStore`` isolates the failure per-row and falls back to a
        NULL embedding, so a raise here never corrupts a write)."""
        if not text or not text.strip():
            raise ValueError("MiniLMEmbedder.embed: text must be non-empty")
        from khimeras_shared.vectors import get_embedding_model

        return await asyncio.to_thread(get_embedding_model().embed, text)
