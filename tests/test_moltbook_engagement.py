"""Tests for the engagement lane (search → comment on others' posts)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from insult.core.moltbook_engagement import (
    EngagementCandidate,
    _already_engaged_post_ids,
    _tokenize_topic,
    extract_engagement_keywords,
    search_candidates,
)
from insult.core.sources.base import Post


@dataclass
class _FakeMemory:
    world_scans: list[dict]
    facts: dict[str, list[dict]] | None = None

    async def get_recent_world_scans(self, limit: int = 10, source: str | None = None) -> list[dict]:
        rows = self.world_scans
        if source:
            rows = [r for r in rows if r.get("source") == source]
        return rows[:limit]

    async def get_facts(self, user_id: str) -> list[dict]:
        return (self.facts or {}).get(user_id, [])


def _post(pid: str, *, author: str = "someone", title: str = "t", created: float | None = None) -> Post:
    return Post(
        id=pid,
        title=title,
        content="body",
        author=author,
        submolt="philosophy",
        upvotes=0,
        comment_count=0,
        created_at=created if created is not None else time.time(),
        url=None,
        source="moltbook",
    )


class TestTokenize:
    def test_drops_short_and_stopwords(self):
        assert "with" not in _tokenize_topic("things with substance")
        assert "the" not in _tokenize_topic("the thing")

    def test_lowercases(self):
        assert "resilience" in _tokenize_topic("RESILIENCE emergence")

    def test_keeps_meaningful_words(self):
        toks = _tokenize_topic("resilience emergence patterns")
        assert "resilience" in toks
        assert "emergence" in toks
        assert "patterns" in toks


class TestExtractKeywords:
    @pytest.mark.asyncio
    async def test_skips_own_outbound_rows(self):
        mem = _FakeMemory(
            world_scans=[
                {"source": "moltbook_outbound", "topic": "Session 1 Emergence after collapse"},
                {"source": "world_scan", "topic": "consciousness emergence in agents"},
            ]
        )
        kws = await extract_engagement_keywords(mem, max_keywords=5)
        # 'session', 'emergence', 'collapse' would come from the moltbook_
        # outbound row but should be excluded.
        assert "session" not in kws
        assert "emergence" in kws  # from non-outbound row
        assert "consciousness" in kws

    @pytest.mark.asyncio
    async def test_dedupes_in_recency_order(self):
        mem = _FakeMemory(
            world_scans=[
                {"source": "world_scan", "topic": "consciousness emergence"},
                {"source": "world_scan", "topic": "emergence patterns"},
            ]
        )
        kws = await extract_engagement_keywords(mem, max_keywords=5)
        assert kws.index("emergence") < kws.index("patterns")
        assert kws.count("emergence") == 1


class TestAlreadyEngaged:
    @pytest.mark.asyncio
    async def test_extracts_post_id_from_commentary(self):
        mem = _FakeMemory(
            world_scans=[
                {
                    "source": "moltbook_engagement",
                    "commentary": "post_id=00000000-0000-0000-0000-000000000001 keyword=foo",
                },
            ]
        )
        ids = await _already_engaged_post_ids(mem)
        assert "00000000-0000-0000-0000-000000000001" in ids

    @pytest.mark.asyncio
    async def test_empty_when_no_engagement_rows(self):
        mem = _FakeMemory(world_scans=[])
        assert await _already_engaged_post_ids(mem) == set()


class TestSearchCandidates:
    @pytest.mark.asyncio
    async def test_drops_own_posts(self):
        source = AsyncMock()
        source.search_posts = AsyncMock(
            return_value=[
                _post("p1", author="insultmx"),
                _post("p2", author="someone"),
            ]
        )
        mem = _FakeMemory(world_scans=[])
        cands = await search_candidates(source, ["resilience"], mem)
        ids = {c.post.id for c in cands}
        assert "p1" not in ids
        assert "p2" in ids

    @pytest.mark.asyncio
    async def test_drops_stale_posts(self):
        old = time.time() - 10 * 86400  # 10 days, > 7d cutoff
        source = AsyncMock()
        source.search_posts = AsyncMock(
            return_value=[
                _post("old", created=old),
                _post("new"),
            ]
        )
        mem = _FakeMemory(world_scans=[])
        cands = await search_candidates(source, ["k"], mem)
        ids = {c.post.id for c in cands}
        assert "old" not in ids
        assert "new" in ids

    @pytest.mark.asyncio
    async def test_drops_already_engaged(self):
        source = AsyncMock()
        source.search_posts = AsyncMock(return_value=[_post("seen"), _post("fresh")])
        mem = _FakeMemory(
            world_scans=[
                {
                    "source": "moltbook_engagement",
                    "commentary": "post_id=seen keyword=foo",
                },
            ]
        )
        cands = await search_candidates(source, ["k"], mem)
        ids = {c.post.id for c in cands}
        assert "seen" not in ids
        assert "fresh" in ids

    @pytest.mark.asyncio
    async def test_dedupes_across_keywords(self):
        source = AsyncMock()
        source.search_posts = AsyncMock(return_value=[_post("dup")])
        mem = _FakeMemory(world_scans=[])
        cands = await search_candidates(source, ["k1", "k2"], mem)
        assert len(cands) == 1
        # First keyword wins
        assert cands[0].keyword == "k1"


class TestEngagementCandidate:
    def test_dataclass_instantiation(self):
        c = EngagementCandidate(post=_post("x"), keyword="resilience")
        assert c.post.id == "x"
        assert c.keyword == "resilience"


# ---------------------------------------------------------------------------
# Block-list — operator-defined skip authors
# ---------------------------------------------------------------------------


class TestBlockedAuthors:
    @pytest.mark.asyncio
    async def test_search_candidates_skips_blocked_author(self):
        source = AsyncMock()
        source.search_posts = AsyncMock(
            return_value=[
                _post("p1", author="cicadafinanceintern"),
                _post("p2", author="someone_else"),
            ]
        )
        mem = _FakeMemory(world_scans=[])
        cands = await search_candidates(
            source,
            ["resilience"],
            mem,
            blocked_authors=frozenset(["cicadafinanceintern"]),
        )
        ids = {c.post.id for c in cands}
        assert "p1" not in ids
        assert "p2" in ids

    @pytest.mark.asyncio
    async def test_search_candidates_blocked_check_is_case_insensitive(self):
        source = AsyncMock()
        source.search_posts = AsyncMock(return_value=[_post("p1", author="CicadaFinanceIntern")])
        mem = _FakeMemory(world_scans=[])
        cands = await search_candidates(
            source,
            ["k"],
            mem,
            blocked_authors=frozenset(["cicadafinanceintern"]),
        )
        assert cands == []

    @pytest.mark.asyncio
    async def test_search_candidates_no_block_list_lets_all_through(self):
        source = AsyncMock()
        source.search_posts = AsyncMock(return_value=[_post("p1", author="cicadafinanceintern")])
        mem = _FakeMemory(world_scans=[])
        # No blocked_authors arg → defaults to empty set, all pass
        cands = await search_candidates(source, ["k"], mem)
        assert len(cands) == 1
