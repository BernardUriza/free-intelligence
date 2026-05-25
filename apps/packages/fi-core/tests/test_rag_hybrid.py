"""Tests for hybrid retrieval — RRF fusion of dense + lexical.

The point of hybrid: an exact-keyword chunk the DENSE arm ranked low (but still
in the candidate pool) bubbles to the top once the lexical arm votes for it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from fi_core.rag import Chunk, HybridRetriever, RetrievedChunk, reciprocal_rank_fusion


@dataclass
class _FakeDense:
    """Stands in for a StoreBackedRetriever — returns a fixed dense-ranked pool."""

    pool: list[RetrievedChunk]

    async def retrieve(self, query, *, namespace, top_k=5, min_similarity=None):  # noqa: ANN001
        return self.pool[:top_k]


def _chunk(text: str, sim: float) -> RetrievedChunk:
    return RetrievedChunk(chunk=Chunk(text=text, source_type="document", source_ref="d"), similarity=sim)


# --- reciprocal_rank_fusion (generic primitive) -------------------------------


def test_rrf_item_in_both_arms_outranks_single_arm():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "x"]])
    assert max(fused, key=lambda key: fused[key]) == "b"  # in both arms → top
    assert fused["b"] > fused["a"] > fused["c"]


def test_rrf_empty_input_is_empty():
    assert reciprocal_rank_fusion([]) == {}


# --- HybridRetriever ----------------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_bubbles_exact_keyword_chunk_above_higher_dense():
    # Dense ranks the keyword-less chunk #1 (sim 0.9) and the keyword chunk #2
    # (sim 0.5). Pure dense → top-1 is the clima chunk. Hybrid must flip it.
    pool = [
        _chunk("el clima templado y agradable de la tarde", 0.9),  # no query keyword
        _chunk("presion arterial elevada del paciente", 0.5),  # exact keyword
    ]
    hybrid = HybridRetriever(dense=_FakeDense(pool))  # default LexicalRetriever
    hits = await hybrid.retrieve("presion arterial", namespace="n", top_k=2)
    assert "presion arterial" in hits[0].chunk.text  # keyword chunk bubbled to #1
    assert len(hits) == 2


@pytest.mark.asyncio
async def test_hybrid_empty_query_returns_empty():
    hybrid = HybridRetriever(dense=_FakeDense([_chunk("algo", 1.0)]))
    assert await hybrid.retrieve("  ", namespace="n") == []
