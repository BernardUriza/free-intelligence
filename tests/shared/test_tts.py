"""Shared Azure TTS — the one place Insult and the gateway synthesize speech.

The capability is voice-agnostic: the caller owns the voice (onyx=Insult,
nova=ALICE, echo=Vultur). These pin the wiring (None when unconfigured) and that
synthesize forwards the caller's voice + deployment unchanged.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from khimeras_shared.tts import build_azure_tts_client, synthesize_azure_tts


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
