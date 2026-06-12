"""Tests for the Source ABC, dataclasses, and registry.

Concrete platform tests (Moltbook HTTP client, etc.) live in their own
files. This file only tests the abstraction itself."""

from __future__ import annotations

import pytest

from personas.insult.core.sources import (
    Comment,
    Post,
    Source,
    SourceAuthError,
    SourceError,
    SourceNotFoundError,
    SourceRateLimitError,
    SourceTransientError,
    get_source,
    list_sources,
    register_source,
)
from personas.insult.core.sources.registry import _clear


class _FakeSource(Source):
    """Minimal Source implementation for registry / dataclass tests."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def fetch_feed(self, sort: str = "hot", limit: int = 10) -> list[Post]:
        return []

    async def fetch_submolt_posts(self, submolt: str, sort: str = "hot", limit: int = 10) -> list[Post]:
        return []

    async def search_posts(self, query: str, limit: int = 10) -> list[Post]:
        return []

    async def create_post(self, submolt: str, title: str, content: str) -> Post:
        return Post(
            id="x",
            title=title,
            content=content,
            author="me",
            submolt=submolt,
            upvotes=0,
            comment_count=0,
            created_at=0.0,
            source=self._name,
        )

    async def create_comment(self, post_id: str, content: str) -> Comment:
        return Comment(
            id="c",
            post_id=post_id,
            content=content,
            author="me",
            upvotes=0,
            created_at=0.0,
            source=self._name,
        )

    async def upvote_post(self, post_id: str) -> None:
        return None

    async def health_check(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def _clean_registry():
    """Each test starts with an empty registry — tests in this file all
    register their own fakes and shouldn't bleed into each other or the
    process-wide singleton."""
    _clear()
    yield
    _clear()


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def test_all_errors_inherit_from_source_error():
    assert issubclass(SourceAuthError, SourceError)
    assert issubclass(SourceRateLimitError, SourceError)
    assert issubclass(SourceTransientError, SourceError)
    assert issubclass(SourceNotFoundError, SourceError)


def test_rate_limit_error_carries_retry_after():
    e = SourceRateLimitError("slow down", retry_after_seconds=12.5)
    assert e.retry_after_seconds == 12.5
    assert "slow down" in str(e)


def test_rate_limit_error_retry_after_optional():
    e = SourceRateLimitError("no header sent")
    assert e.retry_after_seconds is None


# ---------------------------------------------------------------------------
# Dataclass shapes
# ---------------------------------------------------------------------------


def test_post_minimum_fields():
    p = Post(
        id="p1",
        title="t",
        content="c",
        author="a",
        submolt="m/test",
        upvotes=0,
        comment_count=0,
        created_at=1700000000.0,
    )
    assert p.id == "p1"
    assert p.url is None
    assert p.source == ""
    assert p.raw == {}


def test_comment_minimum_fields():
    c = Comment(id="c1", post_id="p1", content="hello", author="a", upvotes=0, created_at=1700000000.0)
    assert c.post_id == "p1"
    assert c.source == ""
    assert c.raw == {}


def test_post_carries_raw_payload():
    p = Post(
        id="p1",
        title="t",
        content="c",
        author="a",
        submolt="m/test",
        upvotes=5,
        comment_count=2,
        created_at=1700000000.0,
        url="https://example.com/p1",
        source="moltbook",
        raw={"extra_field": "value", "platform_only": True},
    )
    assert p.raw["extra_field"] == "value"
    assert p.url == "https://example.com/p1"


# ---------------------------------------------------------------------------
# Registry behavior
# ---------------------------------------------------------------------------


def test_register_then_get_round_trip():
    fake = _FakeSource("moltbook")
    register_source(fake)
    assert get_source("moltbook") is fake


def test_get_unknown_raises_key_error_with_helpful_message():
    register_source(_FakeSource("moltbook"))
    with pytest.raises(KeyError) as exc:
        get_source("reddit")
    assert "reddit" in str(exc.value)
    assert "moltbook" in str(exc.value)  # lists available sources


def test_register_replaces_same_name():
    """Last writer wins so test fixtures can rebind without leaking."""
    a = _FakeSource("moltbook")
    b = _FakeSource("moltbook")
    register_source(a)
    register_source(b)
    assert get_source("moltbook") is b


def test_list_sources_returns_sorted():
    register_source(_FakeSource("zeta"))
    register_source(_FakeSource("alpha"))
    register_source(_FakeSource("mu"))
    assert list_sources() == ["alpha", "mu", "zeta"]


def test_clear_empties_registry():
    register_source(_FakeSource("moltbook"))
    _clear()
    assert list_sources() == []


# ---------------------------------------------------------------------------
# ABC enforcement — can't instantiate Source directly
# ---------------------------------------------------------------------------


def test_source_is_abstract():
    """Direct instantiation of Source should fail at class level."""
    with pytest.raises(TypeError):
        Source()  # type: ignore[abstract]


async def test_fake_source_satisfies_contract():
    """Smoke: FakeSource implements all required abstract methods, so it
    can be instantiated and called without error."""
    f = _FakeSource("test")
    assert f.name == "test"
    assert await f.fetch_feed() == []
    assert await f.fetch_submolt_posts("m/x") == []
    assert await f.search_posts("q") == []
    p = await f.create_post("m/x", "title", "body")
    assert p.title == "title"
    c = await f.create_comment("p1", "comment")
    assert c.post_id == "p1"
    assert await f.upvote_post("p1") is None
    assert await f.health_check() is True
    await f.close()  # default no-op
