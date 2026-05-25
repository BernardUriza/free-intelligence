"""Boundary-clean programmatic RAG store client.

THE P0 acceptance: a process that imports ONLY fi_runner (never fi_core) can
ingest(corpus_id, doc_id, text) then search(corpus_id, query) — round-trip,
persistent, isolated by corpus_id. This module does not `import fi_core`.
"""

from __future__ import annotations

import pytest

pytest.importorskip("h5py")  # default hdf5 backend
from fi_runner.rag_store import RagStoreClient, read_text_file  # noqa: E402 - after importorskip

_DOC = (
    "El paciente refiere dolor toracico opresivo e intenso desde hace dos horas.\n\n"
    "Tiene antecedentes de diabetes e hipertension cronica mal controladas.\n\n"
    "Reporta buen sueno y animo estable sin ideas de riesgo."
)
_CHUNK = {"chunk_size": 12, "overlap": 0, "min_chunk_size": 2}  # chunker counts TOKENS


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "rag.h5"))
    monkeypatch.setenv("FI_RAG_EMBEDDER", "hashing")
    monkeypatch.setenv("FI_RAG_EMBED_DIM", "64")
    return tmp_path / "rag.h5"


@pytest.mark.asyncio
async def test_ingest_then_search_roundtrip(env):
    rag = RagStoreClient()
    n = await rag.ingest("t1", "d1", _DOC, **_CHUNK)
    assert n >= 1
    hits = await rag.search("t1", "dolor toracico", top_k=3)
    assert hits and isinstance(hits[0], dict)  # plain dicts, no fi-core types leak
    assert any("dolor" in h["text"] for h in hits)
    assert hits[0]["doc_id"] == "d1"


@pytest.mark.asyncio
async def test_persists_across_a_fresh_client(env):
    await RagStoreClient().ingest("t1", "d1", _DOC, **_CHUNK)
    # a brand-new client (a recycled process) reads the on-disk H5 — state survives
    hits = await RagStoreClient().search("t1", "diabetes hipertension", top_k=3)
    assert hits, "state did not persist to disk"


@pytest.mark.asyncio
async def test_isolation_by_corpus(env):
    rag = RagStoreClient()
    await rag.ingest("tA", "dA", "dolor toracico agudo grave del paciente", **_CHUNK)
    await rag.ingest("tB", "dB", "clima templado agradable de la tarde", **_CHUNK)
    a = await rag.search("tA", "dolor", top_k=5)
    assert a and all(h["doc_id"] == "dA" for h in a)  # tenant A only
    assert await rag.search("tEmpty", "dolor", top_k=5) == []  # no cross-tenant leak


@pytest.mark.asyncio
async def test_list_and_delete(env):
    rag = RagStoreClient()
    await rag.ingest("t1", "d1", _DOC, metadata={"source": "upload"}, **_CHUNK)
    docs = await rag.list_documents("t1")
    assert [d["doc_id"] for d in docs] == ["d1"]
    assert docs[0]["attributes"] == {"source": "upload"}
    assert await rag.delete_document("t1", "d1") is True
    assert await rag.list_documents("t1") == []


@pytest.mark.asyncio
async def test_ingest_text_file(env, tmp_path):
    f = tmp_path / "notes.md"
    f.write_text("dolor toracico y diabetes del paciente cronico grave", encoding="utf-8")
    rag = RagStoreClient()
    n = await rag.ingest_text_file("t1", f, **_CHUNK)
    assert n >= 1
    hits = await rag.search("t1", "dolor", top_k=3)
    assert hits and hits[0]["doc_id"] == "notes.md"  # doc_id defaults to filename


def test_read_text_file(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("hola mundo", encoding="utf-8")
    assert read_text_file(p) == "hola mundo"
