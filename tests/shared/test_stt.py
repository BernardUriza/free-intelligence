"""Tests for persona_core.stt — voice-message STT via susurro.

The gateway exposes ``POST /v1/stt`` (Bearer auth, raw audio body, no forced
language — Whisper autodetects,
JSON ``{"success", "transcript", "engine"}``). These pin the unconfigured
posture, request shape, ``transcript`` parsing, and fail-safe error behavior.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from persona_core.stt import (
    STT_COLD_START_ATTEMPTS,
    STT_TIMEOUT_S,
    SttTranscript,
    build_susurro_stt_client,
    transcribe_voice_message,
)


def _mock_async_client(*, json_body: dict | None = None, raise_status: Exception | None = None):
    """Build an ``httpx.AsyncClient`` mock usable as an async context manager."""
    resp = MagicMock()
    resp.json = MagicMock(return_value=json_body or {})
    if raise_status is not None:
        resp.raise_for_status = MagicMock(side_effect=raise_status)
    else:
        resp.raise_for_status = MagicMock()

    post = AsyncMock(return_value=resp)
    http = MagicMock()
    http.post = post
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=http), post


class TestBuildSusurroSttClient:
    def test_none_when_base_url_missing(self):
        """STT stays disabled when susurro URL is missing."""
        assert build_susurro_stt_client(base_url="", api_key="k") is None

    def test_none_when_key_missing(self):
        """STT stays disabled when susurro key is missing."""
        assert build_susurro_stt_client(base_url="https://sus.example.com", api_key="") is None

    def test_strips_trailing_slash_from_base_url(self):
        """Base URL is normalized before request construction."""
        client = build_susurro_stt_client(base_url="https://sus.example.com/", api_key="k")

        assert client is not None
        assert client.base_url == "https://sus.example.com"


class TestTranscribeVoiceMessage:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_base_url(self):
        """Missing base URL returns None without an HTTP call."""
        result = await transcribe_voice_message(b"audio", base_url="", api_key="key")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_api_key(self):
        """Missing API key returns None without an HTTP call."""
        result = await transcribe_voice_message(b"audio", base_url="https://sus.example.com", api_key="")

        assert result is None

    @pytest.mark.asyncio
    async def test_successful_transcription_reads_transcript_field(self):
        """Successful STT posts raw bytes and reads transcript, not text."""
        factory, post = _mock_async_client(
            json_body={
                "success": True,
                "transcript": "hola que tal",
                "text": "campo equivocado",
                "engine": "azure-whisper",
            }
        )

        with patch("persona_core.stt.httpx.AsyncClient", factory):
            result = await transcribe_voice_message(
                b"fake-ogg-data",
                base_url="https://sus.example.com",
                api_key="sk-secret",
            )

        assert result == "hola que tal"
        assert isinstance(result, SttTranscript)
        assert result.engine == "azure-whisper"
        post.assert_awaited_once()
        url = post.await_args.args[0] if post.await_args.args else post.await_args.kwargs["url"]
        assert url == "https://sus.example.com/v1/stt"
        kwargs = post.await_args.kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer sk-secret"
        assert kwargs["headers"]["Content-Type"] == "audio/ogg"
        # No forced language: susurro lets Whisper autodetect. Forcing "es" came
        # back translated for audio in any other language (#74).
        assert kwargs["params"] == {}
        assert kwargs.get("content") == b"fake-ogg-data"

    @pytest.mark.asyncio
    async def test_language_travels_only_when_a_caller_asks_for_it(self):
        """A caller that fixes the language still sends it — what went is the default."""
        factory, post = _mock_async_client(json_body={"success": True, "transcript": "x"})

        with patch("persona_core.stt.httpx.AsyncClient", factory):
            await transcribe_voice_message(
                b"d",
                base_url="https://sus.example.com",
                api_key="k",
                language="en",
            )

        assert post.await_args.kwargs["params"] == {"language": "en"}

    @pytest.mark.asyncio
    async def test_passes_content_type_through(self):
        """Caller-provided content type is sent unchanged."""
        factory, post = _mock_async_client(json_body={"success": True, "transcript": "x"})

        with patch("persona_core.stt.httpx.AsyncClient", factory):
            await transcribe_voice_message(
                b"d",
                base_url="https://sus.example.com",
                api_key="k",
                content_type="audio/mpeg",
            )

        assert post.await_args.kwargs["headers"]["Content-Type"] == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_empty_transcript_returns_none(self):
        """Blank transcript is treated as no transcription."""
        factory, _post = _mock_async_client(json_body={"success": True, "transcript": "   "})

        with patch("persona_core.stt.httpx.AsyncClient", factory):
            result = await transcribe_voice_message(b"d", base_url="https://sus.example.com", api_key="k")

        assert result is None

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self):
        """HTTP errors fail safe to None."""
        factory, _post = _mock_async_client(raise_status=Exception("502"))

        with patch("persona_core.stt.httpx.AsyncClient", factory):
            result = await transcribe_voice_message(b"d", base_url="https://sus.example.com", api_key="k")

        assert result is None


class TestColdStartRetry:
    """Susurro runs scale-to-zero: a voice note is often the request that wakes
    it, and the boot outlives the read timeout. One attempt made transcription a
    coin flip against Azure's start time (3 of 10 notes lost on 2026-08-06)."""

    @staticmethod
    def _sequenced_client(effects: list):
        """AsyncClient mock whose POST replays `effects` in order — an exception
        raises, a dict answers as a transcript body."""
        post = AsyncMock()

        async def _post(*args, **kwargs):
            effect = effects[min(post.await_count - 1, len(effects) - 1)]
            if isinstance(effect, BaseException):
                raise effect
            resp = MagicMock()
            resp.json = MagicMock(return_value=effect)
            resp.raise_for_status = MagicMock()
            return resp

        post.side_effect = _post
        http = MagicMock()
        http.post = post
        http.__aenter__ = AsyncMock(return_value=http)
        http.__aexit__ = AsyncMock(return_value=False)
        return MagicMock(return_value=http), post

    @pytest.mark.asyncio
    async def test_cold_start_timeout_retries_and_transcribes(self):
        """THE bug: the first POST dies waiting on the container boot, the second
        hits a warm server. The note must survive, not land as 'no me entra'."""
        factory, post = self._sequenced_client(
            [
                httpx.ReadTimeout("timed out"),
                {"success": True, "transcript": "lo que dije en la nota", "engine": "azure-whisper"},
            ]
        )

        with patch("persona_core.stt.httpx.AsyncClient", factory), patch("asyncio.sleep", new=AsyncMock()):
            result = await transcribe_voice_message(b"ogg", base_url="https://sus.example.com", api_key="k")

        assert result == "lo que dije en la nota"
        assert post.await_count == 2

    @pytest.mark.asyncio
    async def test_gives_up_after_the_bounded_attempts(self):
        """RESISTANCE: a susurro that is genuinely down must not retry forever —
        the turn still has to reach the persona, degraded but alive."""
        factory, post = self._sequenced_client([httpx.ReadTimeout("timed out")])

        with patch("persona_core.stt.httpx.AsyncClient", factory), patch("asyncio.sleep", new=AsyncMock()):
            result = await transcribe_voice_message(b"ogg", base_url="https://sus.example.com", api_key="k")

        assert result is None
        assert post.await_count == STT_COLD_START_ATTEMPTS

    @pytest.mark.asyncio
    async def test_auth_rejection_is_not_retried(self):
        """RESISTANCE: a 401 is the server understanding us and saying no.
        Retrying only doubles the wait before the same answer."""
        denied = httpx.HTTPStatusError("401", request=MagicMock(), response=MagicMock(status_code=401))
        factory, post = self._sequenced_client([denied])

        with patch("persona_core.stt.httpx.AsyncClient", factory), patch("asyncio.sleep", new=AsyncMock()):
            result = await transcribe_voice_message(b"ogg", base_url="https://sus.example.com", api_key="k")

        assert result is None
        assert post.await_count == 1

    @pytest.mark.asyncio
    async def test_timeout_absorbs_a_container_boot(self):
        """The read timeout must outlast a Container Apps cold start. At 30s the
        boot landed ON the deadline (14:58:32 note, 14:58:55 boot, 14:59:02 death)."""
        assert STT_TIMEOUT_S >= 60.0
