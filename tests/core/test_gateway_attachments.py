"""Gateway image vision — siblings SEE the attachments of the summoning message.

P0 2026-07-07: Bernard sent an image asking Vultur "si ves la imagen???" and got
"no llegó imagen a mi mesa de disección" — the gateway built the runner turn from
`message.content` only. Mutator rule: positive (image → Anthropic blocks ride the
final user message into `agent_client.chat`) + resistance (no attachments → the
payload is byte-identical to the pre-fix string shape; oversized/unsupported →
clean rejection notice, turn still runs on the text).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from khimeras_shared.attachments import MAX_ATTACHMENT_SIZE
from persona_gateway.gateway import PersonaClient
from shared.personas import Persona


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _channel():
    channel = MagicMock()
    channel.id = 42
    channel.name = "general"
    channel.send = AsyncMock()
    channel.typing = MagicMock(return_value=_Typing())
    return channel


def _client() -> PersonaClient:
    persona = Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[])
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text="va", model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


def _attachment(filename: str, content_type: str, size: int, data: bytes = b"") -> MagicMock:
    att = MagicMock()
    att.filename = filename
    att.content_type = content_type
    att.size = size
    att.read = AsyncMock(return_value=data)
    att.url = f"https://cdn.discordapp.com/attachments/1/2/{filename}?ex=ffffffff&is=0&hm=abc"
    return att


def _message(content: str, attachments: list | None = None, *, voice: bool = False) -> MagicMock:
    msg = MagicMock()
    msg.channel = _channel()
    msg.author = SimpleNamespace(id=907, display_name="Bernard", bot=False)
    msg.guild = SimpleNamespace(id=1)
    msg.content = content
    msg.id = 777
    msg.attachments = attachments or []
    msg.flags = SimpleNamespace(voice=voice)
    return msg


def _last_user_content(client: PersonaClient):
    messages = client.agent_client.chat.await_args.args[1]
    return messages[-1]["content"]


async def test_image_blocks_reach_the_runner_call():
    client = _client()
    image = _attachment("foto.png", "image/png", 1000, data=b"fakepng")
    msg = _message("si ves la imagen???", [image])

    await client._handle(msg)

    client.agent_client.chat.assert_awaited_once()
    content = _last_user_content(client)
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "si ves la imagen???"}
    image_blocks = [b for b in content if b.get("type") == "image"]
    assert len(image_blocks) == 1
    # aire-server #50: the signed URL rides, never the bytes; AIRE fetches it.
    assert image_blocks[0]["source"] == {"type": "url", "url": image.url}
    image.read.assert_not_awaited()
    stored_text = client.memory.store.await_args_list[0].args[4]
    assert stored_text == "si ves la imagen???"


async def test_no_attachments_keeps_plain_string_payload():
    client = _client()
    msg = _message("qué opinas de Creep?")

    await client._handle(msg)

    client.agent_client.chat.assert_awaited_once()
    assert _last_user_content(client) == "qué opinas de Creep?"


async def test_oversized_non_image_rejected_cleanly_turn_still_runs():
    client = _client()
    heavy = _attachment("notas.txt", "text/plain", MAX_ATTACHMENT_SIZE + 1)
    msg = _message("lee esto", [heavy])

    await client._handle(msg)

    heavy.read.assert_not_awaited()
    sent = " ".join(str(c) for c in msg.channel.send.call_args_list)
    assert "muy pesado" in sent
    client.agent_client.chat.assert_awaited_once()
    assert _last_user_content(client) == "lee esto"


async def test_unsupported_type_rejected_cleanly_turn_still_runs():
    client = _client()
    video = _attachment("clip.mp4", "video/mp4", 1000)
    msg = _message("mira", [video])

    await client._handle(msg)

    sent = " ".join(str(c) for c in msg.channel.send.call_args_list)
    assert "No puedo leer" in sent
    client.agent_client.chat.assert_awaited_once()
    assert _last_user_content(client) == "mira"


async def test_image_only_message_still_runs_without_empty_text_block():
    client = _client()
    image = _attachment("meme.jpg", "image/jpeg", 500, data=b"jpg")
    msg = _message("", [image])

    await client._handle(msg)

    client.agent_client.chat.assert_awaited_once()
    content = _last_user_content(client)
    assert isinstance(content, list)
    assert [b["type"] for b in content] == ["image"]


async def test_bare_mention_without_attachments_stays_silent():
    client = _client()
    msg = _message("")

    await client._handle(msg)

    client.agent_client.chat.assert_not_awaited()
    client.memory.store.assert_not_awaited()


async def test_voice_attachment_is_not_transcribed_by_the_gateway():
    """RESISTANCE: susurro belongs to the HOST (2026-07-23). The @mention path
    keeps the text and leaves the audio alone — it never becomes a document
    block either, so the runner is not handed an .ogg it cannot read."""
    client = _client()
    clip = _attachment("voice.ogg", "audio/ogg", 500, data=b"ogg-bytes")
    msg = _message("escucha", [clip], voice=True)

    await client._handle(msg)

    client.agent_client.chat.assert_awaited_once()
    assert _last_user_content(client) == "escucha"
