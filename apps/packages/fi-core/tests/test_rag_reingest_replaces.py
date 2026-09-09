"""Re-ingesting a corrected document leaves no stale chunks — on BOTH faces.

The founding case (backlog b3-fi-core-retriever-reingest-stale): ingest a text,
correct it, ingest again under the same source_ref; a search must return only
the corrected chunk. Pinned against the real HDF5 store, through
StoreBackedRetriever.ingest (the retriever face) and RagStore.ingest (the
service face), because both now share one write path. Also pins that a
contextualizer wired through RagStore.from_components reaches the embedding
while the stored chunk stays verbatim, and that a plain add/query ChunkStore
still ingests through the fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from fi_core.embeddings.hashing import HashingEmbedder
from fi_core.rag import (
    Chunk,
    ChunkConfig,
    ChunkingStrategy,
    DocumentMetadata,
    RagStore,
    RetrievedChunk,
    StoreBackedRetriever,
)
from fi_core.stores.hdf5 import HDF5ChunkStore

LUNES = "La reunion es el lunes en la sala azul."
MARTES = "La reunion es el martes en la sala roja."
QUERY = "cuando es la reunion"
_CFG = ChunkConfig(chunk_size=50, overlap=0, min_chunk_size=3)


@dataclass
class _RecordingEmbedder:
    inner: HashingEmbedder = field(default_factory=lambda: HashingEmbedder(dim=64))
    embedded: list[str] = field(default_factory=list)

    async def embed(self, text: str) -> list[float]:
        self.embedded.append(text)
        return await self.inner.embed(text)


@dataclass
class _MarkerContextualizer:
    marker: str = "CTX-MARKER"

    async def contextualize(self, *, document: str, chunk: str) -> str:  # noqa: ARG002
        return self.marker


@dataclass
class _PlainChunkStore:
    added: list[tuple[str, Chunk, list[float]]] = field(default_factory=list)

    async def add(self, *, namespace: str, chunk: Chunk, embedding: list[float]) -> None:
        self.added.append((namespace, chunk, embedding))

    async def query(self, *, namespace: str, query_embedding: list[float], top_k: int = 5, filters=None):  # noqa: ANN001, ARG002
        return [RetrievedChunk(chunk=c, similarity=1.0) for _, c, _ in self.added[:top_k]]


@pytest.fixture
def store(tmp_path) -> HDF5ChunkStore:
    return HDF5ChunkStore(tmp_path / "reingest.h5")


# --- the founding case, retriever face ------------------------------------------


@pytest.mark.asyncio
async def test_retriever_reingest_replaces_stale_chunks(store):
    r = StoreBackedRetriever(embedder=HashingEmbedder(dim=64), store=store)
    assert await r.ingest(LUNES, namespace="n", source_ref="aviso.md", config=_CFG) == 1
    assert await r.ingest(MARTES, namespace="n", source_ref="aviso.md", config=_CFG) == 1

    hits = await r.retrieve(QUERY, namespace="n", top_k=5)
    assert [h.chunk.text for h in hits] == [MARTES]

    doc = await store.get_document(namespace="n", document_id="aviso.md")
    assert doc is not None
    assert doc.content == MARTES
    assert doc.chunk_count == 1
    assert [c.text for c in await store.get_chunks_by_document(namespace="n", document_id="aviso.md")] == [MARTES]


@pytest.mark.asyncio
async def test_retriever_reingest_keeps_existing_attributes(store):
    r = StoreBackedRetriever(embedder=HashingEmbedder(dim=64), store=store)
    await store.create_document(namespace="n", document_id="aviso.md", content="")
    await store.update_document(
        namespace="n", document_id="aviso.md", metadata=DocumentMetadata(attributes={"clinic_id": "c1"})
    )
    await r.ingest(MARTES, namespace="n", source_ref="aviso.md", config=_CFG)
    doc = await store.get_document(namespace="n", document_id="aviso.md")
    assert doc.metadata.attributes == {"clinic_id": "c1"}
    assert [h.chunk.text for h in await r.retrieve(QUERY, namespace="n", filters={"clinic_id": "c1"})] == [MARTES]


@pytest.mark.asyncio
async def test_retriever_blank_or_unchunkable_text_touches_nothing(store):
    r = StoreBackedRetriever(embedder=HashingEmbedder(dim=64), store=store)
    await r.ingest(MARTES, namespace="n", source_ref="aviso.md", config=_CFG)
    assert await r.ingest("   ", namespace="n", source_ref="aviso.md", config=_CFG) == 0
    assert await r.ingest("corto", namespace="n", source_ref="aviso.md") == 0
    doc = await store.get_document(namespace="n", document_id="aviso.md")
    assert doc.content == MARTES
    assert doc.chunk_count == 1


# --- the founding case, service face --------------------------------------------


@pytest.mark.asyncio
async def test_ragstore_reingest_replaces_stale_chunks(store):
    rag = RagStore.from_components(store=store, embedder=HashingEmbedder(dim=64))
    assert await rag.ingest("c", "aviso.md", LUNES, min_chunk_size=3) == 1
    assert await rag.ingest("c", "aviso.md", MARTES, min_chunk_size=3) == 1

    assert [h.chunk.text for h in await rag.search("c", QUERY)] == [MARTES]
    doc = await store.get_document(namespace="c", document_id="aviso.md")
    assert doc.content == MARTES
    assert doc.chunk_count == 1
    assert await rag.stats("c") == {"n_docs": 1, "n_chunks": 1, "bytes": len(MARTES.encode("utf-8"))}


@pytest.mark.asyncio
async def test_ragstore_reingest_metadata_semantics_survive_the_refactor(store):
    rag = RagStore.from_components(store=store, embedder=HashingEmbedder(dim=64))
    await rag.ingest("c", "aviso.md", LUNES, metadata={"clinic_id": "c1"}, min_chunk_size=3)
    await rag.ingest("c", "aviso.md", MARTES, min_chunk_size=3)
    assert (await store.get_document(namespace="c", document_id="aviso.md")).metadata.attributes == {"clinic_id": "c1"}
    await rag.ingest("c", "aviso.md", MARTES, metadata={"clinic_id": "c2"}, min_chunk_size=3)
    assert (await store.get_document(namespace="c", document_id="aviso.md")).metadata.attributes == {"clinic_id": "c2"}


@pytest.mark.asyncio
async def test_both_faces_write_the_same_document(store):
    r = StoreBackedRetriever(embedder=HashingEmbedder(dim=64), store=store)
    rag = RagStore(store=store, embedder=r.embedder, retriever=r)
    await r.ingest(LUNES, namespace="c", source_ref="aviso.md", config=_CFG)
    await rag.ingest("c", "aviso.md", MARTES, min_chunk_size=3)
    assert [h.chunk.text for h in await rag.search("c", QUERY)] == [MARTES]
    assert [d.document_id for d in await rag.list_documents("c")] == ["aviso.md"]


# --- Contextual Retrieval on the production path --------------------------------


@pytest.mark.asyncio
async def test_ragstore_contextualizer_embeds_context_but_stores_plain_chunk(store):
    embedder = _RecordingEmbedder()
    rag = RagStore.from_components(store=store, embedder=embedder, contextualizer=_MarkerContextualizer())
    await rag.ingest("c", "aviso.md", MARTES, min_chunk_size=3)

    assert embedder.embedded == [f"CTX-MARKER\n\n{MARTES}"]
    assert [c.text for c in await store.get_chunks_by_document(namespace="c", document_id="aviso.md")] == [MARTES]
    assert [h.chunk.text for h in await rag.search("c", QUERY)] == [MARTES]


@pytest.mark.asyncio
async def test_retriever_contextualizer_embeds_context_but_stores_plain_chunk(store):
    embedder = _RecordingEmbedder()
    r = StoreBackedRetriever(embedder=embedder, store=store, contextualizer=_MarkerContextualizer())
    await r.ingest(MARTES, namespace="n", source_ref="aviso.md", config=_CFG)

    assert embedder.embedded == [f"CTX-MARKER\n\n{MARTES}"]
    assert [c.text for c in await store.get_chunks_by_document(namespace="n", document_id="aviso.md")] == [MARTES]


@pytest.mark.asyncio
async def test_ragstore_from_components_default_has_no_contextualizer(store):
    rag = RagStore.from_components(store=store, embedder=HashingEmbedder(dim=64))
    assert rag.retriever.contextualizer is None


# --- plain ChunkStore fallback --------------------------------------------------


@pytest.mark.asyncio
async def test_plain_chunkstore_still_ingests_through_add():
    plain = _PlainChunkStore()
    r = StoreBackedRetriever(embedder=HashingEmbedder(dim=64), store=plain)
    assert await r.ingest(MARTES, namespace="n", source_ref="aviso.md", config=_CFG) == 1
    assert [c.text for _, c, _ in plain.added] == [MARTES]
    assert plain.added[0][1].source_ref == "aviso.md"
    assert [h.chunk.text for h in await r.retrieve(QUERY, namespace="n")] == [MARTES]


@pytest.mark.asyncio
async def test_plain_chunkstore_cannot_replace_a_document():
    r = StoreBackedRetriever(embedder=HashingEmbedder(dim=64), store=_PlainChunkStore())
    with pytest.raises(TypeError, match="DocumentChunkStore"):
        await r.replace_document(namespace="n", document_id="aviso.md", content=MARTES, chunks=[])


@pytest.mark.asyncio
async def test_strategy_string_and_enum_agree_on_the_service_face(store):
    rag = RagStore.from_components(store=store, embedder=HashingEmbedder(dim=64))
    a = await rag.ingest("c", "a.md", MARTES, strategy="paragraph_aware", min_chunk_size=3)
    b = await rag.ingest("c", "b.md", MARTES, strategy=ChunkingStrategy.PARAGRAPH_AWARE, min_chunk_size=3)
    assert a == b == 1
