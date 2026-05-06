"""Tests for the Phase 7 heartbeat lane — reply to commenters on OUR posts.

The heartbeat orchestrator (`reply_to_own_post_commenters`) ties together
many pieces (Source HTTP, world_scans dedup, redaction, persona LLM). The
unit tests here mock all the I/O surfaces and only exercise the orchestrator's
own decisions: filter selection, dedup short-circuit, SKIP-token handling.

The Plan agent flagged dedup-via-`world_scans.has_external_id` as load-bearing
(push-back #1). If a future refactor breaks that path the bot WILL re-publish
the same reply on every 20-minute tick — these tests guard the contract.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from insult.core.moltbook_engagement import (
    _filter_reply_candidates,
    build_reply_to_commenter,
    reply_to_own_post_commenters,
)

# ---------------------------------------------------------------------------
# Pure-fn filter — depth-1 + self/blocked exclusion
# ---------------------------------------------------------------------------


def test_filter_skips_self_authored_comments():
    """Comments from our own author name are dropped (otherwise the bot
    starts replying to itself in a feedback loop)."""
    comments = [
        {"id": "c1", "author": "insultmx", "content": "(my own comment)", "parent_id": None},
        {"id": "c2", "author": "stranger", "content": "real reply", "parent_id": None},
    ]
    kept = _filter_reply_candidates(
        comments,
        own_author="insultmx",
        blocked_authors=frozenset(),
        our_existing_comment_ids=set(),
    )
    assert [c["id"] for c in kept] == ["c2"]


def test_filter_skips_blocked_authors_case_insensitive():
    comments = [
        {"id": "c1", "author": "CICADAfinanceintern", "content": "noise", "parent_id": None},
        {"id": "c2", "author": "honest", "content": "real", "parent_id": None},
    ]
    kept = _filter_reply_candidates(
        comments,
        own_author="insultmx",
        blocked_authors=frozenset({"cicadafinanceintern"}),
        our_existing_comment_ids=set(),
    )
    assert [c["id"] for c in kept] == ["c2"]


def test_filter_skips_nested_replies_to_strangers():
    """Depth ≥2 between strangers is eavesdropping — skip. But a reply to
    OUR comment (parent_id ∈ our_existing) is depth-1 from our voice's
    standpoint and should be kept."""
    comments = [
        # Top-level — keep
        {"id": "c_top", "author": "alice", "content": "a", "parent_id": None},
        # Nested under stranger — skip (eavesdropping)
        {"id": "c_nested", "author": "bob", "content": "b", "parent_id": "c_top"},
        # Nested under OUR earlier reply — keep (continued conversation)
        {"id": "c_to_us", "author": "alice", "content": "follow-up to insult", "parent_id": "our_prior_reply"},
    ]
    kept = _filter_reply_candidates(
        comments,
        own_author="insultmx",
        blocked_authors=frozenset(),
        our_existing_comment_ids={"our_prior_reply"},
    )
    assert {c["id"] for c in kept} == {"c_top", "c_to_us"}


def test_filter_drops_deleted_comments():
    comments = [
        {"id": "c1", "author": "alice", "content": "x", "parent_id": None, "is_deleted": True},
        {"id": "c2", "author": "alice", "content": "y", "parent_id": None},
    ]
    kept = _filter_reply_candidates(
        comments,
        own_author="insultmx",
        blocked_authors=frozenset(),
        our_existing_comment_ids=set(),
    )
    assert [c["id"] for c in kept] == ["c2"]


# ---------------------------------------------------------------------------
# build_reply_to_commenter — SKIP-token handling
# ---------------------------------------------------------------------------


async def test_reply_to_commenter_returns_none_on_skip_token():
    """When the LLM returns the bare SKIP token (or trailing SKIP line)
    the helper must return None so the caller publishes nothing."""

    class _FakeResp:
        def __init__(self, text: str) -> None:
            self.text = text

    llm = MagicMock()
    llm.chat = AsyncMock(return_value=_FakeResp("SKIP"))
    out = await build_reply_to_commenter(
        post_title="x",
        post_content="y",
        parent_comment_author="alice",
        parent_comment_content="(short)",
        persona="persona",
        llm=llm,
    )
    assert out is None


async def test_reply_to_commenter_handles_trailing_skip_line():
    class _FakeResp:
        def __init__(self, text: str) -> None:
            self.text = text

    llm = MagicMock()
    llm.chat = AsyncMock(return_value=_FakeResp("Some reasoning preamble.\nSKIP"))
    out = await build_reply_to_commenter(
        post_title="t",
        post_content="b",
        parent_comment_author="bob",
        parent_comment_content="(meh)",
        persona="persona",
        llm=llm,
    )
    assert out is None


async def test_reply_to_commenter_returns_text_on_normal_reply():
    class _FakeResp:
        def __init__(self, text: str) -> None:
            self.text = text

    llm = MagicMock()
    llm.chat = AsyncMock(return_value=_FakeResp("That frame treats X as Y, but X is just leverage."))
    out = await build_reply_to_commenter(
        post_title="t",
        post_content="b",
        parent_comment_author="bob",
        parent_comment_content="here is a real claim",
        persona="persona",
        llm=llm,
    )
    assert out is not None and "leverage" in out


# ---------------------------------------------------------------------------
# Orchestrator — reply_to_own_post_commenters
# ---------------------------------------------------------------------------


def _orchestrator_deps(
    *,
    activity: list[dict[str, Any]],
    comments_by_post: dict[str, list[dict[str, Any]]],
    has_external_id_returns: bool = False,
):
    """Build the mock surfaces the orchestrator needs. Returns a tuple
    (source, memory, llm) ready to pass into reply_to_own_post_commenters."""
    source = MagicMock()
    source.fetch_home = AsyncMock(return_value={"activity_on_your_posts": activity})
    source.mark_notifications_read = AsyncMock()
    source.create_comment = AsyncMock(return_value=MagicMock(id="our_reply_id"))
    source._request = AsyncMock(side_effect=lambda method, path, **kw: _stub_request_router(path, comments_by_post))
    # client used by redact_with_llm — not exercised when we skip dedup'd comments
    source.client = MagicMock()

    memory = MagicMock()
    memory.has_external_id = AsyncMock(return_value=has_external_id_returns)
    memory.store_world_scan = AsyncMock()
    memory.get_facts = AsyncMock(return_value=[])
    memory.get_arc = AsyncMock(return_value={"phase": "stability"})

    llm = MagicMock()
    llm.client = MagicMock()
    return source, memory, llm


def _stub_request_router(path: str, comments_by_post: dict[str, list[dict[str, Any]]]):
    """Routes the orchestrator's two GETs (post-body + comments) per post."""
    if "/comments" in path:
        # path looks like /posts/{id}/comments
        post_id = path.split("/")[-2]
        return {"comments": comments_by_post.get(post_id, [])}
    if path.startswith("/posts/"):
        post_id = path.split("/")[-1]
        return {"post": {"id": post_id, "content": "post body for " + post_id}}
    return {}


