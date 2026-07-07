"""Gateway [REACT:] wiring — siblings react to the message that summoned them.

Mutator rule: positive (marker → reactions fired on the triggering message,
marker stripped from the visible text and the persisted row) + resistance
(no marker → text untouched, nothing fired; invite path with no triggering
message → marker still never leaks).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

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
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply_text, model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


async def _deliver(client: PersonaClient, channel, react_to=None) -> None:
    await client._run_and_deliver(
        channel=channel,
        channel_id="C1",
        user_id="U1",
        guild_id="G1",
        channel_name="general",
        messages=[{"role": "user", "content": "hola"}],
        react_to=react_to,
    )


async def test_marker_fires_reactions_and_strips_text():
    client = _client("Va, ese plano final corta.[REACT:🦅,🎞️]")
    channel = _channel()
    trigger = MagicMock()
    with patch("persona_gateway.gateway.add_reactions", new_callable=AsyncMock) as mock_add:
        await _deliver(client, channel, react_to=trigger)
        await asyncio.sleep(0)
    mock_add.assert_awaited_once_with(trigger, ["🦅", "🎞️"])
    sent = " ".join(str(c) for c in channel.send.call_args_list)
    assert "Va, ese plano final corta." in sent
    assert "REACT" not in sent
    stored_text = client.memory.store.call_args.args[4]
    assert "REACT" not in stored_text


async def test_reaction_only_reply_sends_no_text():
    client = _client("[REACT:👀]")
    channel = _channel()
    trigger = MagicMock()
    with patch("persona_gateway.gateway.add_reactions", new_callable=AsyncMock) as mock_add:
        await _deliver(client, channel, react_to=trigger)
        await asyncio.sleep(0)
    mock_add.assert_awaited_once_with(trigger, ["👀"])
    channel.send.assert_not_called()
    client.memory.store.assert_not_called()


async def test_no_marker_is_untouched_and_fires_nothing():
    client = _client("Reseña normal sin reacciones.")
    channel = _channel()
    with patch("persona_gateway.gateway.add_reactions", new_callable=AsyncMock) as mock_add:
        await _deliver(client, channel, react_to=MagicMock())
        await asyncio.sleep(0)
    mock_add.assert_not_awaited()
    channel.send.assert_awaited_once()
    assert "Reseña normal sin reacciones." in str(channel.send.call_args)


async def test_invite_path_never_leaks_marker_without_trigger_message():
    client = _client("Llego al hilo.[REACT:🦅]")
    channel = _channel()
    with patch("persona_gateway.gateway.add_reactions", new_callable=AsyncMock) as mock_add:
        await _deliver(client, channel, react_to=None)
        await asyncio.sleep(0)
    mock_add.assert_not_awaited()
    sent = " ".join(str(c) for c in channel.send.call_args_list)
    assert "Llego al hilo." in sent
    assert "REACT" not in sent
