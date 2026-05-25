"""Tests for Contextual Retrieval — situate chunks before embedding.

The contract: the prompt builder ships Anthropic's canonical text; the
CallableContextualizer bridges a plain async LLM call; and ingest embeds the
CONTEXTUALIZED text while storing the ORIGINAL chunk (faithful citations).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from fi_core.rag import (
    CallableContextualizer,
    Chunk,
    ChunkConfig,
    StoreBackedRetriever,
    build_contextual_prompt,
)


@dataclass
class _SpyEmbedder:
    embedded: list[str] = field(default_factory=list)

    async def embed(self, text: str) -> list[float]:
        self.embedded.append(text)
        return [float(len(text))]


@dataclass
class _SpyStore:
    stored: list[Chunk] = field(default_factory=list)

    async def add(self, *, namespace: str, chunk: Chunk, embedding: list[float]) -> None:  # noqa: ARG002
        self.stored.append(chunk)

    async def query(self, *, namespace, query_embedding, top_k):  # noqa: ANN001 - unused here
        return []


@dataclass
class _FakeContextualizer:
    prefix: str = "CTX"
    seen: list[tuple[str, str]] = field(default_factory=list)

    async def contextualize(self, *, document: str, chunk: str) -> str:
        self.seen.append((document, chunk))
        return f"{self.prefix} for {chunk[:12]}" if self.prefix else ""


_CFG = ChunkConfig(chunk_size=20, overlap=0, min_chunk_size=3)


# --- prompt builder + callable adapter ----------------------------------------


def test_build_contextual_prompt_wraps_document_and_chunk():
    p = build_contextual_prompt("FULL DOC TEXT", "the chunk")
    assert "<document>\nFULL DOC TEXT\n</document>" in p
    assert "<chunk>\nthe chunk\n</chunk>" in p
    assert "succinct context" in p  # Anthropic's instruction


@pytest.mark.asyncio
async def test_callable_contextualizer_calls_with_built_prompt():
    captured = {}

    async def fake_llm(prompt: str) -> str:
        captured["prompt"] = prompt
        return "  situated context.  "  # leading/trailing trimmed

    cc = CallableContextualizer(call=fake_llm)
    out = await cc.contextualize(document="DOC", chunk="CHUNK")
    assert out == "situated context."  # stripped
    assert "<document>\nDOC\n</document>" in captured["prompt"]


# --- ingest with / without contextualizer -------------------------------------


@pytest.mark.asyncio
async def test_ingest_embeds_contextualized_but_stores_original():
    embedder, store, ctx = _SpyEmbedder(), _SpyStore(), _FakeContextualizer()
    r = StoreBackedRetriever(embedder=embedder, store=store, contextualizer=ctx)
    await r.ingest("Dolor toracico opresivo intenso en el paciente grave.", namespace="p", source_ref="hx", config=_CFG)
    assert embedder.embedded, "nothing embedded"
    # the embedded text carries the context prefix...
    assert all(t.startswith("CTX for ") for t in embedder.embedded)
    # ...but the STORED chunk is the original (no CTX prefix) → faithful citation
    assert all(not c.text.startswith("CTX for ") for c in store.stored)
    assert ctx.seen  # the contextualizer saw (document, chunk)


@pytest.mark.asyncio
async def test_ingest_without_contextualizer_embeds_plain_text():
    embedder, store = _SpyEmbedder(), _SpyStore()
    r = StoreBackedRetriever(embedder=embedder, store=store)  # no contextualizer
    await r.ingest("Dolor toracico opresivo intenso en el paciente grave.", namespace="p", source_ref="hx", config=_CFG)
    # embedded == stored text (no contextualization)
    assert embedder.embedded == [c.text for c in store.stored]


@pytest.mark.asyncio
async def test_empty_context_falls_back_to_plain_chunk():
    embedder, store = _SpyEmbedder(), _SpyStore()
    r = StoreBackedRetriever(
        embedder=embedder, store=store, contextualizer=_FakeContextualizer(prefix="")
    )
    # prefix="" → context "" stripped to falsy → no prepend → embed original
    await r.ingest("Dolor toracico opresivo intenso en el paciente grave.", namespace="p", source_ref="hx", config=_CFG)
    assert embedder.embedded == [c.text for c in store.stored]
