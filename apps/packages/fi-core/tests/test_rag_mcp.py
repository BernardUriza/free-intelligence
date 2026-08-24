"""Tests for fi_core.rag.mcp_server.

Direct invocation of the tool functions (bypassing the MCP stdio transport).
These tests pin the contract that any MCP client (Claude Code, Cursor, etc.)
sees over the wire.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from fi_core.rag import Chunk, RetrievedChunk

# Skip the whole module if the MCP SDK is not installed.
mcp_server = pytest.importorskip("fi_core.rag.mcp_server")


# ============================================================
# chunk_document
# ============================================================


@pytest.mark.asyncio
async def test_chunk_document_splits_text():
    r = await mcp_server.chunk_document("Hola mundo. " * 300, strategy="sentence_aware")
    assert r["strategy"] == "sentence_aware"
    assert r["count"] >= 1
    assert isinstance(r["chunks"], list)
    assert all(isinstance(c, str) for c in r["chunks"])


@pytest.mark.asyncio
async def test_chunk_document_unknown_strategy_returns_error():
    r = await mcp_server.chunk_document("x", strategy="bogus")
    assert "error" in r
    assert "paragraph_aware" in r["valid_strategies"]


# ============================================================
# estimate_tokens
# ============================================================


@pytest.mark.asyncio
async def test_estimate_tokens_spanish_heuristic():
    r = await mcp_server.estimate_tokens("uno dos tres cuatro")
    assert r["words"] == 4
    assert r["tokens"] == int(4 * 1.3)


# ============================================================
# lexical_search — accent-folded, model-less
# ============================================================


@pytest.mark.asyncio
async def test_lexical_search_accent_folded_match():
    # Query has no tildes (how a user types); corpus is correctly accented.
    corpus = ["El omnívoro y la carne", "Cómo cambiar una llanta"]
    r = await mcp_server.lexical_search("omnivoro carne", corpus, top_k=2)
    assert r["hits"]
    assert r["hits"][0]["text"] == "El omnívoro y la carne"
    assert r["hits"][0]["score"] > 0


@pytest.mark.asyncio
async def test_lexical_search_empty_corpus_returns_no_hits():
    r = await mcp_server.lexical_search("algo", [], top_k=2)
    assert r["hits"] == []


# ============================================================
# semantic_search — cosine over caller-supplied vectors
# ============================================================


@pytest.mark.asyncio
async def test_semantic_search_ranks_by_cosine():
    r = await mcp_server.semantic_search(
        [1.0, 0.0], ["a", "b"], [[1.0, 0.0], [0.0, 1.0]], top_k=2, min_score=0.0
    )
    assert [h["text"] for h in r["hits"]] == ["a", "b"]
    assert r["hits"][0]["score"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_semantic_search_length_mismatch_returns_error():
    r = await mcp_server.semantic_search([1.0], ["a", "b"], [[1.0]])
    assert "error" in r
    assert r["n_texts"] == 2
    assert r["n_vectors"] == 1


# ============================================================
# cosine_similarity
# ============================================================


@pytest.mark.asyncio
async def test_cosine_similarity_identical_vectors():
    r = await mcp_server.cosine_similarity([1.0, 2.0], [1.0, 2.0])
    assert r["similarity"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_cosine_similarity_length_mismatch_returns_error():
    r = await mcp_server.cosine_similarity([1.0], [1.0, 2.0])
    assert "error" in r


# ============================================================
# MCP server instance
# ============================================================


def test_mcp_server_instance_exists():
    """Validate the FastMCP instance is constructed at module load."""
    assert mcp_server.mcp is not None
    assert mcp_server.mcp.name == "fi-core-rag"


# ============================================================
# search_documents (persistent doc-RAG)
# ============================================================


@dataclass
class _FakeRetriever:
    """Stands in for a configured StoreBackedRetriever (no model/DB)."""

    captured: dict | None = None

    async def retrieve(self, query, *, namespace, top_k=5, min_similarity=None, filters=None):  # noqa: ANN001
        self.captured = {"query": query, "namespace": namespace, "top_k": top_k, "min_similarity": min_similarity}
        return [RetrievedChunk(chunk=Chunk(text="recalled", source_type="document", source_ref="doc1"), similarity=0.88)]


@pytest.fixture(autouse=True)
def _reset_retriever():
    """Keep the module-global retriever clean between tests."""
    mcp_server.set_retriever(None)
    yield
    mcp_server.set_retriever(None)


@pytest.mark.asyncio
async def test_search_documents_uses_injected_retriever():
    fake = _FakeRetriever()
    mcp_server.set_retriever(fake)
    r = await mcp_server.search_documents("¿síntomas?", namespace="patient-1", top_k=3)
    assert fake.captured == {"query": "¿síntomas?", "namespace": "patient-1", "top_k": 3, "min_similarity": None}
    assert r["hits"] == [
        {"text": "recalled", "similarity": 0.88, "source_type": "document", "source_ref": "doc1"}
    ]


@pytest.mark.asyncio
async def test_search_documents_unconfigured_returns_error(monkeypatch):
    # No retriever injected + env unset → graceful error dict, not a crash.
    # `FI_RAG_BACKEND` is the name every other consumer sets; `FI_RAG_STORE` was
    # this module's private spelling and is why a correctly configured box left
    # this server unconfigured. Both cleared, so the test cannot pass merely
    # because it is unsetting a variable nobody sets.
    for var in ("FI_RAG_EMBEDDER", "FI_RAG_STORE", "FI_RAG_BACKEND", "FI_RAG_STORE_PATH"):
        monkeypatch.delenv(var, raising=False)
    r = await mcp_server.search_documents("q", namespace="n")
    assert r["hits"] == []
    assert "not configured" in r["error"]


@pytest.mark.asyncio
async def test_the_env_every_other_consumer_sets_actually_configures_this_server(monkeypatch, tmp_path):
    """This module read `FI_RAG_STORE` and `FI_RAG_HDF5_PATH` — names that appear
    NOWHERE else in the repo. `store_service`, fi-runner's capability and both
    deploy docs all set `FI_RAG_BACKEND` / `FI_RAG_STORE_PATH`, so a correctly
    configured box left this server unconfigured: `search_documents` answered
    `{"error": "...not configured", "hits": []}` and the agent reported "nothing
    found" — a retrieval failure wearing the face of an empty corpus."""
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "r.h5"))
    monkeypatch.setenv("FI_RAG_EMBEDDER", "hashing")
    monkeypatch.setenv("FI_RAG_EMBED_DIM", "64")
    retriever = mcp_server._build_retriever_from_env()
    assert retriever is not None


