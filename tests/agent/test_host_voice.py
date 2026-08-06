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
import pytest

from demux_ai.batch import DEFAULT_WINDOW_SECONDS
from demux_ai.host_client import HostClient
from demux_ai.host_loop import HostDispatchLoop
from khimeras_shared.stt import WAKE_ETA_SECONDS, SusurroSttClient


@pytest.fixture(autouse=True)
def _susurro_awake():
    """Default every test to a WARM susurro so the wake path stays opt-in.

    Without this the suite would drive the real probe against a fake host and
    sit through the wake deadline — and, worse, the cold path would ride along
    invisibly in tests that are about something else.
    """
    with patch("demux_ai.host_client.susurro_is_awake", new=AsyncMock(return_value=True)):
        yield


def _voice_message(*, is_bot: bool = False, content: str = "") -> SimpleNamespace:
    attachment = SimpleNamespace(
        content_type="audio/ogg",
        filename="voice-message.ogg",
        read=AsyncMock(return_value=b"OggS"),
    )
    return SimpleNamespace(
        id=999,
        content=content,
        channel=SimpleNamespace(id=111, send=AsyncMock()),
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
    due = client.dispatch_loop.batcher.pop_due(now=time.time() + DEFAULT_WINDOW_SECONDS + 1)
    assert due[0][1] == "oye, ¿qué opinas de Hereditary?\n[adjuntó: voice-message.ogg]"
    assert due[0][2] == "999"


async def test_stt_failure_degrades_to_the_filename_note():
    client = _client()
    with patch(
        "demux_ai.host_client.transcribe_voice_message",
        new=AsyncMock(side_effect=RuntimeError("susurro down")),
    ):
        await client.on_message(_voice_message())
    due = client.dispatch_loop.batcher.pop_due(now=time.time() + DEFAULT_WINDOW_SECONDS + 1)
    assert due[0][1] == "[adjuntó: voice-message.ogg]"


async def test_no_stt_client_keeps_the_old_behaviour():
    client = _client(with_stt=False)
    await client.on_message(_voice_message())
    due = client.dispatch_loop.batcher.pop_due(now=time.time() + DEFAULT_WINDOW_SECONDS + 1)
    assert due[0][1] == "[adjuntó: voice-message.ogg]"


async def test_a_bots_audio_is_never_transcribed():
    """RESISTANCE: bot output is dropped anyway — don't spend susurro on it."""
    client = _client()
    transcribe = AsyncMock(return_value="soy otro bot")
    with patch("demux_ai.host_client.transcribe_voice_message", new=transcribe):
        await client.on_message(_voice_message(is_bot=True))
    transcribe.assert_not_awaited()
    assert client.dispatch_loop.batcher.pending_keys() == []


async def test_the_host_echoes_the_transcript_to_the_channel():
    """Restored from pre-purga batch.py: a voice note is opaque unless you hit
    play, so the words get published as a sidecar."""
    msg = _voice_message()
    client = _client()
    with patch(
        "demux_ai.host_client.transcribe_voice_message",
        new=AsyncMock(return_value="abre la puerta"),
    ):
        await client.on_message(msg)
    msg.channel.send.assert_awaited_once_with(">>> 🔊 **bern dijo:**\nabre la puerta\n🎙️")


async def test_a_long_transcript_is_truncated_not_split():
    msg = _voice_message()
    client = _client()
    with patch(
        "demux_ai.host_client.transcribe_voice_message",
        new=AsyncMock(return_value="pa " * 900),
    ):
        await client.on_message(msg)
    sent = msg.channel.send.await_args.args[0]
    assert len(sent) <= 1990
    assert sent.endswith("…")


async def test_no_transcript_means_no_echo():
    """RESISTANCE: a text message (or a dead susurro) must not spam the channel."""
    msg = _voice_message()
    client = _client()
    with patch(
        "demux_ai.host_client.transcribe_voice_message",
        new=AsyncMock(side_effect=RuntimeError("susurro down")),
    ):
        await client.on_message(msg)
    msg.channel.send.assert_not_awaited()


async def test_a_failing_echo_never_blocks_the_routing():
    """RESISTANCE: the echo is a sidecar — if the send 403s, the turn still routes."""
    msg = _voice_message()
    msg.channel.send = AsyncMock(side_effect=RuntimeError("missing permissions"))
    client = _client()
    with patch(
        "demux_ai.host_client.transcribe_voice_message",
        new=AsyncMock(return_value="sigo llegando"),
    ):
        await client.on_message(msg)
    due = client.dispatch_loop.batcher.pop_due(now=time.time() + DEFAULT_WINDOW_SECONDS + 1)
    assert due[0][3] == "sigo llegando"


async def test_text_plus_voice_keeps_both():
    client = _client()
    with patch(
        "demux_ai.host_client.transcribe_voice_message",
        new=AsyncMock(return_value="y esto lo dije hablando"),
    ):
        await client.on_message(_voice_message(content="mira esto"))
    due = client.dispatch_loop.batcher.pop_due(now=time.time() + DEFAULT_WINDOW_SECONDS + 1)
    assert due[0][1] == "mira esto\ny esto lo dije hablando\n[adjuntó: voice-message.ogg]"


class TestSleepingSusurroIsAnnounced:
    """Susurro stays scale-to-zero on purpose (asleep it costs nothing), so a
    voice note is routinely the request that boots it — ~30s of silence during
    which the user has no idea anything is happening. Bernard's ask: say it out
    loud, give the estimate, prove the pipeline with a hello-world clip, then
    deliver his audio."""

    async def test_a_warm_susurro_announces_nothing(self):
        """RESISTANCE: the common case must stay silent. Announcing a wake that
        isn't happening turns every voice note into channel noise."""
        msg = _voice_message()
        client = _client()
        with (
            patch("demux_ai.host_client.wake_susurro", new=AsyncMock(return_value=True)) as wake,
            patch("demux_ai.host_client.transcribe_voice_message", new=AsyncMock(return_value="ya estaba despierto")),
        ):
            await client.on_message(msg)
        wake.assert_not_awaited()
        assert msg.channel.send.await_count == 1
        assert "dijo:" in msg.channel.send.await_args.args[0]

    async def test_a_sleeping_susurro_warns_with_an_eta_then_delivers(self):
        """THE ask: tell him it's asleep and how long, wake it, then hand over
        the transcript — instead of 30 silent seconds ending in 'no me entra'."""
        msg = _voice_message()
        client = _client()
        with (
            patch("demux_ai.host_client.susurro_is_awake", new=AsyncMock(return_value=False)),
            patch("demux_ai.host_client.wake_susurro", new=AsyncMock(return_value=True)) as wake,
            patch("demux_ai.host_client.transcribe_voice_message", new=AsyncMock(return_value="lo que dije dormido")),
        ):
            await client.on_message(msg)

        wake.assert_awaited_once()
        notice, echo = (call.args[0] for call in msg.channel.send.await_args_list)
        assert "dormido" in notice
        assert str(WAKE_ETA_SECONDS) in notice
        assert echo == ">>> 🔊 **bern dijo:**\nlo que dije dormido\n🎙️"

    async def test_the_wake_happens_before_the_transcription(self):
        """The hello-world probe exists to run FIRST: transcribing before the
        pipeline is confirmed is what made the note a coin flip."""
        order: list[str] = []

        async def _wake(**_kwargs):
            order.append("wake")
            return True

        async def _transcribe(*_args, **_kwargs):
            order.append("transcribe")
            return "por fin"

        client = _client()
        with (
            patch("demux_ai.host_client.susurro_is_awake", new=AsyncMock(return_value=False)),
            patch("demux_ai.host_client.wake_susurro", new=_wake),
            patch("demux_ai.host_client.transcribe_voice_message", new=_transcribe),
        ):
            await client.on_message(_voice_message())

        assert order == ["wake", "transcribe"]

    async def test_a_failed_wake_says_so_and_still_tries(self):
        """RESISTANCE: a wake that never lands must not swallow the audio — the
        attempt may still succeed, and silence is the failure we're killing."""
        msg = _voice_message()
        client = _client()
        transcribe = AsyncMock(return_value="pasé de todos modos")
        with (
            patch("demux_ai.host_client.susurro_is_awake", new=AsyncMock(return_value=False)),
            patch("demux_ai.host_client.wake_susurro", new=AsyncMock(return_value=False)),
            patch("demux_ai.host_client.transcribe_voice_message", new=transcribe),
        ):
            await client.on_message(msg)

        transcribe.assert_awaited_once()
        notices = [call.args[0] for call in msg.channel.send.await_args_list]
        assert any("No logré despertar" in n for n in notices)
        assert notices[-1].endswith("🎙️")

    async def test_a_text_message_never_probes_susurro(self):
        """RESISTANCE: no audio, no probe. A chatty channel must not poll the
        gateway (and keep it awake) on every ordinary message."""
        msg = _voice_message()
        msg.attachments = []
        client = _client()
        with patch("demux_ai.host_client.susurro_is_awake", new=AsyncMock(return_value=False)) as probe:
            await client.on_message(msg)
        probe.assert_not_awaited()

    async def test_a_non_audio_attachment_never_probes_susurro(self):
        """RESISTANCE: an image is not a voice note — the document lane must not
        pay for a susurro boot."""
        msg = _voice_message()
        msg.attachments = [SimpleNamespace(content_type="image/png", filename="foto.png", read=AsyncMock())]
        msg.flags = SimpleNamespace(voice=False)
        client = _client()
        with patch("demux_ai.host_client.susurro_is_awake", new=AsyncMock(return_value=False)) as probe:
            await client.on_message(msg)
        probe.assert_not_awaited()