async def test_reply_dedup_via_world_scans_short_circuits_llm(monkeypatch):
    """LOAD-BEARING: when world_scans says we already replied to a
    comment id, the orchestrator must NOT call the LLM, NOT call the
    redactor, and NOT call create_comment for that comment. Otherwise
    the heartbeat publishes duplicates every 20 minutes."""
    activity = [{"post_id": "p1", "post_title": "Session 4", "unread_count": 1}]
    comments_by_post = {"p1": [{"id": "c_already_replied", "author": "alice", "content": "x", "parent_id": None}]}
    source, memory, llm = _orchestrator_deps(
        activity=activity,
        comments_by_post=comments_by_post,
        has_external_id_returns=True,  # ← already replied
    )
    # If the LLM gets called it's a regression — fail loudly.
    llm.chat = AsyncMock(side_effect=AssertionError("LLM should not be invoked when dedup matches"))

    # Block redact_with_llm at module scope so a code-path leak is caught here.
    import insult.core.moltbook_engagement as eng

    monkeypatch.setattr(eng, "redact_with_llm", AsyncMock(side_effect=AssertionError("redact must not run")))

    results = await reply_to_own_post_commenters(
        source=source,
        memory=memory,
        persona="persona",
        llm=llm,
        summary_model="haiku",
        facts_user_ids=[],
        channel_id="ch1",
    )
    assert results == []
    assert source.create_comment.await_count == 0
    assert source.mark_notifications_read.await_count == 0
    # Dedup check ran for the candidate
    memory.has_external_id.assert_awaited_with("moltbook_reply", "c_already_replied")


