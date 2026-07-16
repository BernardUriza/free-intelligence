"""Invite turns carry the trigger message's attachments to the runner.

The 2026-07-16 bug: a host-routed turn about an image («que opinas» + foto)
reached Insult BLIND — respond_to_invite built its context from Postgres text
only, while the already-fetched trigger message's attachments were discarded.

Mutator rule: positive (image on the trigger → multimodal blocks ride the
instruction turn) + resistance (attachment processing fault → text-only turn
still delivers, never a dead invite).
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


def _client(reply_text: str) -> PersonaClient:
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[])
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply_text, model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


def _invite_channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    channel.typing = MagicMock(return_value=_Typing())
    channel.fetch_message = AsyncMock()
    return channel


def _image_trigger():
    trigger = MagicMock()
    attachment = MagicMock()
    attachment.content_type = "image/png"
    attachment.filename = "foto.png"
    trigger.attachments = [attachment]
    trigger.flags = MagicMock(voice=False)
    return trigger


_IMAGE_BLOCK = {
    "type": "image",
    "source": {"type": "base64", "media_type": "image/png", "data": "aGk="},
}


async def _invite(client: PersonaClient, channel) -> None:
    with patch.object(client, "get_channel", return_value=channel):
        await client.respond_to_invite(
            channel_id="1489180895264116736",
            guild_id="G1",
            channel_name="general",
            reason="bernard2389: «que opinas»",
            invited_by="host_router",
            trigger_message_id="1527198401375113227",
        )
        await asyncio.sleep(0)


async def test_invite_trigger_image_rides_the_instruction_turn():
    client = _client("Esa foto es un crimen de composición.")
    channel = _invite_channel()
    channel.fetch_message.return_value = _image_trigger()
    with patch(
        "persona_gateway.gateway.process_attachments",
        new=AsyncMock(return_value=([_IMAGE_BLOCK], [])),
    ):
        await _invite(client, channel)
    messages = client.agent_client.chat.await_args.args[1]
    content = messages[-1]["content"]
    assert isinstance(content, list)
    assert _IMAGE_BLOCK in content
    assert any(b.get("type") == "text" and "El turno es tuyo" in b["text"] for b in content)


async def test_invite_without_attachments_keeps_plain_text_instruction():
    client = _client("Respondo al hilo.")
    channel = _invite_channel()
    trigger = MagicMock()
    trigger.attachments = []
    channel.fetch_message.return_value = trigger
    await _invite(client, channel)
    messages = client.agent_client.chat.await_args.args[1]
    assert isinstance(messages[-1]["content"], str)


async def test_invite_attachment_fault_degrades_to_text_only_turn():
    client = _client("Llego igual sin la imagen.")
    channel = _invite_channel()
    channel.fetch_message.return_value = _image_trigger()
    with patch(
        "persona_gateway.gateway.process_attachments",
        new=AsyncMock(side_effect=RuntimeError("cdn down")),
    ):
        await _invite(client, channel)
    messages = client.agent_client.chat.await_args.args[1]
    assert isinstance(messages[-1]["content"], str)
    sent = " ".join(str(c) for c in channel.send.call_args_list)
    assert "Llego igual sin la imagen." in sent
