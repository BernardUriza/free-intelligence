"""Tests for reranking — RerankingRetriever + the rerank MCP tool.

Uses fake rerankers (no 600MB model download). The real BgeReranker is verified
separately (manual smoke); here we pin the composition + wiring + graceful errors.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from fi_core.rag import (
    Chunk,
    RerankingRetriever,
    RerankResult,
    RetrievedChunk,
)


@dataclass
class _FakeBase:
    pool: list[RetrievedChunk]
    seen_top_k: int | None = None

    async def retrieve(self, query, *, namespace, top_k=5, filters=None):  # noqa: ANN001
        self.seen_top_k = top_k
        return self.pool[:top_k]


@dataclass
class _ReverseReranker:
    """Reverses the candidate order — deterministic, no model."""

    async def rerank(self, query, documents):  # noqa: ANN001
        n = len(documents)
        return [RerankResult(index=i, score=float(rank)) for rank, i in enumerate(reversed(range(n)))]


@dataclass
class _KeepReranker:
    """Ranks documents containing 'KEEP' first (deterministic)."""

    async def rerank(self, query, documents):  # noqa: ANN001
        order = sorted(range(len(documents)), key=lambda i: "KEEP" in documents[i], reverse=True)
        return [RerankResult(index=i, score=float(len(documents) - rank)) for rank, i in enumerate(order)]


def _chunk(text: str, sim: float) -> RetrievedChunk:
    return RetrievedChunk(chunk=Chunk(text=text, source_type="document", source_ref="d"), similarity=sim)


# --- RerankingRetriever -------------------------------------------------------


@pytest.mark.asyncio
async def test_reranking_reorders_pool_and_overfetches():
    pool = [_chunk("A", 0.9), _chunk("B", 0.8), _chunk("C", 0.7)]
    base = _FakeBase(pool)
    rr = RerankingRetriever(base=base, reranker=_ReverseReranker(), candidate_k=50)
    out = await rr.retrieve("q", namespace="n", top_k=2)
    assert base.seen_top_k == 50  # over-fetched the candidate pool
    assert [h.chunk.text for h in out] == ["C", "B"]  # reranker reversed → top-2
    assert out[0].similarity == 0.7  # original chunk preserved (not the rerank score)


@pytest.mark.asyncio
async def test_reranking_empty_query_and_empty_pool():
    rr = RerankingRetriever(base=_FakeBase([_chunk("A", 1.0)]), reranker=_ReverseReranker())
    assert await rr.retrieve("  ", namespace="n") == []
    rr2 = RerankingRetriever(base=_FakeBase([]), reranker=_ReverseReranker())
    assert await rr2.retrieve("q", namespace="n") == []


# --- rerank MCP tool ----------------------------------------------------------

mcp_server = pytest.importorskip("fi_core.rag.mcp_server")


@pytest.fixture(autouse=True)
def _reset_reranker():
    mcp_server.set_reranker(None)
    yield
    mcp_server.set_reranker(None)


@pytest.mark.asyncio
async def test_rerank_tool_uses_injected_reranker():
    mcp_server.set_reranker(_KeepReranker())
    r = await mcp_server.rerank("q", ["nope", "KEEP this one", "no"], top_k=2)
    assert r["hits"][0]["text"] == "KEEP this one"  # the KEEP doc ranked first
    assert len(r["hits"]) == 2


@pytest.mark.asyncio
async def test_rerank_tool_empty_documents():
    assert await mcp_server.rerank("q", [], top_k=5) == {"hits": []}


@pytest.mark.asyncio
async def test_rerank_tool_reranker_error_is_graceful():
    @dataclass
    class _BoomReranker:
        async def rerank(self, query, documents):  # noqa: ANN001
            raise RuntimeError("model not installed")

    mcp_server.set_reranker(_BoomReranker())
    r = await mcp_server.rerank("q", ["a", "b"])
    assert r["hits"] == [] and "not available" in r["error"]
