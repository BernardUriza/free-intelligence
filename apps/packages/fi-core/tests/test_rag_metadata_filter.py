"""Tests for metadata filtering — query restricted by parent-document attributes.

HDF5 is exercised for real (h5py is a dev dep); the retriever + MCP layers are
tested for forwarding the ``filters`` argument. The pgvector ``@>`` path is in
test_rag_pgvector_smoke.py (needs a real DB).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from fi_core.rag import (
    Chunk,
    ChunkWithEmbedding,
    DocumentMetadata,
    RetrievedChunk,
    StoreBackedRetriever,
)


# --- HDF5: real filtering by document attributes ------------------------------


@pytest.mark.asyncio
async def test_hdf5_query_filters_by_document_attributes(tmp_path):
    h5py = pytest.importorskip("h5py")  # noqa: F841 - skip if the stores-hdf5 extra is absent
    from fi_core.stores.hdf5 import HDF5ChunkStore

    store = HDF5ChunkStore(tmp_path / "rag.h5")
    for doc_id, clinic in (("dA", "A"), ("dB", "B")):
        await store.create_document(
            namespace="ns", document_id=doc_id, content=doc_id,
            metadata=DocumentMetadata(attributes={"clinic_id": clinic}),
        )
        await store.save_chunks(
            namespace="ns", document_id=doc_id,
            chunks=[ChunkWithEmbedding(Chunk(f"texto {clinic}", "document", doc_id), [1.0, 0.0, 0.0, 0.0])],
        )
    # identical embeddings → both equally similar; only the filter separates them.
    only_a = await store.query(namespace="ns", query_embedding=[1.0, 0.0, 0.0, 0.0], top_k=10, filters={"clinic_id": "A"})
    assert [h.chunk.source_ref for h in only_a] == ["dA"]
    both = await store.query(namespace="ns", query_embedding=[1.0, 0.0, 0.0, 0.0], top_k=10)
    assert {h.chunk.source_ref for h in both} == {"dA", "dB"}  # no filter → all
    none = await store.query(namespace="ns", query_embedding=[1.0, 0.0, 0.0, 0.0], top_k=10, filters={"clinic_id": "Z"})
    assert none == []  # no doc matches


# --- StoreBackedRetriever forwards filters to the store -----------------------


@dataclass
class _CaptureStore:
    captured: Any = "UNSET"

    async def add(self, **_kw) -> None:  # noqa: ANN003
        ...

    async def query(self, *, namespace, query_embedding, top_k, filters=None) -> list[RetrievedChunk]:  # noqa: ANN001
        self.captured = filters
        return []


@dataclass
class _FakeEmbedder:
    async def embed(self, text: str) -> list[float]:
        return [1.0, 0.0]


@pytest.mark.asyncio
async def test_store_backed_retriever_forwards_filters():
    store = _CaptureStore()
    r = StoreBackedRetriever(embedder=_FakeEmbedder(), store=store)
    await r.retrieve("q", namespace="n", filters={"clinic_id": "A"})
    assert store.captured == {"clinic_id": "A"}
    await r.retrieve("q", namespace="n")  # default → None
    assert store.captured is None


# --- MCP search_documents forwards filters -----------------------------------

mcp_server = pytest.importorskip("fi_core.rag.mcp_server")


@dataclass
class _CaptureRetriever:
    captured: Any = field(default="UNSET")

    async def retrieve(self, query, *, namespace, top_k=5, min_similarity=None, filters=None):  # noqa: ANN001
        self.captured = filters
        return []


@pytest.mark.asyncio
async def test_search_documents_tool_forwards_filters():
    cap = _CaptureRetriever()
    mcp_server.set_retriever(cap)
    try:
        await mcp_server.search_documents("q", namespace="n", filters={"clinic_id": "A"})
        assert cap.captured == {"clinic_id": "A"}
    finally:
        mcp_server.set_retriever(None)
