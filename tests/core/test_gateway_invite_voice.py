"""Invite turns carry the voice note's words — transcribed by the HOST.

2026-07-23, in two moves. First: Bernard's audios reached the persona MUTE —
STT was wired only into `_handle`, which `HOST_OWNS_RECEPTION=true` had demoted
to zero traffic, so the host routed "[adjuntó: voice-message.ogg]" and nobody
transcribed it. Then Bernard's call on the architecture: the host owns
reception, so the host owns susurro — nobody else talks to it. The gateway now
READS the transcript off the `/invite` wire.

Mutator rule: positive (the wire transcript reaches both the instruction the
model reads and the user row persisted to memory) + resistance (no transcript →
a plain text-only turn, and the gateway never calls susurro itself).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona

SPOKEN = "quiero migrar el runner a otra región"


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


def _voice_trigger():
    attachment = MagicMock()
    attachment.content_type = "audio/ogg"
    attachment.filename = "voice-message.ogg"
    trigger = MagicMock()
    trigger.id = 1527198401375113227
    trigger.content = ""
    trigger.attachments = [attachment]
    trigger.flags = MagicMock(voice=True)
    trigger.author = MagicMock(bot=False, id=907264175246569543, display_name="bernard2389")
    return trigger


async def _invite(client: PersonaClient, channel, transcript: str) -> None:
    with patch.object(client, "get_channel", return_value=channel):
        await client.respond_to_invite(
            channel_id="1489180895264116736",
            guild_id="G1",
            channel_name="general",
            reason="bernard2389: «[adjuntó: voice-message.ogg]»",
            invited_by="host_router",
            trigger_message_id="1527198401375113227",
            trigger_transcript=transcript,
        )
        await asyncio.sleep(0)


async def test_wire_transcript_reaches_the_turn_and_memory():
    client = _client("Ya te oí, y sigue siendo mala idea.")
    channel = _invite_channel()
    channel.fetch_message.return_value = _voice_trigger()
    await _invite(client, channel, SPOKEN)

    instruction = client.agent_client.chat.await_args.args[1][-1]["content"]
    assert isinstance(instruction, str)
    assert SPOKEN in instruction

    user_rows = [c.args for c in client.memory.store.await_args_list if c.args[3] == "user"]
    assert user_rows, "el turno de voz del humano nunca se persistió"
    assert SPOKEN in user_rows[0][4]


async def test_no_transcript_keeps_a_plain_turn():
    client = _client("Respondo al hilo.")
    channel = _invite_channel()
    channel.fetch_message.return_value = _voice_trigger()
    await _invite(client, channel, "")

    instruction = client.agent_client.chat.await_args.args[1][-1]["content"]
    assert "Nota de voz" not in instruction


async def test_gateway_never_calls_susurro_itself():
    """RESISTANCE: transcription belongs to the host. If the gateway ever grows
    its own STT call again, this fails."""
    client = _client("ok")
    channel = _invite_channel()
    channel.fetch_message.return_value = _voice_trigger()
    transcribe = AsyncMock(return_value="no debería llamarse")
    with patch("khimeras_shared.stt.transcribe_voice_message", new=transcribe):
        await _invite(client, channel, SPOKEN)
    transcribe.assert_not_awaited()
