"""Gateway [REMIND:] + [REMEMBER:] wiring — the markers stopped leaking raw.

THE BUG this locks out (P0 2026-07-14): the personas were still instructed to emit
`[REMIND:]` / `[REMEMBER:]`, but post-castigo the gateway parsed NEITHER — so both
markers went out RAW into Discord and the intent behind them (a scheduled row, a
learned fact) died unstored.

Mutator rule: positive (marker → stripped from the visible text AND persisted) +
resistance (no marker → untouched; a persistence failure → the message still
sends, the marker still never leaks, the turn never raises).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _channel():
    channel = MagicMock()
    channel.send = AsyncMock()
    channel.typing = MagicMock(return_value=_Typing())
    return channel


def _client(reply_text: str) -> PersonaClient:
    persona = Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.save_reminder = AsyncMock(return_value=42)
    memory.add_remember_fact = AsyncMock(return_value=7)
    memory.save_facts = AsyncMock()
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply_text, model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


async def _deliver(client: PersonaClient, channel) -> None:
    await client._run_and_deliver(
        channel=channel,
        channel_id="C1",
        user_id="U1",
        guild_id="G1",
        channel_name="general",
        messages=[{"role": "user", "content": "recuérdame sacar la ropa en 2 horas"}],
        react_to=MagicMock(),
    )


def _sent(channel) -> str:
    return " ".join(str(c) for c in channel.send.call_args_list)


# --------------------------------------------------------------------------
# [REMIND:]
# --------------------------------------------------------------------------


async def test_remind_marker_persists_and_is_stripped():
    client = _client("Va, te lo agendo.[REMIND: +2h | sacar la ropa de la lavadora]")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.save_reminder.assert_awaited_once()
    kwargs = client.memory.save_reminder.await_args.kwargs
    assert kwargs["description"] == "sacar la ropa de la lavadora"
    assert kwargs["channel_id"] == "C1"
    assert kwargs["created_by"] == "U1"

    sent = _sent(channel)
    assert "Va, te lo agendo." in sent
    assert "REMIND" not in sent
    assert "REMIND" not in client.memory.store.call_args.args[4]


async def test_no_remind_marker_persists_nothing():
    """RESISTANCE: an ordinary reply never writes a reminder row."""
    client = _client("Reseña normal, sin agendas.")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.save_reminder.assert_not_awaited()
    assert "Reseña normal, sin agendas." in _sent(channel)


async def test_remind_storage_failure_still_delivers_the_message():
    """RESISTANCE: a dead reminders table must not take the turn down; the ack
    still reaches Discord and the marker still never leaks."""
    client = _client("Va, te lo agendo.[REMIND: +2h | algo]")
    client.memory.save_reminder = AsyncMock(side_effect=RuntimeError("pg down"))
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    sent = _sent(channel)
    assert "Va, te lo agendo." in sent
    assert "REMIND" not in sent


async def test_remind_with_unresolvable_time_still_delivers_and_strips():
    """RESISTANCE: a `<when>` we can't parse degrades to no row — never a raw
    marker in the channel, never a crash."""
    client = _client("Ahí te va.[REMIND: cuando salga la luna | algo]")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.save_reminder.assert_not_awaited()
    sent = _sent(channel)
    assert "Ahí te va." in sent
    assert "REMIND" not in sent


# --------------------------------------------------------------------------
# [REMEMBER:]
# --------------------------------------------------------------------------


async def test_remember_marker_persists_add_only_and_is_stripped():
    client = _client("Anotado.[REMEMBER: Alex es entrenadora canina]")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.add_remember_fact.assert_awaited_once_with("U1", "Alex es entrenadora canina")
    client.memory.save_facts.assert_not_awaited()  # never a snapshot replace

    sent = _sent(channel)
    assert "Anotado." in sent
    assert "REMEMBER" not in sent
    assert "REMEMBER" not in client.memory.store.call_args.args[4]


async def test_no_remember_marker_persists_nothing():
    """RESISTANCE: an ordinary reply never writes a fact."""
    client = _client("Solo una respuesta.")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.add_remember_fact.assert_not_awaited()


async def test_remember_storage_failure_still_delivers_the_message():
    """RESISTANCE: a failing fact write is best-effort — the turn survives."""
    client = _client("Anotado.[REMEMBER: algo durable]")
    client.memory.add_remember_fact = AsyncMock(side_effect=RuntimeError("pg down"))
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    sent = _sent(channel)
    assert "Anotado." in sent
    assert "REMEMBER" not in sent


async def test_both_markers_in_one_turn_are_each_handled():
    client = _client("Va.[REMIND: +1h | tomar el ARV][REMEMBER: toma ARV diario]")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.save_reminder.assert_awaited_once()
    client.memory.add_remember_fact.assert_awaited_once_with("U1", "toma ARV diario")
    sent = _sent(channel)
    assert "Va." in sent
    assert "REMIND" not in sent
    assert "REMEMBER" not in sent


async def test_marker_only_reply_sends_no_text_but_still_persists():
    """A turn that is ONLY a marker leaves nothing to say — but the intent lands."""
    client = _client("[REMEMBER: vive en GDL]")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.add_remember_fact.assert_awaited_once()
    channel.send.assert_not_called()
