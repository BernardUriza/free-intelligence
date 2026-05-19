"""Tests for fi_core.stores.hdf5.HDF5ChunkStore.

Real h5py I/O against tmp_path-managed files — no mocks. These tests pin
the contract that AURITY (medical RAG), Insult Tier 2 (mental-science
layer), and Robo-Poet (training corpus reader) all rely on.

Coverage: ChunkStore (add/query) + DocumentChunkStore (CRUD + bulk +
reindex) + cascading deletes + status auto-promotion + idempotent
save_chunks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fi_core.rag import (
    Chunk,
    ChunkWithEmbedding,
    DocumentMetadata,
)
from fi_core.stores.hdf5 import HDF5ChunkStore


def _chunk(text: str, source_ref: str, source_type: str = "test") -> Chunk:
    return Chunk(
        text=text,
        source_type=source_type,
        source_ref=source_ref,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _ce(text: str, source_ref: str, embedding: list[float]) -> ChunkWithEmbedding:
    return ChunkWithEmbedding(chunk=_chunk(text, source_ref), embedding=embedding)


@pytest.fixture
def store(tmp_path):
    return HDF5ChunkStore(tmp_path / "test_store.h5")


# ============================================================
# Document CRUD
# ============================================================


@pytest.mark.asyncio
async def test_create_and_get_document(store):
    await store.create_document(
        namespace="ns1",
        document_id="d1",
        content="Hello world.",
        metadata=DocumentMetadata(status="pending", attributes={"clinic_id": "C1"}),
    )
    doc = await store.get_document(namespace="ns1", document_id="d1")
    assert doc is not None
    assert doc.document_id == "d1"
    assert doc.namespace == "ns1"
    assert doc.content == "Hello world."
    assert doc.metadata.status == "pending"
    assert doc.metadata.attributes == {"clinic_id": "C1"}
    assert doc.chunk_count == 0


@pytest.mark.asyncio
async def test_get_document_returns_none_when_missing(store):
    doc = await store.get_document(namespace="nope", document_id="d1")
    assert doc is None


@pytest.mark.asyncio
async def test_create_document_rejects_duplicates(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    with pytest.raises(ValueError, match="already exists"):
        await store.create_document(namespace="ns1", document_id="d1", content="B")


@pytest.mark.asyncio
async def test_create_document_synthesizes_created_at_when_none(store):
    await store.create_document(
        namespace="ns1",
        document_id="d1",
        content="A",
        metadata=DocumentMetadata(status="pending"),  # no created_at
    )
    doc = await store.get_document(namespace="ns1", document_id="d1")
    assert doc.metadata.created_at is not None


@pytest.mark.asyncio
async def test_update_document_content(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    updated = await store.update_document(
        namespace="ns1", document_id="d1", content="A revised"
    )
    assert updated is True
    doc = await store.get_document(namespace="ns1", document_id="d1")
    assert doc.content == "A revised"


@pytest.mark.asyncio
async def test_update_document_returns_false_when_missing(store):
    updated = await store.update_document(
        namespace="ns1", document_id="nope", content="X"
    )
    assert updated is False


@pytest.mark.asyncio
async def test_update_document_metadata(store):
    await store.create_document(
        namespace="ns1",
        document_id="d1",
        content="A",
        metadata=DocumentMetadata(status="pending"),
    )
    new_meta = DocumentMetadata(status="archived", attributes={"reason": "obsolete"})
    await store.update_document(namespace="ns1", document_id="d1", metadata=new_meta)
    doc = await store.get_document(namespace="ns1", document_id="d1")
    assert doc.metadata.status == "archived"
    assert doc.metadata.attributes == {"reason": "obsolete"}


@pytest.mark.asyncio
async def test_delete_document(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    deleted = await store.delete_document(namespace="ns1", document_id="d1")
    assert deleted is True
    assert await store.get_document(namespace="ns1", document_id="d1") is None


@pytest.mark.asyncio
async def test_delete_document_returns_false_when_missing(store):
    deleted = await store.delete_document(namespace="ns1", document_id="nope")
    assert deleted is False


# ============================================================
# list_documents
# ============================================================


@pytest.mark.asyncio
async def test_list_documents_empty_namespace_returns_empty(store):
    docs = await store.list_documents(namespace="empty")
    assert docs == []


@pytest.mark.asyncio
async def test_list_documents_returns_all_when_no_filter(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    await store.create_document(namespace="ns1", document_id="d2", content="B")
    await store.create_document(namespace="ns1", document_id="d3", content="C")
    docs = await store.list_documents(namespace="ns1")
    assert len(docs) == 3
    assert {d.document_id for d in docs} == {"d1", "d2", "d3"}


@pytest.mark.asyncio
async def test_list_documents_filters_by_status(store):
    await store.create_document(
        namespace="ns1",
        document_id="d1",
        content="A",
        metadata=DocumentMetadata(status="pending"),
    )
    await store.create_document(
        namespace="ns1",
        document_id="d2",
        content="B",
        metadata=DocumentMetadata(status="indexed"),
    )
    pending = await store.list_documents(namespace="ns1", status="pending")
    assert len(pending) == 1
    assert pending[0].document_id == "d1"


@pytest.mark.asyncio
async def test_list_documents_respects_limit(store):
    for i in range(5):
        await store.create_document(namespace="ns1", document_id=f"d{i}", content="X")
    docs = await store.list_documents(namespace="ns1", limit=3)
    assert len(docs) == 3


# ============================================================
# save_chunks + get_chunks_by_document
# ============================================================


@pytest.mark.asyncio
async def test_save_chunks_persists_and_returns_count(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    saved = await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[
            _ce("Chunk 1", "d1#0", [1.0, 0.0]),
            _ce("Chunk 2", "d1#1", [0.0, 1.0]),
        ],
    )
    assert saved == 2
    chunks = await store.get_chunks_by_document(namespace="ns1", document_id="d1")
    assert len(chunks) == 2
    assert {c.text for c in chunks} == {"Chunk 1", "Chunk 2"}


@pytest.mark.asyncio
async def test_save_chunks_raises_when_document_missing(store):
    with pytest.raises(ValueError, match="does not exist"):
        await store.save_chunks(
            namespace="ns1",
            document_id="nope",
            chunks=[_ce("X", "n#0", [1.0])],
        )


@pytest.mark.asyncio
async def test_save_chunks_is_idempotent_on_source_ref_text(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    first = await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("Same chunk", "d1#0", [1.0, 0.0])],
    )
    second = await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("Same chunk", "d1#0", [1.0, 0.0])],
    )
    assert first == 1
    assert second == 0  # second insert is a no-op
    chunks = await store.get_chunks_by_document(namespace="ns1", document_id="d1")
    assert len(chunks) == 1


@pytest.mark.asyncio
async def test_save_chunks_auto_promotes_pending_to_indexed(store):
    await store.create_document(
        namespace="ns1",
        document_id="d1",
        content="A",
        metadata=DocumentMetadata(status="pending"),
    )
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("X", "d1#0", [1.0, 0.0])],
    )
    doc = await store.get_document(namespace="ns1", document_id="d1")
    assert doc.metadata.status == "indexed"
    assert doc.metadata.indexed_at is not None


@pytest.mark.asyncio
async def test_save_chunks_does_not_demote_non_pending_status(store):
    """If a doc is already 'archived' or custom status, don't auto-promote to 'indexed'."""
    await store.create_document(
        namespace="ns1",
        document_id="d1",
        content="A",
        metadata=DocumentMetadata(status="custom_state"),
    )
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("X", "d1#0", [1.0, 0.0])],
    )
    doc = await store.get_document(namespace="ns1", document_id="d1")
    assert doc.metadata.status == "custom_state"


