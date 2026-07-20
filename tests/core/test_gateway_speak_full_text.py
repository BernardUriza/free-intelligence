"""🔊 habla el TURNO completo, nunca un chunk con el version tag leído en voz alta.

Regresión latente post-purga (checklist c0-r7): `on_raw_reaction_add` hablaba
`message.content` — en una respuesta multi-chunk eso es UN pedazo, y el último
pedazo carga el `-# ᵛX·Y·Z` que susurro leería en voz alta. El fix: delivery
registra message_id → texto completo sin tag; el 🔊 hace lookup y su fallback
(mensaje de un deploy viejo ya evictado) le arranca cualquier version tag.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest

from persona_gateway import delivery
from persona_gateway.delivery import (
    full_text_for,
    send_chunked,
    strip_version_tag,
)
from persona_gateway.gateway import PersonaClient
from shared.personas import Persona


@pytest.fixture(autouse=True)
def _clean_registry():
    delivery._full_texts.clear()
    yield
    delivery._full_texts.clear()


def _channel_with_ids(start: int = 100):
    channel = MagicMock()
    counter = {"next": start}

    async def _send(piece):
        message = MagicMock()
        message.id = counter["next"]
        counter["next"] += 1
        return message

    channel.send = AsyncMock(side_effect=_send)
    return channel


async def test_send_chunked_registers_every_piece_to_the_full_text():
    long_text = "\n".join(f"párrafo {i} " + "x" * 180 for i in range(30))
    channel = _channel_with_ids()
    sent = await send_chunked(channel, long_text)
    assert len(sent) > 1
    for message in sent:
        assert full_text_for(message.id) == long_text.strip()


async def test_registered_full_text_carries_no_version_tag():
    channel = _channel_with_ids()
    sent = await send_chunked(channel, "respuesta corta")
    delivered = channel.send.call_args_list[0].args[0]
    assert "-# ᵛ" in delivered
    assert "-# ᵛ" not in full_text_for(sent[0].id)


async def test_registry_evicts_oldest_beyond_cap():
    channel = _channel_with_ids()
    for i in range(delivery._FULL_TEXT_CAP + 5):
        await send_chunked(channel, f"texto {i}")
    assert full_text_for(100) is None
    assert len(delivery._full_texts) == delivery._FULL_TEXT_CAP


def test_strip_version_tag_removes_current_and_old_tags():
    assert strip_version_tag("hola\n-# ᵛ⁴·²⁶·⁰") == "hola"
    assert strip_version_tag("hola\n-# ᵛ³·⁹·²⁵") == "hola"
    assert strip_version_tag("hola sin tag") == "hola sin tag"


def test_strip_version_tag_resists_tag_lookalike_mid_text():
    text = "el deploy\n-# ᵛ⁴·²⁶·⁰ se rompió\ny siguió el párrafo"
    assert strip_version_tag(text) == text


def _persona_client() -> PersonaClient:
    persona = Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    agent_client = MagicMock()
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


def _speak_setup(client: PersonaClient, *, bot_id: int, message):
    client._voice = MagicMock(enabled=True)
    client._voice.speak = AsyncMock()
    channel = MagicMock()
    channel.fetch_message = AsyncMock(return_value=message)
    client.get_channel = MagicMock(return_value=channel)
    return client._voice.speak, channel


def _payload(*, message_id: int, emoji: str = "🔊", user_id: int = 555):
    return SimpleNamespace(emoji=emoji, user_id=user_id, channel_id=42, message_id=message_id)


async def test_speaker_reads_the_full_turn_not_the_chunk():
    channel = _channel_with_ids()
    full = "\n".join(f"bloque {i} " + "y" * 180 for i in range(30))
    sent = await send_chunked(channel, full)
    last = sent[-1]

    client = _persona_client()
    bot_user = SimpleNamespace(id=999)
    message = MagicMock()
    message.id = last.id
    message.author = SimpleNamespace(id=999)
    message.content = channel.send.call_args_list[-1].args[0]
    speak, _ = _speak_setup(client, bot_id=999, message=message)

    with patch.object(PersonaClient, "user", new_callable=PropertyMock, return_value=bot_user):
        await client.on_raw_reaction_add(_payload(message_id=last.id))

    speak.assert_awaited_once()
    spoken = speak.await_args.args[1]
    assert spoken == full.strip()
    assert "-# ᵛ" not in spoken


async def test_speaker_falls_back_to_untagged_content_when_unregistered():
    client = _persona_client()
    bot_user = SimpleNamespace(id=999)
    message = MagicMock()
    message.id = 12345
    message.author = SimpleNamespace(id=999)
    message.content = "respuesta de un deploy viejo\n-# ᵛ³·⁹·²⁵"
    speak, _ = _speak_setup(client, bot_id=999, message=message)

    with patch.object(PersonaClient, "user", new_callable=PropertyMock, return_value=bot_user):
        await client.on_raw_reaction_add(_payload(message_id=12345))

    speak.assert_awaited_once()
    assert speak.await_args.args[1] == "respuesta de un deploy viejo"


async def test_wrong_emoji_never_speaks():
    client = _persona_client()
    bot_user = SimpleNamespace(id=999)
    message = MagicMock()
    message.author = SimpleNamespace(id=999)
    speak, _ = _speak_setup(client, bot_id=999, message=message)

    with patch.object(PersonaClient, "user", new_callable=PropertyMock, return_value=bot_user):
        await client.on_raw_reaction_add(_payload(message_id=1, emoji="🎬"))

    speak.assert_not_awaited()


async def test_foreign_message_never_speaks():
    client = _persona_client()
    bot_user = SimpleNamespace(id=999)
    message = MagicMock()
    message.id = 777
    message.author = SimpleNamespace(id=111)
    message.content = "mensaje de otro"
    speak, _ = _speak_setup(client, bot_id=999, message=message)

    with patch.object(PersonaClient, "user", new_callable=PropertyMock, return_value=bot_user):
        await client.on_raw_reaction_add(_payload(message_id=777))

    speak.assert_not_awaited()
