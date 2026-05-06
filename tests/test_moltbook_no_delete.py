"""Operator-policy guard: MoltbookSource MUST NOT delete its own comments.

Lock-in test for the v3.7.67 rule. If a future refactor adds a working
delete_comment / delete_post / cleanup helper to MoltbookSource, this
test fails — and the comment block on the method explains why.

Background: 2026-05-06 — assistant unilaterally deleted 4 replies that
came back verification_failed via raw curl, replacing them with
permanent 'Deleted comment' tombstones in the feed. The operator
escalated. Standing rule since: the bot must NEVER delete published
comments / posts. Failed-verification comments are soft-visible
blemishes; tombstones are loud regret signals — the latter is worse."""

from __future__ import annotations

import pytest

from insult.core.sources.moltbook import MoltbookSource


@pytest.mark.asyncio
async def test_delete_comment_method_raises_not_implemented():
    """The class still defines `delete_comment` — but only as a refusal.
    Calling it MUST raise NotImplementedError so anyone wiring a debug
    endpoint or a cron path discovers the policy at integration time,
    not in production."""
    src = MoltbookSource(api_key="moltbook_test_key")
    with pytest.raises(NotImplementedError) as exc_info:
        await src.delete_comment("any-id")
    msg = str(exc_info.value)
    assert "operator policy" in msg.lower()
    assert "2026-05-06" in msg or "delete" in msg.lower()


def test_no_delete_post_method_exists():
    """We never built one and we will not. If a developer adds one for
    'cleanup' reasons, this assertion catches it. Use the dashboard
    manually if a hard deletion is genuinely required."""
    assert not hasattr(MoltbookSource, "delete_post"), (
        "MoltbookSource.delete_post must not exist — operator policy v3.7.67. "
        "If you need to delete a post, do it via the dashboard manually."
    )
