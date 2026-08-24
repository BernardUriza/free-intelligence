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


# --- a config that cannot terminate is refused, not obeyed -------------------
# `chunk_size` and `overlap` arrive from an AGENT: `chunk_document` is an MCP
# tool. `chunk_by_fixed_size` advances by `chunk_size - overlap`, so an overlap
# at or above the chunk size is a step of <= 0 — the loop never ends AND appends
# every pass, so one tool call hangs the stdio server and eats the box's memory.


def test_an_overlap_at_or_above_the_chunk_size_is_refused():
    import pytest

    for overlap in (100, 150):
        with pytest.raises(ValueError, match="never advances"):
            ChunkConfig(chunk_size=100, overlap=overlap, min_chunk_size=1)


def test_a_chunk_size_that_rounds_to_zero_words_is_refused():
    """`words_per_chunk = int(chunk_size / 1.3)` is 0 for chunk_size 1, which is
    the same non-terminating loop by a different road."""
    import pytest

    with pytest.raises(ValueError, match="at least 2"):
        ChunkConfig(chunk_size=1, overlap=0, min_chunk_size=1)


def test_negative_sizes_are_refused():
    import pytest

    with pytest.raises(ValueError):
        ChunkConfig(chunk_size=100, overlap=-1)
    with pytest.raises(ValueError):
        ChunkConfig(chunk_size=100, overlap=10, min_chunk_size=-5)


def test_a_legitimate_overlap_still_chunks():
    """The rule tightened; it did not narrow what legitimately works."""
    text = " ".join(f"w{i}" for i in range(400))
    pieces = chunk_document(text, ChunkingStrategy.FIXED_SIZE,
                            ChunkConfig(chunk_size=100, overlap=50, min_chunk_size=1))
    assert len(pieces) > 1


# --- the tail of a document is not a rounding error -------------------------


def test_a_short_tail_joins_the_previous_chunk_instead_of_vanishing():
    """Measured at defaults before the fix: a 330-word text came back as ONE
    chunk covering 307 words, with w307..w329 present in no chunk and no signal
    that anything was missing. The end of a document is where conclusions and the
    most recent entries live — the worst part to lose, and the easiest to not
    notice losing."""
    words = [f"w{i}" for i in range(330)]
    pieces = chunk_document(" ".join(words), ChunkingStrategy.FIXED_SIZE, ChunkConfig())
    covered = {w for piece in pieces for w in piece.split()}
    assert set(words) - covered == set(), "no word may be absent from every chunk"


def test_no_strategy_drops_text_at_any_size():
    """A sweep rather than one case: the loss showed up at 330 words under
    FIXED_SIZE and nowhere else, so a single example would have pinned the
    example instead of the property."""
    for strategy in ChunkingStrategy:
        for n in (50, 120, 200, 330, 500, 700, 1000):
            words = [f"w{i}" for i in range(n)]
            pieces = chunk_document(" ".join(words), strategy, ChunkConfig())
            if not pieces:
                continue  # a document too short to index at all — RagStore refuses it
            covered = {w for piece in pieces for w in piece.split()}
            assert set(words) - covered == set(), f"{strategy.value} lost text at n={n}"


def test_min_chunk_size_still_prevents_a_tiny_STANDALONE_chunk():
    """The rule means "no tiny chunks", not "discard text" — merging the tail must
    not reintroduce the fragment it was there to prevent."""
    words = [f"w{i}" for i in range(330)]
    pieces = chunk_document(" ".join(words), ChunkingStrategy.FIXED_SIZE, ChunkConfig())
    assert all(estimate_tokens(p) >= ChunkConfig().min_chunk_size for p in pieces)
