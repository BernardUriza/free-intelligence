"""Invite turns transcribe the trigger message's voice notes.

The 2026-07-23 bug: Bernard's audios reached the persona MUTE. STT was wired
only into `_handle`, and `HOST_OWNS_RECEPTION=true` had demoted that path to
zero traffic — the host routed "[adjuntó: voice-message.ogg]" and nobody ever
called susurro. Same shape as the 2026-07-16 blind image.

Mutator rule: positive (voice note → transcript rides the instruction turn AND
is persisted as the user's words) + resistance (STT fault → the turn still
lands, never a dead invite).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from khimeras_shared.stt import SusurroSttClient
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
    return PersonaClient(
        persona,
        memory,
        agent_client,
        intents=discord.Intents.none(),
        stt_client=SusurroSttClient(base_url="https://sus.example", api_key="k"),
    )


def _invite_channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    channel.typing = MagicMock(return_value=_Typing())
    channel.fetch_message = AsyncMock()
    return channel


def _voice_trigger():
    attachment = MagicMock()
    attachment.content_type = "audio/ogg"
    attachment.filename = "voice-message.ogg"
    attachment.read = AsyncMock(return_value=b"OggS")
    trigger = MagicMock()
    trigger.id = 1527198401375113227
    trigger.content = ""
    trigger.attachments = [attachment]
    trigger.flags = MagicMock(voice=True)
    trigger.author = MagicMock(bot=False, id=907264175246569543, display_name="bernard2389")
    return trigger


async def _invite(client: PersonaClient, channel) -> None:
    with patch.object(client, "get_channel", return_value=channel):
        await client.respond_to_invite(
            channel_id="1489180895264116736",
            guild_id="G1",
            channel_name="general",
            reason="bernard2389: «[adjuntó: voice-message.ogg]»",
            invited_by="host_router",
            trigger_message_id="1527198401375113227",
        )
        await asyncio.sleep(0)


async def test_invite_voice_note_is_transcribed_into_the_turn():
    client = _client("Ya te oí, y sigue siendo mala idea.")
    channel = _invite_channel()
    channel.fetch_message.return_value = _voice_trigger()
    with patch(
        "persona_gateway.ingest.transcribe_voice_message",
        new=AsyncMock(return_value="quiero migrar el runner a otra región"),
    ):
        await _invite(client, channel)

    messages = client.agent_client.chat.await_args.args[1]
    instruction = messages[-1]["content"]
    assert isinstance(instruction, str)
    assert "quiero migrar el runner a otra región" in instruction

    user_rows = [c.args for c in client.memory.store.await_args_list if c.args[3] == "user"]
    assert user_rows, "el turno de voz del humano nunca se persistió"
    assert "quiero migrar el runner a otra región" in user_rows[0][4]


async def test_invite_stt_fault_degrades_to_text_only_turn():
    client = _client("Llego igual sin el audio.")
    channel = _invite_channel()
    channel.fetch_message.return_value = _voice_trigger()
    with patch(
        "persona_gateway.ingest.transcribe_voice_message",
        new=AsyncMock(side_effect=RuntimeError("susurro down")),
    ):
        await _invite(client, channel)

    messages = client.agent_client.chat.await_args.args[1]
    assert isinstance(messages[-1]["content"], str)
    assert "Nota de voz" not in messages[-1]["content"]
    sent = " ".join(str(c) for c in channel.send.call_args_list)
    assert "Llego igual sin el audio." in sent
