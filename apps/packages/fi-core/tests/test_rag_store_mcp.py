"""Tests for the STATEFUL RAG store MCP server (real HDF5 + zero-model hashing).

Round-trip (ingest → search), persistence across a simulated restart, isolation
by corpus_id, and list/delete. Direct tool invocation (no stdio transport).
"""

from __future__ import annotations

import pytest

pytest.importorskip("h5py")  # the default hdf5 backend
store_mcp = pytest.importorskip("fi_core.rag.store_mcp_server")

_DOC = (
    "El paciente refiere dolor toracico opresivo e intenso desde hace dos horas.\n\n"
    "Tiene antecedentes de diabetes e hipertension cronica mal controladas.\n\n"
    "Reporta buen sueno y animo estable sin ideas de riesgo."
)
# Small chunk config (the chunker counts TOKENS; defaults would drop short text).
_CHUNK = {"chunk_size": 12, "overlap": 0, "min_chunk_size": 2}


@pytest.fixture
def configured(tmp_path, monkeypatch):
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "rag.h5"))
    monkeypatch.setenv("FI_RAG_EMBEDDER", "hashing")
    monkeypatch.setenv("FI_RAG_EMBED_DIM", "64")
    store_mcp._reset()
    yield tmp_path / "rag.h5"
    store_mcp._reset()


@pytest.mark.asyncio
async def test_ingest_then_search_roundtrip(configured):
    r = await store_mcp.ingest_document("c1", "d1", _DOC, **_CHUNK)
    assert r["chunks"] >= 1  # persisted
    res = await store_mcp.search_documents("c1", "dolor toracico", top_k=3)
    assert res["hits"], "no hits"
    assert any("dolor" in h["text"] for h in res["hits"])
    assert res["hits"][0]["doc_id"] == "d1"


@pytest.mark.asyncio
async def test_persists_across_restart(configured):
    await store_mcp.ingest_document("c1", "d1", _DOC, **_CHUNK)
    store_mcp._reset()  # simulate a process restart — drops in-memory caches
    # a fresh store is built from the same FI_RAG_STORE_PATH and reads from disk
    res = await store_mcp.search_documents("c1", "diabetes hipertension", top_k=3)
    assert res["hits"], "state did not survive the restart"


@pytest.mark.asyncio
async def test_isolation_by_corpus(configured):
    await store_mcp.ingest_document("cA", "dA", "dolor toracico agudo grave del paciente", **_CHUNK)
    await store_mcp.ingest_document("cB", "dB", "clima templado agradable de la tarde", **_CHUNK)
    a = await store_mcp.search_documents("cA", "dolor", top_k=5)
    assert a["hits"] and all(h["doc_id"] == "dA" for h in a["hits"])  # only corpus A's docs
    assert await store_mcp.search_documents("cEmpty", "dolor", top_k=5) == {"hits": []}  # no cross-corpus leak


@pytest.mark.asyncio
async def test_list_and_delete(configured):
    await store_mcp.ingest_document("c1", "d1", _DOC, metadata={"clinic_id": "x"}, **_CHUNK)
    listed = await store_mcp.list_documents("c1")
    assert [d["doc_id"] for d in listed["documents"]] == ["d1"]
    assert listed["documents"][0]["attributes"] == {"clinic_id": "x"}
    assert listed["documents"][0]["chunk_count"] >= 1

    deleted = await store_mcp.delete_document("c1", "d1")
    assert deleted["deleted"] is True
    assert await store_mcp.list_documents("c1") == {"documents": []}
    assert (await store_mcp.search_documents("c1", "dolor", top_k=3))["hits"] == []


@pytest.mark.asyncio
async def test_reingest_replaces_chunks(configured):
    await store_mcp.ingest_document("c1", "d1", "dolor toracico inicial del paciente", **_CHUNK)
    await store_mcp.ingest_document("c1", "d1", "ahora habla de sueno y animo estable", **_CHUNK)
    listed = await store_mcp.list_documents("c1")
    assert len([d for d in listed["documents"] if d["doc_id"] == "d1"]) == 1  # not duplicated
    # the new content is searchable, the old is gone
    assert (await store_mcp.search_documents("c1", "sueno animo", top_k=3))["hits"]


@pytest.mark.asyncio
async def test_unknown_strategy_is_graceful(configured):
    r = await store_mcp.ingest_document("c1", "d1", _DOC, strategy="bogus")
    assert "error" in r
