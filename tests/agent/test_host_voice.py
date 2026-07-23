"""The host transcribes voice notes BEFORE routing them.

2026-07-23: the router picked who answers a voice note from the filename alone
("[adjuntó: voice-message.ogg]") — it chose a persona without knowing whether
the audio was about cinema, a health scare or a landlord. The receiver now
transcribes first, so the routable text carries what was actually said.

Mutator rule: positive (transcript becomes the routable text) + resistance (a
dead susurro degrades to the old filename note instead of dropping the turn; a
bot's audio is never transcribed; no STT client → unchanged behaviour).
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from demux_ai.host_client import HostClient
from demux_ai.host_loop import HostDispatchLoop
from khimeras_shared.stt import SusurroSttClient


def _voice_message(*, is_bot: bool = False, content: str = "") -> SimpleNamespace:
    attachment = SimpleNamespace(
        content_type="audio/ogg",
        filename="voice-message.ogg",
        read=AsyncMock(return_value=b"OggS"),
    )
    return SimpleNamespace(
        id=999,
        content=content,
        channel=SimpleNamespace(id=111),
        author=SimpleNamespace(id=222, bot=is_bot, display_name="bern"),
        mentions=[],
        role_mentions=[],
        attachments=[attachment],
        flags=SimpleNamespace(voice=True),
    )


def _client(*, with_stt: bool = True) -> HostClient:
    loop = HostDispatchLoop(router=SimpleNamespace(route=MagicMock()))
    stt = SusurroSttClient(base_url="https://sus.example", api_key="k") if with_stt else None
    return HostClient(loop, intents=discord.Intents.none(), stt_client=stt)


async def test_transcript_becomes_the_routable_text():
    client = _client()
    with patch(
        "demux_ai.host_client.transcribe_voice_message",
        new=AsyncMock(return_value="oye, ¿qué opinas de Hereditary?"),
    ):
        await client.on_message(_voice_message())
    due = client.dispatch_loop.batcher.pop_due(now=time.time() + 10)
    assert due[0][1] == "oye, ¿qué opinas de Hereditary?\n[adjuntó: voice-message.ogg]"
    assert due[0][2] == "999"


async def test_stt_failure_degrades_to_the_filename_note():
    client = _client()
    with patch(
        "demux_ai.host_client.transcribe_voice_message",
        new=AsyncMock(side_effect=RuntimeError("susurro down")),
    ):
        await client.on_message(_voice_message())
    due = client.dispatch_loop.batcher.pop_due(now=time.time() + 10)
    assert due[0][1] == "[adjuntó: voice-message.ogg]"


async def test_no_stt_client_keeps_the_old_behaviour():
    client = _client(with_stt=False)
    await client.on_message(_voice_message())
    due = client.dispatch_loop.batcher.pop_due(now=time.time() + 10)
    assert due[0][1] == "[adjuntó: voice-message.ogg]"


async def test_a_bots_audio_is_never_transcribed():
    """RESISTANCE: bot output is dropped anyway — don't spend susurro on it."""
    client = _client()
    transcribe = AsyncMock(return_value="soy otro bot")
    with patch("demux_ai.host_client.transcribe_voice_message", new=transcribe):
        await client.on_message(_voice_message(is_bot=True))
    transcribe.assert_not_awaited()
    assert client.dispatch_loop.batcher.pending_keys() == []


async def test_text_plus_voice_keeps_both():
    client = _client()
    with patch(
        "demux_ai.host_client.transcribe_voice_message",
        new=AsyncMock(return_value="y esto lo dije hablando"),
    ):
        await client.on_message(_voice_message(content="mira esto"))
    due = client.dispatch_loop.batcher.pop_due(now=time.time() + 10)
    assert due[0][1] == "mira esto\ny esto lo dije hablando\n[adjuntó: voice-message.ogg]"
