"""Tests for the world_scans repository — covers the v3.7.12 schema migration
that added `source` and `external_id` columns plus the partial UNIQUE index
that backs Moltbook digest dedupe."""

from __future__ import annotations

import os
import tempfile

import pytest

from insult.core.memory.store import MemoryStore


@pytest.fixture
async def store():
    """Fresh on-disk MemoryStore per test — schema migrations run on connect."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = MemoryStore(path)
    await s.connect()
    try:
        yield s
    finally:
        await s.close()
        os.remove(path)


async def test_store_default_source_is_web(store):
    """Pre-existing callers that pass no source should land in source='web'."""
    inserted = await store.store_world_scan("topic", "findings", "commentary")
    assert inserted is True
    rows = await store.get_recent_world_scans(limit=10)
    assert len(rows) == 1
    assert rows[0]["source"] == "web"
    assert rows[0]["external_id"] is None


async def test_store_with_external_source_and_id(store):
    inserted = await store.store_world_scan(
        "art expo",
        "findings text",
        "in-character take",
        source="moltbook",
        external_id="post_abc123",
    )
    assert inserted is True
    rows = await store.get_recent_world_scans(limit=10, source="moltbook")
    assert len(rows) == 1
    assert rows[0]["external_id"] == "post_abc123"


async def test_dedupe_skips_second_insert_with_same_external_id(store):
    """Two stores with same (source, external_id) — first inserts, second
    is a no-op via INSERT OR IGNORE. Critical for Moltbook digest fetchers
    that may see the same post across consecutive polls."""
    a = await store.store_world_scan("t", "f", "c", source="moltbook", external_id="dup_1")
    b = await store.store_world_scan("t", "f", "c", source="moltbook", external_id="dup_1")
    assert a is True
    assert b is False  # deduped
    rows = await store.get_recent_world_scans(limit=10, source="moltbook")
    assert len(rows) == 1


async def test_dedupe_does_not_block_different_source(store):
    """Same external_id under different sources must coexist — Moltbook post
    'abc' and a Reddit post 'abc' are unrelated."""
    a = await store.store_world_scan("t", "f", "c", source="moltbook", external_id="abc")
    b = await store.store_world_scan("t", "f", "c", source="reddit", external_id="abc")
    assert a is True
    assert b is True
    rows = await store.get_recent_world_scans(limit=10)
    assert len(rows) == 2


async def test_dedupe_does_not_block_null_external_ids(store):
    """The UNIQUE index is partial (WHERE external_id IS NOT NULL), so legacy
    web rows without an external_id never collide regardless of count."""
    a = await store.store_world_scan("a", "f", "c")
    b = await store.store_world_scan("b", "f", "c")
    c = await store.store_world_scan("c", "f", "c")
    assert a is True and b is True and c is True
    rows = await store.get_recent_world_scans(limit=10)
    assert len(rows) == 3


async def test_get_recent_filters_by_source(store):
    await store.store_world_scan("web1", "f", "c")
    await store.store_world_scan("mb1", "f", "c", source="moltbook", external_id="m1")
    await store.store_world_scan("mb2", "f", "c", source="moltbook", external_id="m2")
    web_only = await store.get_recent_world_scans(source="web")
    mb_only = await store.get_recent_world_scans(source="moltbook")
    assert {r["topic"] for r in web_only} == {"web1"}
    assert {r["topic"] for r in mb_only} == {"mb1", "mb2"}


async def test_get_recent_no_source_filter_returns_all(store):
    await store.store_world_scan("web1", "f", "c")
    await store.store_world_scan("mb1", "f", "c", source="moltbook", external_id="m1")
    rows = await store.get_recent_world_scans(limit=10)
    assert {r["topic"] for r in rows} == {"web1", "mb1"}


async def test_has_external_id_true_when_present(store):
    await store.store_world_scan("t", "f", "c", source="moltbook", external_id="abc")
    assert await store.has_external_id("moltbook", "abc") is True


async def test_has_external_id_false_when_absent(store):
    assert await store.has_external_id("moltbook", "never_seen") is False


async def test_has_external_id_respects_source_boundary(store):
    """A post id seen under one source must not match under another source."""
    await store.store_world_scan("t", "f", "c", source="moltbook", external_id="abc")
    assert await store.has_external_id("reddit", "abc") is False


async def test_get_recent_results_include_new_columns(store):
    """Schema migration smoke: returned dicts must carry source + external_id
    so downstream consumers can render attribution / link back to original."""
    await store.store_world_scan("t", "f", "c", source="moltbook", external_id="post_42")
    rows = await store.get_recent_world_scans(limit=1)
    assert "source" in rows[0]
    assert "external_id" in rows[0]
    assert rows[0]["source"] == "moltbook"
    assert rows[0]["external_id"] == "post_42"
