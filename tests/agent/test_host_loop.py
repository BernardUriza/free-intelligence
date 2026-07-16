"""The host dispatch loop (#6, slice 3) — inbound stream → debounced routed turns.

Positive: a human message batches and, on a later tick past the window, routes to
a persona. Resistance: bot-authored and command-prefixed messages are ignored (the
host never routes another bot's output or a `!command`); a batch not yet due does
not dispatch.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from demux_ai import dispatch
from demux_ai.batch import MessageBatcher
from demux_ai.host_loop import HostDispatchLoop


def _loop(target="vultur") -> HostDispatchLoop:
    router = SimpleNamespace(route=AsyncMock(return_value=SimpleNamespace(target=target, reason=f"llm_{target}")))
    return HostDispatchLoop(router=router, batcher=MessageBatcher(window_seconds=3.0))


async def test_human_message_batches_then_dispatches_on_a_due_tick():
    loop = _loop("vultur")
    assert loop.handle_message(
        channel_id="C1", author_id="u1", author_is_bot=False, text="reséñame Solaris", now=100.0, author_name="bern"
    )
    with patch.object(dispatch, "summon_persona", new=AsyncMock(return_value=True)) as summon:
        assert await loop.tick(now=101.0) == []  # not due yet
        decisions = await loop.tick(now=104.0)  # quiet past window
    assert [d.target for d in decisions] == ["vultur"]
    assert summon.await_args.kwargs["persona_id"] == "vultur"
    assert "reséñame Solaris" in summon.await_args.args[0]["reason"]


async def test_mentioned_persona_forces_dispatch_without_router():
    """An explicit bot @mention in a burst wins over the LLM router's topical default."""
    router = SimpleNamespace(route=AsyncMock(return_value=SimpleNamespace(target="insult", reason="llm_insult")))
    loop = HostDispatchLoop(
        router=router,
        batcher=MessageBatcher(window_seconds=3.0),
        mention_targets={"1512687836766404618": "vultur"},
    )
    assert loop.handle_message(
        channel_id="C1",
        author_id="u1",
        author_is_bot=False,
        text="@Vultur hola",
        now=100.0,
        mentioned_ids=["1512687836766404618"],
    )
    with patch.object(dispatch, "summon_persona", new=AsyncMock(return_value=True)) as summon:
        decisions = await loop.tick(now=104.0)
    router.route.assert_not_awaited()
    assert [d.target for d in decisions] == ["vultur"]
    assert summon.await_args.kwargs["persona_id"] == "vultur"


async def test_latest_mentioned_persona_in_a_burst_wins():
    """If a burst mentions two personas, the latest explicit mention is routed."""
    router = SimpleNamespace(route=AsyncMock(return_value=SimpleNamespace(target="insult", reason="llm_insult")))
    loop = HostDispatchLoop(
        router=router,
        batcher=MessageBatcher(window_seconds=3.0),
        mention_targets={"1512687836766404618": "vultur", "1503983124982534284": "alice"},
    )
    loop.handle_message(
        channel_id="C1",
        author_id="u1",
        author_is_bot=False,
        text="@Vultur espera",
        now=100.0,
        mentioned_ids=["1512687836766404618"],
    )
    loop.handle_message(
        channel_id="C1",
        author_id="u1",
        author_is_bot=False,
        text="@ALICE mejor tú",
        now=101.0,
        mentioned_ids=["1503983124982534284"],
    )
    with patch.object(dispatch, "summon_persona", new=AsyncMock(return_value=True)) as summon:
        decisions = await loop.tick(now=105.0)
    router.route.assert_not_awaited()
    assert [d.target for d in decisions] == ["alice"]
    assert summon.await_args.kwargs["persona_id"] == "alice"


async def test_bot_authored_message_is_ignored():
    """RESISTANCE: the host never routes another bot's output (loop guard)."""
    loop = _loop()
    assert (
        loop.handle_message(channel_id="C1", author_id="b", author_is_bot=True, text="soy Vultur", now=100.0) is False
    )
    assert loop.batcher.pending_keys() == []


async def test_command_prefixed_message_is_ignored():
    """RESISTANCE: `!`/`/` lines are commands, not turns."""
    loop = _loop()
    assert loop.handle_message(channel_id="C1", author_id="u1", author_is_bot=False, text="!ping", now=100.0) is False
    assert loop.handle_message(channel_id="C1", author_id="u1", author_is_bot=False, text="/help", now=100.0) is False
    assert loop.batcher.pending_keys() == []


async def test_tick_with_nothing_due_dispatches_nothing():
    loop = _loop()
    loop.handle_message(channel_id="C1", author_id="u1", author_is_bot=False, text="hola", now=100.0)
    with patch.object(dispatch, "summon_persona", new=AsyncMock()) as summon:
        assert await loop.tick(now=101.0) == []
    summon.assert_not_awaited()
