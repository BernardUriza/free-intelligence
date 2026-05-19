"""Tests for fi_core.rag.chunking.

Pure-Python algorithm — no external services. These tests pin the
contract that AURITY and Insult both rely on.
"""

from __future__ import annotations

from fi_core.rag import (
    ChunkConfig,
    ChunkingStrategy,
    chunk_document,
    estimate_tokens,
)


def test_estimate_tokens_spanish_heuristic():
    """1.3 tokens per word — matches Spanish corpora better than 1:1."""
    assert estimate_tokens("hola que tal") == int(3 * 1.3)
    assert estimate_tokens("") == 0


def test_chunk_document_short_text_with_low_min_returns_single_chunk():
    """When min_chunk_size is lower than the text size, return the text whole."""
    text = "Una oración corta pero suficiente para superar el mínimo."
    chunks = chunk_document(
        text,
        strategy=ChunkingStrategy.PARAGRAPH_AWARE,
        config=ChunkConfig(chunk_size=400, overlap=50, min_chunk_size=3),
    )
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_document_below_min_chunk_size_returns_empty():
    """Pinned contract: text below `min_chunk_size` tokens is dropped."""
    chunks = chunk_document(
        "Una corta.",  # ~2 words / ~3 tokens
        strategy=ChunkingStrategy.PARAGRAPH_AWARE,
        config=ChunkConfig(chunk_size=400, overlap=50, min_chunk_size=100),
    )
    assert chunks == []


def test_chunk_document_empty_returns_empty():
    assert chunk_document("") == []


def test_paragraph_aware_splits_when_chunk_size_exceeded():
    """Two paragraphs that together exceed chunk_size end up in separate chunks."""
    # Each paragraph ~40 tokens, chunk_size=30 → must split.
    para_a = " ".join(["palabra"] * 30)
    para_b = " ".join(["otra"] * 30)
    text = f"{para_a}\n\n{para_b}"
    chunks = chunk_document(
        text,
        strategy=ChunkingStrategy.PARAGRAPH_AWARE,
        config=ChunkConfig(chunk_size=30, overlap=5, min_chunk_size=10),
    )
    assert len(chunks) >= 2
    assert any("palabra" in c for c in chunks)
    assert any("otra" in c for c in chunks)


def test_sentence_aware_keeps_sentences_whole():
    text = (
        "Primera oración aquí. "
        "Segunda oración también aquí. "
        "Tercera para tener material. "
        "Cuarta oración cierra el bloque."
    )
    chunks = chunk_document(
        text,
        strategy=ChunkingStrategy.SENTENCE_AWARE,
        config=ChunkConfig(chunk_size=10, overlap=2, min_chunk_size=3),
    )
    # Each chunk should be 1-2 sentences
    for c in chunks:
        assert c.endswith(".") or c.endswith("?") or c.endswith("!")


def test_fixed_size_produces_overlapping_chunks():
    text = " ".join(["palabra"] * 200)
    chunks = chunk_document(
        text,
        strategy=ChunkingStrategy.FIXED_SIZE,
        config=ChunkConfig(chunk_size=100, overlap=20, min_chunk_size=10),
    )
    assert len(chunks) >= 2
    # Overlap means adjacent chunks share a suffix/prefix
    for i in range(len(chunks) - 1):
        # Some words from chunk i should appear at start of chunk i+1
        first_words_next = chunks[i + 1].split()[:5]
        # Last 5 words of chunk i should overlap with first 5 of chunk i+1
        # (at minimum 1 should match because of overlap)
        last_words_curr = chunks[i].split()[-10:]
        assert any(w in last_words_curr for w in first_words_next), f"No overlap between chunk {i} and chunk {i + 1}"


def test_min_chunk_size_filters_tiny_chunks():
    text = "a b c"  # 3 words, ~4 tokens
    chunks = chunk_document(
        text,
        strategy=ChunkingStrategy.PARAGRAPH_AWARE,
        config=ChunkConfig(chunk_size=100, overlap=0, min_chunk_size=10),
    )
    # Below min — filtered out
    assert chunks == []


def test_paragraph_strategy_falls_back_to_sentences_for_huge_paragraph():
    """A single paragraph exceeding 1.5 * chunk_size gets sentence-split."""
    long_para = " ".join([f"Oración {i}." for i in range(50)])
    chunks = chunk_document(
        long_para,
        strategy=ChunkingStrategy.PARAGRAPH_AWARE,
        config=ChunkConfig(chunk_size=30, overlap=5, min_chunk_size=10),
    )
    # Should split into multiple chunks via sentence fallback
    assert len(chunks) > 1
