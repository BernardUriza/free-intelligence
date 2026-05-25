"""Tests for StoreBackedRetriever — persistent doc-RAG (embed query → store → chunks).

Uses fake Embedder + ChunkStore (the Protocols) so the glue is verified without a
real model or database. The retriever must: embed only non-empty queries, pass
through the store's ordered hits, apply the similarity floor, and on ingest chunk
→ embed each → add.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from fi_core.rag import Chunk, ChunkConfig, RetrievedChunk, StoreBackedRetriever


@dataclass
class _FakeEmbedder:
    calls: list[str] = field(default_factory=list)

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return [float(len(text)), 1.0]  # deterministic, shape-stable


@dataclass
class _FakeStore:
    hits: list[RetrievedChunk] = field(default_factory=list)
    added: list[tuple[str, Chunk, list[float]]] = field(default_factory=list)
    last_query: dict | None = None

    async def add(self, *, namespace: str, chunk: Chunk, embedding: list[float]) -> None:
        self.added.append((namespace, chunk, embedding))

    async def query(self, *, namespace: str, query_embedding: list[float], top_k: int, filters=None) -> list[RetrievedChunk]:  # noqa: ANN001
        self.last_query = {"namespace": namespace, "embedding": query_embedding, "top_k": top_k}
        return self.hits[:top_k]


def _hit(text: str, sim: float) -> RetrievedChunk:
    return RetrievedChunk(chunk=Chunk(text=text, source_type="document", source_ref="doc1"), similarity=sim)


# --- retrieve -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_embeds_query_and_passes_store_hits_through():
    store = _FakeStore(hits=[_hit("a", 0.9), _hit("b", 0.7)])
    embedder = _FakeEmbedder()
    r = StoreBackedRetriever(embedder=embedder, store=store)
    out = await r.retrieve("¿síntomas?", namespace="patient-1", top_k=2)
    assert embedder.calls == ["¿síntomas?"]  # the query was embedded
    assert store.last_query == {"namespace": "patient-1", "embedding": [float(len("¿síntomas?")), 1.0], "top_k": 2}
    assert [h.chunk.text for h in out] == ["a", "b"]  # store order preserved


@pytest.mark.asyncio
async def test_retrieve_empty_query_short_circuits_without_embedding():
    embedder = _FakeEmbedder()
    r = StoreBackedRetriever(embedder=embedder, store=_FakeStore(hits=[_hit("a", 1.0)]))
    assert await r.retrieve("   ", namespace="n") == []
    assert embedder.calls == []  # no embedder call, no store hit


@pytest.mark.asyncio
async def test_retrieve_applies_similarity_floor():
    store = _FakeStore(hits=[_hit("strong", 0.9), _hit("weak", 0.2)])
    r = StoreBackedRetriever(embedder=_FakeEmbedder(), store=store, min_similarity=0.5)
    out = await r.retrieve("q", namespace="n", top_k=5)
    assert [h.chunk.text for h in out] == ["strong"]  # weak dropped by the floor
    # per-call override loosens it
    out2 = await r.retrieve("q", namespace="n", top_k=5, min_similarity=0.0)
    assert [h.chunk.text for h in out2] == ["strong", "weak"]


# --- ingest -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_chunks_embeds_each_and_adds():
    store = _FakeStore()
    embedder = _FakeEmbedder()
    r = StoreBackedRetriever(embedder=embedder, store=store)
    text = (
        "El paciente presenta dolor torácico opresivo de inicio súbito.\n\n"
        "Antecedentes de hipertensión arterial y diabetes mellitus.\n\n"
        "Se solicita electrocardiograma y troponinas seriadas."
    )
    # Small chunk config so short paragraphs clear min (the chunker measures TOKENS).
    n = await r.ingest(
        text,
        namespace="patient-1",
        source_ref="historia.md",
        config=ChunkConfig(chunk_size=20, overlap=0, min_chunk_size=3),
    )
    assert n == len(store.added) > 0  # one add per chunk
    assert len(embedder.calls) == n  # each chunk embedded
    ns, chunk, _emb = store.added[0]
    assert ns == "patient-1" and chunk.source_ref == "historia.md" and chunk.source_type == "document"


@pytest.mark.asyncio
async def test_ingest_empty_text_stores_nothing():
    store = _FakeStore()
    r = StoreBackedRetriever(embedder=_FakeEmbedder(), store=store)
    assert await r.ingest("   ", namespace="n", source_ref="x") == 0
    assert store.added == []


# --- end-to-end: real chunking + real cosine recall ---------------------------


class _BowEmbedder:
    """Deterministic bag-of-words embedder over a tiny vocab — makes cosine
    meaningful so the e2e proves real ranking, not pass-through."""

    VOCAB = ("dolor", "toracico", "diabetes", "hipertension", "sueno", "animo")

    async def embed(self, text: str) -> list[float]:
        from fi_core.rag import fold_accents

        t = fold_accents(text)
        return [float(t.count(w)) for w in self.VOCAB]


class _CosineStore:
    """In-memory ChunkStore that actually ranks by cosine — the real query path."""

    def __init__(self) -> None:
        self.items: dict[str, list[tuple[Chunk, list[float]]]] = {}

    async def add(self, *, namespace: str, chunk: Chunk, embedding: list[float]) -> None:
        self.items.setdefault(namespace, []).append((chunk, embedding))

    async def query(self, *, namespace: str, query_embedding: list[float], top_k: int, filters=None) -> list[RetrievedChunk]:  # noqa: ANN001
        from fi_core.rag import cosine_similarity

        scored = [
            RetrievedChunk(chunk=c, similarity=cosine_similarity(query_embedding, v))
            for c, v in self.items.get(namespace, [])
        ]
        scored.sort(key=lambda h: h.similarity, reverse=True)
        return scored[:top_k]


@pytest.mark.asyncio
async def test_end_to_end_ingest_then_retrieve_recalls_the_right_chunk():
    r = StoreBackedRetriever(embedder=_BowEmbedder(), store=_CosineStore())
    doc = (
        "El paciente refiere dolor toracico opresivo.\n\n"
        "Tiene antecedentes de diabetes e hipertension.\n\n"
        "Refiere buen sueno y animo estable."
    )
    # paragraph_aware merges small adjacent paragraphs up to chunk_size, so the
    # exact count is the chunker's call; what matters is that recall ranks right.
    n = await r.ingest(doc, namespace="p1", source_ref="hx.md", config=ChunkConfig(chunk_size=20, overlap=0, min_chunk_size=3))
    assert n >= 1
    hits = await r.retrieve("¿tiene dolor toracico?", namespace="p1", top_k=1)
    assert hits and "dolor toracico" in hits[0].chunk.text  # the chest-pain chunk ranked first

