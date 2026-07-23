"""The host's Discord shell (#6, slice 4) — the testable seam of the glue.

The network connection needs the real token (the cutover atom, untestable here).
What IS testable: `_ingest` maps a Discord message onto the dispatch loop, and
`run_host` stays DORMANT without a token so the shell never becomes a second
omnipresent bot fighting Insult for reception.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import discord

from demux_ai import host_client
from demux_ai.host_client import HOST_TOKEN_ENV, HostClient, build_host, run_host
from demux_ai.host_loop import HostDispatchLoop


def _message(text: str, *, is_bot: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=999,
        content=text,
        channel=SimpleNamespace(id=111),
        author=SimpleNamespace(id=222, bot=is_bot, display_name="bern"),
        mentions=[],
        role_mentions=[],
    )


def test_ingest_threads_the_message_id_for_reactions():
    """The message id must reach the batcher so the routed turn can anchor its
    [REACT:] markers (the post-cutover reactions regression)."""
    client = _client()
    client._ingest(_message("reséñame Alien"), now=100.0)
    due = client.dispatch_loop.batcher.pop_due(now=200.0)
    assert due == [("111:222", "reséñame Alien", "999", "")]


def _client() -> HostClient:
    loop = HostDispatchLoop(router=SimpleNamespace(route=MagicMock()))
    return HostClient(loop, intents=discord.Intents.none())


def test_ingest_maps_a_human_message_onto_the_loop():
    client = _client()
    accepted = client._ingest(_message("reséñame Alien"), now=100.0)
    assert accepted is True
    assert client.dispatch_loop.batcher.pending_keys() == ["111:222"]


def test_ingest_threads_mentioned_user_ids_to_the_loop():
    """Discord user mentions must reach the host loop for deterministic persona routing."""
    client = _client()
    msg = _message("@Vultur hola")
    msg.mentions = [SimpleNamespace(id=1512687836766404618)]
    assert client._ingest(msg, now=100.0) is True
    assert client.dispatch_loop._forced_target == {}
    client.dispatch_loop.mention_targets = {"1512687836766404618": "vultur"}
    msg = _message("@Vultur hola")
    msg.mentions = [SimpleNamespace(id=1512687836766404618)]
    assert client._ingest(msg, now=101.0) is True
    assert client.dispatch_loop._forced_target == {"111:222": "vultur"}


def test_ingest_threads_mentioned_role_names_to_the_loop():
    """Discord role mentions must reach the host loop for deterministic persona routing."""
    client = _client()
    msg = _message("@Vultur hola")
    msg.role_mentions = [SimpleNamespace(name="Vultur")]
    assert client._ingest(msg, now=100.0) is True
    assert client.dispatch_loop._forced_target == {"111:222": "vultur"}


def test_ingest_ignores_a_bot_message():
    """RESISTANCE: the host never batches another bot's output."""
    client = _client()
    assert client._ingest(_message("soy Vultur", is_bot=True), now=100.0) is False
    assert client.dispatch_loop.batcher.pending_keys() == []


def test_run_host_is_dormant_without_a_token(monkeypatch):
    """RESISTANCE: no token → the shell does NOT connect (no second omnipresent
    bot). It logs and returns instead of ever calling discord's .run()."""
    monkeypatch.delenv(HOST_TOKEN_ENV, raising=False)
    with patch.object(host_client, "build_host") as bh:
        run_host(SimpleNamespace(), token=None)
    bh.assert_not_called()


def test_build_host_enables_message_content_intent():
    """The host must read message text to route it — message_content intent on."""
    client = build_host(SimpleNamespace())
    assert client.intents.message_content is True
