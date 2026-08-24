"""Tests for the STATEFUL RAG store MCP server (real HDF5 + zero-model hashing).

Round-trip (ingest → search), persistence across a simulated restart, isolation
by corpus_id, and list/delete. Direct tool invocation (no stdio transport).
"""

from __future__ import annotations

import asyncio

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


# --- P1: lifecycle (delete_corpus + stats) ------------------------------------


@pytest.mark.asyncio
async def test_stats_and_delete_corpus(configured):
    await store_mcp.ingest_document("c1", "d1", _DOC, **_CHUNK)
    await store_mcp.ingest_document("c1", "d2", "otro dolor diabetes del paciente grave", **_CHUNK)
    st = await store_mcp.stats("c1")
    assert st["n_docs"] == 2 and st["n_chunks"] >= 2 and st["bytes"] > 0  # the metering base
    res = await store_mcp.delete_corpus("c1")
    assert res["deleted_documents"] == 2
    assert await store_mcp.list_documents("c1") == {"documents": []}
    assert await store_mcp.stats("c1") == {"n_docs": 0, "n_chunks": 0, "bytes": 0}


# --- P1: HDF5 locking under concurrency ---------------------------------------


@pytest.mark.asyncio
async def test_concurrent_ingests_do_not_corrupt(configured):
    # 8 concurrent ingests (distinct docs) to one H5 file. The thread/flock lock
    # serializes file access; without it h5py concurrent writers corrupt the file.
    docs = [f"doc-{i}" for i in range(8)]
    await asyncio.gather(
        *[store_mcp.ingest_document("c1", d, f"contenido {i} dolor diabetes sueno animo", **_CHUNK)
          for i, d in enumerate(docs)]
    )
    listed = await store_mcp.list_documents("c1")
    assert sorted(d["doc_id"] for d in listed["documents"]) == sorted(docs)  # all present, file intact
    assert (await store_mcp.search_documents("c1", "dolor", top_k=20))["hits"]  # still queryable


# --- P2: per-tenant quotas ----------------------------------------------------


@pytest.mark.asyncio
async def test_quota_max_docs_rejects_over_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "q.h5"))
    monkeypatch.setenv("FI_RAG_EMBEDDER", "hashing")
    monkeypatch.setenv("FI_RAG_EMBED_DIM", "64")
    monkeypatch.setenv("FI_RAG_MAX_DOCS", "1")  # one doc per corpus
    store_mcp._reset()
    try:
        assert (await store_mcp.ingest_document("c1", "d1", _DOC, **_CHUNK))["chunks"] >= 1
        over = await store_mcp.ingest_document("c1", "d2", _DOC, **_CHUNK)
        assert over.get("quota_exceeded") is True and "error" in over  # clear over-quota signal
        # re-ingesting d1 is a REPLACE (not a new doc) → allowed
        assert (await store_mcp.ingest_document("c1", "d1", _DOC, **_CHUNK))["chunks"] >= 1
        # a different corpus is unaffected (per-tenant)
        assert (await store_mcp.ingest_document("c2", "d1", _DOC, **_CHUNK))["chunks"] >= 1
    finally:
        store_mcp._reset()


# --- a re-ingest must not destroy what it cannot replace --------------------
# `ingest` deleted the old chunks and only then discovered the new text chunked
# to nothing: the working version was gone, the call returned 0 with no error,
# chunk_count went to zero, status reverted to "pending", searches came back
# empty and the byte count — the BILLING base — read zero. og118 collided with
# this and handled the 0 at its call site with a 422 telling the user to
# re-upload, after the copy they had was already destroyed.


@pytest.mark.asyncio
async def test_a_reingest_that_indexes_to_nothing_leaves_the_old_version_intact(configured):
    await store_mcp.ingest_document("c1", "d1", _DOC, **_CHUNK)
    before = await store_mcp.search_documents("c1", "dolor toracico", top_k=3)
    assert before["hits"], "precondition: the document is searchable"

    out = await store_mcp.ingest_document("c1", "d1", "ok", chunk_size=400,
                                          overlap=50, min_chunk_size=100)
    assert out.get("error"), "an ingest that stores nothing must not report success"

    after = await store_mcp.search_documents("c1", "dolor toracico", top_k=3)
    assert after["hits"], "the version that worked survived the failed re-ingest"
    docs = await store_mcp.list_documents("c1")
    assert any(d["doc_id"] == "d1" and d["chunk_count"] > 0 for d in docs["documents"])


@pytest.mark.asyncio
async def test_a_reingest_without_metadata_keeps_the_documents_attributes(configured):
    """`metadata=None` means "leave them alone". It used to mean "wipe them",
    which removed a document from every filtered query its tenant ran while
    leaving it visible to unfiltered ones — a routine content correction
    silently dropping a document out of its own clinic's view."""
    await store_mcp.ingest_document("c1", "d1", _DOC, metadata={"clinic_id": "x"}, **_CHUNK)
    hits = await store_mcp.search_documents("c1", "dolor toracico", top_k=3,
                                            filters={"clinic_id": "x"})
    assert hits["hits"], "precondition: the filter finds it"

    await store_mcp.ingest_document("c1", "d1", _DOC + " Nota corregida.", **_CHUNK)
    still = await store_mcp.search_documents("c1", "dolor toracico", top_k=3,
                                             filters={"clinic_id": "x"})
    assert still["hits"], "the correction must not remove it from its tenant's view"


@pytest.mark.asyncio
async def test_metadata_when_passed_is_still_authoritative(configured):
    """Preserving on None must not make attributes unchangeable."""
    await store_mcp.ingest_document("c1", "d1", _DOC, metadata={"clinic_id": "x"}, **_CHUNK)
    await store_mcp.ingest_document("c1", "d1", _DOC, metadata={"clinic_id": "y"}, **_CHUNK)
    assert not (await store_mcp.search_documents("c1", "dolor", top_k=3,
                                                 filters={"clinic_id": "x"}))["hits"]
    assert (await store_mcp.search_documents("c1", "dolor toracico", top_k=3,
                                             filters={"clinic_id": "y"}))["hits"]