async def test_orchestrator_publishes_and_persists_world_scan(monkeypatch):
    """Happy path: filter passes, no dedup hit, LLM returns text, redact
    survives, source.create_comment called with parent_id, world_scans
    persisted with external_id == parent comment id (NOT our reply id —
    the dedup key MUST be the upstream comment so future ticks skip)."""
    activity = [{"post_id": "p1", "post_title": "Session 4", "unread_count": 1}]
    comments_by_post = {
        "p1": [{"id": "c_new", "author": "alice", "content": "real claim worth answering", "parent_id": None}]
    }
    source, memory, llm = _orchestrator_deps(
        activity=activity,
        comments_by_post=comments_by_post,
        has_external_id_returns=False,
    )

    class _FakeResp:
        text = "real reply text, in english."

    llm.chat = AsyncMock(return_value=_FakeResp())

    import insult.core.moltbook_engagement as eng

    monkeypatch.setattr(eng, "redact_with_llm", AsyncMock(return_value="real reply text, in english."))
    monkeypatch.setattr(eng, "regex_privacy_strip", lambda t, f: t)
    monkeypatch.setattr(eng, "is_outbound_blocked", AsyncMock(return_value=(None, None)))

    results = await reply_to_own_post_commenters(
        source=source,
        memory=memory,
        persona="persona",
        llm=llm,
        summary_model="haiku",
        facts_user_ids=[],
        channel_id="ch1",
    )
    assert len(results) == 1
    r = results[0]
    assert r.parent_comment_id == "c_new"
    assert r.parent_comment_author == "alice"
    assert r.reply_id == "our_reply_id"

    # create_comment used parent_id wiring — replies must thread under the comment, not the post root
    create_call = source.create_comment.await_args
    assert create_call.args[0] == "p1"
    assert create_call.kwargs["parent_id"] == "c_new"

    # world_scans dedup key = upstream comment id
    persist_call = memory.store_world_scan.await_args
    assert persist_call.kwargs["external_id"] == "c_new"
    assert persist_call.kwargs["source"] == "moltbook_reply"

    # Notifications marked read after the batch
    source.mark_notifications_read.assert_awaited_once_with("p1")


async def test_orchestrator_skips_when_outbound_gate_blocks(monkeypatch):
    """Vulnerability / disclosure gate must short-circuit the entire
    heartbeat — same posture as outbound posting. We never reach the
    home fetch in this branch."""
    source, memory, llm = _orchestrator_deps(
        activity=[],
        comments_by_post={},
    )
    import insult.core.moltbook_engagement as eng

    monkeypatch.setattr(eng, "is_outbound_blocked", AsyncMock(return_value=("vulnerability", "u1")))

    results = await reply_to_own_post_commenters(
        source=source,
        memory=memory,
        persona="persona",
        llm=llm,
        summary_model="haiku",
        facts_user_ids=["u1"],
        channel_id="ch1",
    )
    assert results == []
    source.fetch_home.assert_not_awaited()


async def test_orchestrator_no_activity_returns_empty(monkeypatch):
    """Empty `activity_on_your_posts` is the steady state — no error,
    no replies, no notifications-read calls."""
    source, memory, llm = _orchestrator_deps(activity=[], comments_by_post={})

    import insult.core.moltbook_engagement as eng

    monkeypatch.setattr(eng, "is_outbound_blocked", AsyncMock(return_value=(None, None)))

    results = await reply_to_own_post_commenters(
        source=source,
        memory=memory,
        persona="persona",
        llm=llm,
        summary_model="haiku",
        facts_user_ids=[],
        channel_id="ch1",
    )
    assert results == []
    source.create_comment.assert_not_awaited()
    source.mark_notifications_read.assert_not_awaited()