@pytest.mark.asyncio
async def test_get_chunks_by_document_returns_empty_for_chunkless_doc(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    chunks = await store.get_chunks_by_document(namespace="ns1", document_id="d1")
    assert chunks == []


@pytest.mark.asyncio
async def test_get_chunks_by_document_returns_empty_for_missing_doc(store):
    chunks = await store.get_chunks_by_document(namespace="ns1", document_id="nope")
    assert chunks == []


# ============================================================
# delete_chunks_by_document
# ============================================================


@pytest.mark.asyncio
async def test_delete_chunks_by_document_clears_chunks_keeps_doc(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("X", "d1#0", [1.0, 0.0]), _ce("Y", "d1#1", [0.0, 1.0])],
    )
    deleted = await store.delete_chunks_by_document(namespace="ns1", document_id="d1")
    assert deleted == 2
    # Document still exists
    doc = await store.get_document(namespace="ns1", document_id="d1")
    assert doc is not None
    assert doc.chunk_count == 0
    # Chunks gone
    assert await store.get_chunks_by_document(namespace="ns1", document_id="d1") == []


@pytest.mark.asyncio
async def test_delete_document_cascades_to_chunks(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("X", "d1#0", [1.0, 0.0])],
    )
    await store.delete_document(namespace="ns1", document_id="d1")
    # Query namespace — should have no chunks left
    results = await store.query(
        namespace="ns1", query_embedding=[1.0, 0.0], top_k=5
    )
    assert results == []


# ============================================================
# query (cosine similarity)
# ============================================================


@pytest.mark.asyncio
async def test_query_returns_top_k_by_cosine_similarity(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[
            _ce("Exact match", "d1#0", [1.0, 0.0, 0.0]),
            _ce("Orthogonal",  "d1#1", [0.0, 1.0, 0.0]),
            _ce("Mid match",   "d1#2", [0.7, 0.7, 0.0]),
        ],
    )
    results = await store.query(
        namespace="ns1", query_embedding=[1.0, 0.0, 0.0], top_k=2
    )
    assert len(results) == 2
    # First result should be exact match with similarity ~1.0
    assert results[0].chunk.text == "Exact match"
    assert results[0].similarity == pytest.approx(1.0, abs=1e-5)
    # Second should be mid-match
    assert results[1].chunk.text == "Mid match"
    assert results[1].similarity > 0.5


