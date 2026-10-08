"""Gateway [REMIND_CANCEL:] wiring — the marker cancels and never leaks.

Same contract family as test_gateway_reminds_remembers: positive (marker →
stripped from the visible text AND the cancel fired with the emitting persona's
id + the asking user's id) + resistance (no marker → nothing cancelled; a dead
reminders table → the message still sends, the marker still never leaks) + the
ordering guarantee (cancel routes BEFORE create, so a same-turn [REMIND:] can
never be eaten by its own cancel criterion).
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
    memory.cancel_pending_reminders = AsyncMock(return_value=[{"id": 7, "description": "sacar la ropa"}])
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
        messages=[{"role": "user", "content": "ya no me recuerdes lo de la ropa"}],
        react_to=MagicMock(),
    )


def _sent(channel) -> str:
    return " ".join(str(c) for c in channel.send.call_args_list)


async def test_cancel_marker_cancels_and_is_stripped():
    client = _client("Hecho, olvidado.[REMIND_CANCEL: la ropa]")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.cancel_pending_reminders.assert_awaited_once_with(
        created_by="U1",
        persona_id="vultur",
        criterion="la ropa",
    )
    sent = _sent(channel)
    assert "Hecho, olvidado." in sent
    assert "REMIND_CANCEL" not in sent
    assert "REMIND_CANCEL" not in client.memory.store.call_args.args[4]


async def test_no_cancel_marker_cancels_nothing():
    """RESISTANCE: an ordinary reply never retires a row."""
    client = _client("Reseña normal, sin bajas.")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.cancel_pending_reminders.assert_not_awaited()
    assert "Reseña normal, sin bajas." in _sent(channel)


async def test_cancel_storage_failure_still_delivers_the_message():
    """RESISTANCE: a dead reminders table must not take the turn down; the ack
    still reaches Discord and the marker still never leaks."""
    client = _client("Hecho.[REMIND_CANCEL: la ropa]")
    client.memory.cancel_pending_reminders = AsyncMock(side_effect=RuntimeError("pg down"))
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    sent = _sent(channel)
    assert "Hecho." in sent
    assert "REMIND_CANCEL" not in sent


async def test_multiple_cancel_markers_each_fire():
    client = _client("Fuera ambos.[REMIND_CANCEL: la ropa][REMIND_CANCEL: el arv]")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    criteria = [c.kwargs["criterion"] for c in client.memory.cancel_pending_reminders.await_args_list]
    assert criteria == ["la ropa", "el arv"]
    assert "REMIND_CANCEL" not in _sent(channel)


async def test_cancel_routes_before_a_same_turn_remind():
    """ORDER IS THE CONTRACT: 'cancela lo de la ropa y ahora recuérdame la ropa
    a las 9' — the cancel must only see pre-existing rows, so it fires BEFORE
    save_reminder persists the new one."""
    client = _client("Va.[REMIND_CANCEL: la ropa][REMIND: +2h | sacar la ropa a las 9]")
    channel = _channel()
    order = MagicMock()
    order.attach_mock(client.memory.cancel_pending_reminders, "cancel")
    order.attach_mock(client.memory.save_reminder, "save")

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.cancel_pending_reminders.assert_awaited_once()
    client.memory.save_reminder.assert_awaited_once()
    call_names = [name for name, _args, _kwargs in order.mock_calls if name in ("cancel", "save")]
    assert call_names == ["cancel", "save"]
    sent = _sent(channel)
    assert "REMIND" not in sent


async def test_cancel_only_reply_sends_no_text_but_still_cancels():
    """A turn that is ONLY the marker leaves nothing to say — the intent lands."""
    client = _client("[REMIND_CANCEL: la ropa]")
    channel = _channel()

    await _deliver(client, channel)
    await asyncio.sleep(0)

    client.memory.cancel_pending_reminders.assert_awaited_once()
    channel.send.assert_not_called()
