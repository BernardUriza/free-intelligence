"""Integration smoke: StoreBackedRetriever against a REAL pgvector database.

Skipped unless ``FI_RAG_PGVECTOR_TEST_DSN`` points at a Postgres with the
``vector`` extension. Spin one up throwaway::

    docker run -d --name fi-rag-smoke -e POSTGRES_PASSWORD=smoke \
        -e POSTGRES_DB=firag -p 5433:5432 pgvector/pgvector:pg16
    docker exec fi-rag-smoke psql -U postgres -d firag -c 'CREATE EXTENSION IF NOT EXISTS vector;'
    FI_RAG_PGVECTOR_TEST_DSN=postgresql://postgres:smoke@localhost:5433/firag \
        pytest tests/test_rag_pgvector_smoke.py -v

Uses a deterministic bag-of-words embedder (no model download) so the test
exercises the STORE path — schema, RPUSH-equivalent add, and pgvector's ``<=>``
cosine query — fast and offline-of-cloud. The real embedder path
(sentence-transformers / Azure) is the embedder's own concern.
"""

from __future__ import annotations

import os
import uuid

import pytest

from fi_core.rag import ChunkConfig, StoreBackedRetriever, fold_accents

_DSN = os.getenv("FI_RAG_PGVECTOR_TEST_DSN")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _DSN, reason="set FI_RAG_PGVECTOR_TEST_DSN to a pgvector DB"),
]

_VOCAB = ("dolor", "toracico", "diabetes", "hipertension", "sueno", "animo", "ecg", "troponinas")


class _DetEmbedder:
    """8-dim bag-of-words over a fixed vocab — deterministic, no model."""

    async def embed(self, text: str) -> list[float]:
        t = fold_accents(text)
        vec = [float(t.count(w)) for w in _VOCAB]
        return vec if any(vec) else [1.0, *([0.0] * (len(_VOCAB) - 1))]  # never a zero vector


@pytest.mark.asyncio
async def test_pgvector_ingest_then_semantic_retrieve():
    from fi_core.stores.pgvector import PgVectorChunkStore

    store = PgVectorChunkStore(dsn=_DSN, embedding_dim=len(_VOCAB), table_prefix="fi_rag_test")
    await store.init_schema()
    namespace = f"smoke-{uuid.uuid4().hex[:8]}"  # isolate this run
    try:
        retriever = StoreBackedRetriever(embedder=_DetEmbedder(), store=store)
        doc = (
            "El paciente refiere dolor toracico opresivo intenso.\n\n"
            "Antecedentes de diabetes e hipertension cronica.\n\n"
            "Refiere buen sueno y animo estable sin novedad."
        )
        n = await retriever.ingest(
            doc, namespace=namespace, source_ref="hx.md",
            config=ChunkConfig(chunk_size=20, overlap=0, min_chunk_size=3),
        )
        assert n >= 1  # chunks persisted to pgvector

        hits = await retriever.retrieve("sueno animo", namespace=namespace, top_k=1)
        assert hits, "pgvector returned no hits"
        assert "sueno" in hits[0].chunk.text  # the right chunk ranked first via <=> cosine
        assert 0.0 <= hits[0].similarity <= 1.0

        # isolation: an empty namespace yields nothing (no cross-tenant leak)
        assert await retriever.retrieve("dolor", namespace="smoke-empty", top_k=3) == []
    finally:
        close = getattr(store, "close", None)
        if close is not None:
            await close()
