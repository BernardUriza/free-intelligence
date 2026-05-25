"""Reranking — a second, cross-encoder pass over retrieved candidates.

Bi-encoder retrieval (embed query, embed docs, cosine) is fast but coarse: the
query and a doc are embedded SEPARATELY, so fine relevance is lost. A reranker
(cross-encoder) reads the query and each candidate TOGETHER and scores their
joint relevance — far more calibrated. The standard recipe: retrieve 50–100
cheap candidates, rerank, keep the top 10.

fi-core ships the Protocol + a reference impl; the model dep is an extra:
- :class:`Reranker` — the port (consumer can bring Cohere, a custom model, ...).
- :class:`BgeReranker` — ``BAAI/bge-reranker-v2-m3`` (multilingual, Apache-2.0,
  self-host) via sentence-transformers ``CrossEncoder``. Needs ``fi-core[rerank]``.
- :class:`RerankingRetriever` — wraps ANY retriever (StoreBacked / Hybrid):
  over-fetch a candidate pool, rerank, return top-k. Reorders the original
  RetrievedChunks (their similarity is preserved; the rerank score drives ORDER).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from fi_core.rag.types import RetrievedChunk


@dataclass(frozen=True)
class RerankResult:
    """One reranked candidate: its ``index`` into the input list + ``score``
    (higher = more relevant; the scale is the reranker's, not necessarily [0,1])."""

    index: int
    score: float


@runtime_checkable
class Reranker(Protocol):
    """Scores query–document pairs jointly and returns them best-first."""

    async def rerank(self, query: str, documents: list[str]) -> list[RerankResult]:
        """Return :class:`RerankResult` for each document, sorted best-first."""
        ...


@runtime_checkable
class SupportsRetrieve(Protocol):
    """Anything with the retriever shape (StoreBackedRetriever, HybridRetriever)."""

    async def retrieve(self, query: str, *, namespace: str, top_k: int = 5) -> list[RetrievedChunk]:
        ...


@dataclass
class BgeReranker:
    """``BAAI/bge-reranker-v2-m3`` cross-encoder reranker (multilingual).

    Lazy-loads the model on first use (it's ~600MB) and runs the blocking
    ``predict`` off the event loop. Requires ``fi-core[rerank]``."""

    model_name: str = "BAAI/bge-reranker-v2-m3"
    device: str | None = None
    _model: Any = field(default=None, init=False, repr=False)

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise ImportError(
                    "BgeReranker requires the rerank extra: pip install 'fi-core[rerank]'"
                ) from exc
            self._model = CrossEncoder(self.model_name, device=self.device)
        return self._model

    async def rerank(self, query: str, documents: list[str]) -> list[RerankResult]:
        if not documents:
            return []
        model = self._get_model()
        pairs = [(query, d) for d in documents]
        scores = await asyncio.to_thread(model.predict, pairs)  # blocking → off-loop
        ranked = sorted(enumerate(scores), key=lambda x: float(x[1]), reverse=True)
        return [RerankResult(index=i, score=float(s)) for i, s in ranked]


@dataclass
class RerankingRetriever:
    """Wrap a retriever with a reranking pass: over-fetch, rerank, return top-k.

    ``base`` is any retriever (StoreBackedRetriever / HybridRetriever). The
    returned chunks are the originals (their similarity preserved) REORDERED by
    the reranker; pass-through when the pool is empty."""

    base: SupportsRetrieve
    reranker: Reranker
    candidate_k: int = 50  # over-fetch pool size before reranking

    async def retrieve(
        self,
        query: str,
        *,
        namespace: str,
        top_k: int = 5,
        candidate_k: int | None = None,
    ) -> list[RetrievedChunk]:
        if not query or not query.strip():
            return []
        pool = await self.base.retrieve(query, namespace=namespace, top_k=candidate_k or self.candidate_k)
        if not pool:
            return []
        ranked = await self.reranker.rerank(query, [h.chunk.text for h in pool])
        return [pool[r.index] for r in ranked[:top_k]]


__all__ = ["BgeReranker", "RerankResult", "Reranker", "RerankingRetriever", "SupportsRetrieve"]