@pytest.mark.asyncio
async def test_query_empty_namespace_returns_empty(store):
    results = await store.query(
        namespace="empty", query_embedding=[1.0, 0.0], top_k=5
    )
    assert results == []


@pytest.mark.asyncio
async def test_query_isolates_namespaces(store):
    await store.create_document(namespace="ns_a", document_id="d1", content="A")
    await store.save_chunks(
        namespace="ns_a",
        document_id="d1",
        chunks=[_ce("In NS A", "d1#0", [1.0, 0.0])],
    )
    await store.create_document(namespace="ns_b", document_id="d1", content="B")
    await store.save_chunks(
        namespace="ns_b",
        document_id="d1",
        chunks=[_ce("In NS B", "d1#0", [1.0, 0.0])],
    )
    results_a = await store.query(
        namespace="ns_a", query_embedding=[1.0, 0.0], top_k=5
    )
    assert len(results_a) == 1
    assert results_a[0].chunk.text == "In NS A"


@pytest.mark.asyncio
async def test_query_handles_zero_query_vector(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("X", "d1#0", [1.0, 0.0])],
    )
    results = await store.query(namespace="ns1", query_embedding=[0.0, 0.0], top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_query_top_k_larger_than_namespace_size(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("Only one", "d1#0", [1.0, 0.0])],
    )
    results = await store.query(namespace="ns1", query_embedding=[1.0, 0.0], top_k=10)
    assert len(results) == 1


# ============================================================
# ChunkStore.add (auto-document mode)
# ============================================================


@pytest.mark.asyncio
async def test_add_creates_document_and_chunk(store):
    await store.add(
        namespace="ns1",
        chunk=_chunk("Solo chunk", "src/file.txt"),
        embedding=[1.0, 0.0, 0.0],
    )
    docs = await store.list_documents(namespace="ns1")
    assert len(docs) == 1
    # Document auto-synthesized from chunk source_ref
    assert docs[0].document_id.startswith("_auto_")


@pytest.mark.asyncio
async def test_add_query_roundtrip(store):
    await store.add(
        namespace="ns1",
        chunk=_chunk("Findable", "src/a.txt"),
        embedding=[1.0, 0.0, 0.0],
    )
    await store.add(
        namespace="ns1",
        chunk=_chunk("Other", "src/b.txt"),
        embedding=[0.0, 1.0, 0.0],
    )
    results = await store.query(
        namespace="ns1", query_embedding=[1.0, 0.0, 0.0], top_k=1
    )
    assert results[0].chunk.text == "Findable"


# ============================================================
# reindex_document + persistence across instances
# ============================================================


@pytest.mark.asyncio
async def test_index_rebuilt_when_store_reopened(tmp_path):
    """Pinned contract: chunks persisted by one instance are queryable by a fresh one."""
    path = tmp_path / "persist.h5"
    store1 = HDF5ChunkStore(path)
    await store1.create_document(namespace="ns1", document_id="d1", content="A")
    await store1.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("Persisted", "d1#0", [1.0, 0.0])],
    )

    # Fresh instance — must rebuild index from disk on construction.
    store2 = HDF5ChunkStore(path)
    results = await store2.query(
        namespace="ns1", query_embedding=[1.0, 0.0], top_k=1
    )
    assert len(results) == 1
    assert results[0].chunk.text == "Persisted"


@pytest.mark.asyncio
async def test_reindex_document_returns_false_for_missing(store):
    result = await store.reindex_document(namespace="ns1", document_id="nope")
    assert result is False


@pytest.mark.asyncio
async def test_reindex_document_returns_true_for_existing(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("X", "d1#0", [1.0, 0.0])],
    )
    result = await store.reindex_document(namespace="ns1", document_id="d1")
    assert result is True
    # Index still works post-reindex
    results = await store.query(
        namespace="ns1", query_embedding=[1.0, 0.0], top_k=1
    )
    assert len(results) == 1


# ============================================================
# Empty + boundary cases
# ============================================================


@pytest.mark.asyncio
async def test_save_chunks_empty_list_returns_zero(store):
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    saved = await store.save_chunks(
        namespace="ns1", document_id="d1", chunks=[]
    )
    assert saved == 0


@pytest.mark.asyncio
async def test_document_attributes_survive_round_trip(store):
    attrs = {
        "clinic_id": "C1",
        "encounter_id": 123,
        "tags": ["urgent", "followup"],
    }
    await store.create_document(
        namespace="ns1",
        document_id="d1",
        content="A",
        metadata=DocumentMetadata(status="indexed", attributes=attrs),
    )
    doc = await store.get_document(namespace="ns1", document_id="d1")
    assert doc.metadata.attributes == attrs
