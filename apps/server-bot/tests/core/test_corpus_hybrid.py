"""The fused shortlist: words recover what the cosine missed, and the index sees an ingest."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from persona_core.corpus import lexical, references


def _row(row_id: int, text: str) -> dict:
    return {
        "id": row_id,
        "source_type": "manual",
        "source_ref": f"x:{row_id}",
        "chunk_text": text,
        "created_at": datetime(2026, 11, 24, tzinfo=UTC),
    }


class _Conn:
    """Answers the three queries of a search; `rows` is the namespace, best cosine first."""

    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.full_reads = 0

    async def fetchrow(self, sql, *args):
        return {"n": len(self.rows), "last": max((r["id"] for r in self.rows), default=None)}

    async def fetch(self, sql, *args):
        if "LIMIT" in sql:
            return [{**r, "similarity": 0.9 - i / 100} for i, r in enumerate(self.rows)][: args[2]]
        self.full_reads += 1
        return self.rows

    async def close(self):
        pass


@pytest.fixture(autouse=True)
def _no_cache():
    lexical._cache.clear()
    yield
    lexical._cache.clear()


async def _search(conn: _Conn, query: str, *, top_k: int = 2, fusion_pool: int = 3) -> list[dict]:
    with (
        patch.object(references, "embed_query", new=AsyncMock(return_value=[0.1] * 384)),
        patch.object(references, "connect", new=AsyncMock(return_value=conn)),
    ):
        return await references.query_corpus(query, namespace="ns", top_k=top_k, fusion_pool=fusion_pool)


ROWS = [_row(1, "quelite"), _row(2, "perejil"), _row(3, "menta"), _row(4, "cilantro, huele a cítrico")]


async def test_words_recover_a_chunk_the_cosine_left_out():
    assert 4 not in {h["id"] for h in await _search(_Conn(ROWS), "cilantro", top_k=2, fusion_pool=0)}
    hits = await _search(_Conn(ROWS), "cilantro", top_k=2)
    found = next(h for h in hits if h["id"] == 4)
    assert found["similarity"] is None


async def test_a_query_sharing_no_word_keeps_the_cosine_order():
    assert [h["id"] for h in await _search(_Conn(ROWS), "capital de Australia")] == [1, 2]


async def test_the_index_is_reused_until_the_namespace_changes():
    conn = _Conn(list(ROWS))
    await _search(conn, "cilantro")
    await _search(conn, "cilantro")
    assert conn.full_reads == 1
    conn.rows.append(_row(5, "epazote"))
    assert 5 in {h["id"] for h in await _search(conn, "epazote")}
    assert conn.full_reads == 2


async def test_a_lexical_only_passage_can_lead_the_block():
    hit = {"source_type": "m", "source_ref": "x:y", "chunk_text": "pasaje", "similarity": None}
    with (
        patch.object(references, "query_corpus", new=AsyncMock(return_value=[hit])),
        patch.object(references, "score_relevance", new=AsyncMock(return_value=[3.0])),
    ):
        block = await references.build_references_block("pregunta bastante larga", namespace="n", header="H")
    assert block == "H\n- [y] pasaje"
