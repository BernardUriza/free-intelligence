"""Tests for `insult.core.deep_memory` (DM-3+).

Pure unit tests live here. Integration tests against a live PG +
Azure OpenAI live in scripts/backfill_deep_memory.py's manual run path
(already validated 2026-05-19 against prod with 293 chunks ingested).
"""

from __future__ import annotations

import importlib

import pytest


def test_module_imports_clean():
    """Module loads without side effects when AZURE_OPENAI vars are unset.

    The runner side imports `deep_memory` at module load time; if any
    top-level code triggered an Azure client constructor we'd get a
    boot-time error in environments where embeddings are intentionally
    not configured (CI, smoke tests, dev without secrets).
    """
    mod = importlib.import_module("insult.core.deep_memory")
    # Defaults are env-driven; importing must NOT raise.
    assert mod.EMBEDDING_DIM == 1536
    assert mod.EMBEDDING_DEPLOYMENT  # default or env-overridden


def test_chunk_text_for_embedding_short_text_returns_empty_or_single():
    """Tiny text falls under min_chunk_size — drop it, don't index noise.

    The chunker filters chunks below 50 tokens by default. A two-word
    string is well below; the wrapper should return [] (matches fi-core
    PARAGRAPH_AWARE behavior), not crash.
    """
    from insult.core.deep_memory import chunk_text_for_embedding

    assert chunk_text_for_embedding("") == []
    assert chunk_text_for_embedding("  ") == []
    # Below min_chunk_size (50 tokens) — filtered out
    assert chunk_text_for_embedding("short") == []


def test_chunk_text_for_embedding_long_text_produces_multiple_chunks():
    """Real-sized conversation text produces multiple paragraph-aware chunks."""
    from insult.core.deep_memory import chunk_text_for_embedding

    # ~800 tokens of representative conversation text
    text = (
        "\n\n".join(
            f"[2026-05-{day:02d} 10:00] bernard: "
            + " ".join(["palabra"] * 30)
            for day in range(1, 21)
        )
    )
    chunks = chunk_text_for_embedding(text, chunk_size=200, overlap=20)
    assert len(chunks) >= 2
    # No chunk should be empty
    assert all(c.strip() for c in chunks)


@pytest.mark.asyncio
async def test_query_user_memory_empty_args_returns_empty():
    """Defensive: bad args never hit the API or the DB."""
    from insult.core.deep_memory import query_user_memory

    assert await query_user_memory(user_id="", query="x", top_k=5) == []
    assert await query_user_memory(user_id="abc", query="", top_k=5) == []
    assert await query_user_memory(user_id="abc", query="x", top_k=0) == []
    assert await query_user_memory(user_id="abc", query="x", top_k=-1) == []


@pytest.mark.asyncio
async def test_insert_chunks_empty_inputs_returns_zero():
    """Same defensive shape on the insert side."""
    from insult.core.deep_memory import insert_chunks

    assert (
        await insert_chunks(user_id="", source_type="message", source_ref="r", chunks=["x"])
        == 0
    )
    assert (
        await insert_chunks(user_id="u", source_type="invalid_type", source_ref="r", chunks=["x"])
        == 0
    )
    assert (
        await insert_chunks(user_id="u", source_type="message", source_ref="r", chunks=[])
        == 0
    )
    assert (
        await insert_chunks(user_id="u", source_type="message", source_ref="r", chunks=["", "  "])
        == 0
    )
