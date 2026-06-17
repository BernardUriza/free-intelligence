"""Shared Azure TTS — the one place Insult and the gateway synthesize speech.

The capability is voice-agnostic: the caller owns the voice (onyx=Insult,
nova=ALICE, echo=Vultur). These pin the wiring (None when unconfigured) and that
synthesize forwards the caller's voice + deployment unchanged.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from khimeras_shared.tts import (
    build_azure_tts_client,
    should_auto_tts,
    split_for_tts,
    synthesize_azure_tts,
)


class TestShouldAutoTts:
    def test_long_reply_fires(self):
        assert should_auto_tts("x" * 1900, min_chars=1800, arbor_active=False) is True

    def test_short_reply_does_not_fire(self):
        assert should_auto_tts("x" * 1799, min_chars=1800, arbor_active=False) is False

    def test_zero_threshold_is_off(self):
        # RESISTANCE: 0 disables the feature even for a huge reply.
        assert should_auto_tts("x" * 9000, min_chars=0, arbor_active=False) is False

    def test_arbor_active_forbids_auto(self):
        # RESISTANCE: Arbor stays on-demand (voice.md) — never auto-fire.
        assert should_auto_tts("x" * 9000, min_chars=1800, arbor_active=True) is False


class TestSplitForTts:
    def test_empty_is_no_segments(self):
        assert split_for_tts("") == []

    def test_fits_in_one_segment(self):
        assert split_for_tts("hola", cap=4096) == ["hola"]

    def test_long_text_splits_and_preserves_everything(self):
        text = ("palabra " * 2000).strip()  # ~16k chars
        segs = split_for_tts(text, cap=4096)
        assert len(segs) > 1
        assert all(len(s) <= 4096 for s in segs)
        # No content lost (modulo whitespace at split boundaries).
        assert "".join(s.replace(" ", "") for s in segs) == text.replace(" ", "")


class TestBuildAzureTtsClient:
    def test_none_when_endpoint_missing(self):
        assert build_azure_tts_client(endpoint="", api_key="k") is None

    def test_none_when_key_missing(self):
        assert build_azure_tts_client(endpoint="https://x", api_key="") is None

    def test_builds_when_both_present(self):
        client = build_azure_tts_client(endpoint="https://x.openai.azure.com/", api_key="k")
        assert client is not None


class TestSynthesizeAzureTts:
    @pytest.mark.asyncio
    async def test_forwards_voice_and_deployment(self):
        client = MagicMock()
        client.audio.speech.create = AsyncMock(return_value=MagicMock(content=b"mp3bytes"))

        out = await synthesize_azure_tts(client, "hola", voice="echo", deployment="tts")

        assert out == b"mp3bytes"
        client.audio.speech.create.assert_awaited_once()
        kwargs = client.audio.speech.create.await_args.kwargs
        assert kwargs["voice"] == "echo"
        assert kwargs["model"] == "tts"
        assert kwargs["response_format"] == "mp3"

    @pytest.mark.asyncio
    async def test_caps_input_at_azure_limit(self):
        client = MagicMock()
        client.audio.speech.create = AsyncMock(return_value=MagicMock(content=b""))

        await synthesize_azure_tts(client, "x" * 5000, voice="onyx", deployment="tts")

        assert len(client.audio.speech.create.await_args.kwargs["input"]) == 4096
