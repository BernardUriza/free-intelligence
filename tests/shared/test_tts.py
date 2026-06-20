"""Shared susurro-gateway TTS — the one place Insult and the gateway synthesize speech.

The capability is voice-agnostic: the caller owns the voice (onyx=Insult,
nova=ALICE, echo=Vultur). ``build_susurro_tts_client`` pins the wiring (None when
unconfigured) and ``synthesize_susurro_tts`` POSTs the caller's voice unchanged to
the gateway's ``/v1/tts``, returning the raw MP3 bytes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khimeras_shared.tts import (
    DEFAULT_SUSURRO_URL,
    build_susurro_tts_client,
    should_auto_tts,
    split_for_tts,
    synthesize_susurro_tts,
)


def _mock_async_client(*, content: bytes = b"", raise_status: Exception | None = None):
    """Build a MagicMock standing in for ``httpx.AsyncClient(...)`` usable as an
    async context manager. Returns ``(client_factory, post_mock)``."""
    resp = MagicMock()
    resp.content = content
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


class TestBuildSusurroTtsClient:
    def test_none_when_base_url_missing(self):
        assert build_susurro_tts_client(base_url="", api_key="k") is None

    def test_none_when_key_missing(self):
        assert build_susurro_tts_client(base_url=DEFAULT_SUSURRO_URL, api_key="") is None

    def test_builds_when_both_present(self):
        client = build_susurro_tts_client(base_url=DEFAULT_SUSURRO_URL, api_key="k")
        assert client is not None
        assert client.api_key == "k"

    def test_strips_trailing_slash_from_base_url(self):
        # RESISTANCE: a trailing slash must not produce a double-slash URL.
        client = build_susurro_tts_client(base_url="https://sus.example.com/", api_key="k")
        assert client.base_url == "https://sus.example.com"


class TestSynthesizeSusurroTts:
    @pytest.mark.asyncio
    async def test_posts_to_v1_tts_with_bearer_and_returns_mp3_bytes(self):
        client = build_susurro_tts_client(base_url="https://sus.example.com", api_key="sk-secret")
        factory, post = _mock_async_client(content=b"mp3bytes")

        with patch("khimeras_shared.tts.httpx.AsyncClient", factory):
            out = await synthesize_susurro_tts(client, "hola", voice="onyx")

        assert out == b"mp3bytes"
        post.assert_awaited_once()
        url = post.await_args.args[0] if post.await_args.args else post.await_args.kwargs["url"]
        assert url == "https://sus.example.com/v1/tts"
        kwargs = post.await_args.kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer sk-secret"
        assert kwargs["json"] == {"input": "hola", "voice": "onyx", "format": "mp3"}

    @pytest.mark.asyncio
    async def test_forwards_caller_voice(self):
        client = build_susurro_tts_client(base_url="https://sus.example.com", api_key="k")
        factory, post = _mock_async_client(content=b"x")

        with patch("khimeras_shared.tts.httpx.AsyncClient", factory):
            await synthesize_susurro_tts(client, "hi", voice="echo")

        assert post.await_args.kwargs["json"]["voice"] == "echo"

    @pytest.mark.asyncio
    async def test_caps_input_at_gateway_limit(self):
        client = build_susurro_tts_client(base_url="https://sus.example.com", api_key="k")
        factory, post = _mock_async_client(content=b"")

        with patch("khimeras_shared.tts.httpx.AsyncClient", factory):
            await synthesize_susurro_tts(client, "x" * 5000, voice="onyx")

        assert len(post.await_args.kwargs["json"]["input"]) == 4096

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        # RESISTANCE: a gateway error is surfaced (caller logs + falls back),
        # never swallowed into a silent empty clip.
        client = build_susurro_tts_client(base_url="https://sus.example.com", api_key="k")
        factory, _post = _mock_async_client(raise_status=RuntimeError("502 from gateway"))

        with patch("khimeras_shared.tts.httpx.AsyncClient", factory), pytest.raises(RuntimeError):
            await synthesize_susurro_tts(client, "hola", voice="onyx")
