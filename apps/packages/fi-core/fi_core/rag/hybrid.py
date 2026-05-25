"""Hybrid retrieval — fuse dense (vector) + lexical ranking with RRF.

Pure semantic search misses exact keywords / proper nouns that are rare in the
embedder's training (and an English-centric embedder under-weights short Spanish
text — fi-core's whole reason for a lexical arm). Hybrid retrieval runs both and
fuses them with Reciprocal Rank Fusion (RRF), which combines by RANK, not score,
so the incomparable scales of cosine and term-overlap never need normalizing.

:func:`reciprocal_rank_fusion` is the generic primitive (also used by
``fi_core.memory`` for fact recall). :class:`HybridRetriever` re-ranks a
:class:`~fi_core.rag.store_retrieval.StoreBackedRetriever`'s dense candidate pool
with the Spanish-tuned :class:`~fi_core.rag.retrieval.LexicalRetriever`: a chunk
the dense ranker under-weighted but that exactly matches a query keyword floats
up. (It fuses over the dense candidate pool, so a chunk the dense arm misses
entirely is not recovered — a separate sparse index over the store would be the
next step; for fi-core's small/medium corpora the over-fetch pool covers it.)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TypeVar

from fi_core.rag.retrieval import LexicalRetriever
from fi_core.rag.store_retrieval import StoreBackedRetriever
from fi_core.rag.types import RetrievedChunk

K = TypeVar("K")

#: RRF default (the standard; rank-1 contributes 1/(60+1)). Matches fi_core.memory.
DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(rankings: list[list[K]], *, k: int = DEFAULT_RRF_K) -> dict[K, float]:
    """Fuse several ranked lists into one score per key. Each list contributes
    ``1 / (k + rank)`` per key (rank 1-based); a key in multiple lists accumulates,
    so an item strong in BOTH arms outranks one strong in only one — while a
    single strong arm still surfaces it. Order-only: no comparable score scales
    needed across arms (why RRF beats a naive weighted sum)."""
    scores: dict[K, float] = defaultdict(float)
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            scores[key] += 1.0 / (k + rank)
    return dict(scores)


@dataclass
class HybridRetriever:
    """Dense (store) + lexical retrieval fused by RRF over the candidate pool."""

    dense: StoreBackedRetriever
    lexical: LexicalRetriever = field(default_factory=LexicalRetriever)
    rrf_k: int = DEFAULT_RRF_K
    candidate_k: int = 50  # dense over-fetch pool size before fusion

    async def retrieve(
        self,
        query: str,
        *,
        namespace: str,
        top_k: int = 5,
        candidate_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Over-fetch the dense pool, re-rank it lexically, fuse with RRF, return
        the top-k. Empty/blank query or empty pool → empty list."""
        if not query or not query.strip():
            return []
        pool = await self.dense.retrieve(
            query, namespace=namespace, top_k=candidate_k or self.candidate_k, min_similarity=0.0
        )
        if not pool:
            return []
        # Dense arm: the pool is already similarity-descending → pool index order.
        dense_order = list(range(len(pool)))
        # Lexical arm: score each pool chunk, keep the ones with a real match.
        scored = [(i, self.lexical.score(query, h.chunk.text)) for i, h in enumerate(pool)]
        lexical_order = [i for i, s in sorted(scored, key=lambda x: x[1], reverse=True) if s > 0]
        fused = reciprocal_rank_fusion([dense_order, lexical_order], k=self.rrf_k)
        ranked = sorted(fused, key=lambda i: fused[i], reverse=True)
        return [pool[i] for i in ranked[:top_k]]


__all__ = ["DEFAULT_RRF_K", "HybridRetriever", "reciprocal_rank_fusion"]