@pytest.mark.asyncio
async def test_hashing_is_accepted_here_as_it_is_everywhere_else(monkeypatch, tmp_path):
    """The private copy had no `hashing` branch at all, though hashing is the
    documented default embedder — so the one value the docs tell you to use was
    the one value this server refused."""
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "r.h5"))
    monkeypatch.setenv("FI_RAG_EMBEDDER", "hashing")
    assert mcp_server._build_retriever_from_env() is not None


@pytest.mark.asyncio
async def test_the_embedding_dim_default_matches_the_store_it_writes_to(monkeypatch, tmp_path):
    """This module defaulted FI_RAG_EMBED_DIM to 1536 while `store_service`
    defaults to 256, so a corpus written at 256 would be read back through a
    1536-dim store. Asserted on the embedder this server actually builds, not on
    the text of the file — one builder now, so one default."""
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "r.h5"))
    monkeypatch.setenv("FI_RAG_EMBEDDER", "hashing")
    monkeypatch.delenv("FI_RAG_EMBED_DIM", raising=False)

    from fi_core.rag.store_service import build_embedder_from_env

    mine = mcp_server._build_retriever_from_env().embedder
    theirs = build_embedder_from_env()
    assert len(await mine.embed("x")) == len(await theirs.embed("x")), \
        "a corpus written by one and read by the other must agree on dimension"
