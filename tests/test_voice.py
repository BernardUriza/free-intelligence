"""Tests for insult.cogs.voice.resolve_full_response.

The live regression this covers: a user reacted 🔊 on a bot message that
was one chunk of a ~5000-char response split by delivery.py. TTS spoke
only 1989 chars (≈ 2:05 of audio) and cut off. resolve_full_response
pulls the full pre-chunk text from memory so TTS speaks the whole thing.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from insult.cogs.voice import _VERSION_TAG_RE, build_arbor_tts_payload, pick_tts_voice, resolve_full_response


class TestPickTtsVoice:
    """The VoiceCog speaks ANY 🔊'd message. ALICE must sound female; Insult
    and humans stay onyx. Regression for the 'ALICE habla con voz de hombre'
    bug (2026-05-20)."""

    @staticmethod
    def _settings(alice_id="1503983124982534284"):
        return SimpleNamespace(tts_voice="onyx", alice_tts_voice="nova", alice_bot_user_id=alice_id)

    def test_alice_message_gets_female_voice(self):
        voice, is_alice = pick_tts_voice(1503983124982534284, self._settings())
        assert voice == "nova"
        assert is_alice is True

    def test_alice_id_as_string_also_matches(self):
        """message.author.id is an int; the setting is a str. Comparison must
        be type-agnostic."""
        voice, is_alice = pick_tts_voice("1503983124982534284", self._settings())
        assert voice == "nova"
        assert is_alice is True

    def test_insult_or_human_keeps_default_voice(self):
        voice, is_alice = pick_tts_voice(907264175246569543, self._settings())
        assert voice == "onyx"
        assert is_alice is False

    def test_empty_alice_id_disables_feature(self):
        """No configured ALICE id → everything uses the default voice."""
        voice, is_alice = pick_tts_voice(1503983124982534284, self._settings(alice_id=""))
        assert voice == "onyx"
        assert is_alice is False


class TestArborTtsPayload:
    def test_uses_configured_voice_and_mp3(self):
        settings = SimpleNamespace(arbor_tts_voice="arbor")
        payload = build_arbor_tts_payload("hola", settings)
        assert payload == {"text": "hola", "voice": "arbor", "format": "mp3"}

    def test_limits_text_to_service_boundary(self):
        settings = SimpleNamespace(arbor_tts_voice="arbor")
        payload = build_arbor_tts_payload("x" * 5000, settings)
        assert len(payload["text"]) == 4096


class TestResolveFullResponse:
    @pytest.fixture
    def memory_with(self):
        """Factory: build a mock memory whose get_recent returns the given rows."""

        def _build(rows: list[dict]):
            mem = AsyncMock()
            mem.get_recent = AsyncMock(return_value=rows)
            return mem

        return _build

    async def test_returns_full_text_when_chunk_substring_matches(self, memory_with):
        full = "A" * 1800 + " — frontera — " + "B" * 1800 + " — final — " + "C" * 1300
        chunk = "A" * 1800 + " — frontera — " + "B" * 200  # chunked slice
        mem = memory_with([{"role": "assistant", "content": full}])
        result = await resolve_full_response(mem, "c1", chunk)
        assert result == full

    async def test_strips_version_tag_before_lookup(self, memory_with):
        """The final chunk carries a '\\n-# ᵛ³·⁵·¹³' suffix. It must not
        poison the substring match against memory."""
        full = "Respuesta completa sin tag de versión."
        chunk_with_tag = "Respuesta completa sin tag de versión.\n-# ᵛ³·⁵·¹³"
        mem = memory_with([{"role": "assistant", "content": full}])
        result = await resolve_full_response(mem, "c1", chunk_with_tag)
        assert result == full

    async def test_returns_none_when_no_assistant_match(self, memory_with):
        mem = memory_with(
            [
                {"role": "user", "content": "hola"},
                {"role": "assistant", "content": "otra respuesta distinta"},
            ]
        )
        result = await resolve_full_response(mem, "c1", "texto que nadie tiene")
        assert result is None

    async def test_picks_most_recent_match_when_duplicated(self, memory_with):
        """If the same substring appears in two assistant entries, return
        the NEWEST (last in chronological order from get_recent)."""
        mem = memory_with(
            [
                {"role": "assistant", "content": "Respuesta vieja con ancla compartida."},
                {"role": "user", "content": "pregunta intermedia"},
                {"role": "assistant", "content": "Respuesta NUEVA con ancla compartida."},
            ]
        )
        result = await resolve_full_response(mem, "c1", "ancla compartida")
        assert result == "Respuesta NUEVA con ancla compartida."

    async def test_skips_user_rows_even_if_they_contain_the_text(self, memory_with):
        mem = memory_with(
            [
                {"role": "user", "content": "el chunk exacto aquí"},
                {"role": "assistant", "content": "otra cosa totalmente"},
            ]
        )
        result = await resolve_full_response(mem, "c1", "el chunk exacto aquí")
        assert result is None

    async def test_returns_none_on_memory_failure(self, memory_with):
        mem = AsyncMock()
        mem.get_recent = AsyncMock(side_effect=RuntimeError("db down"))
        result = await resolve_full_response(mem, "c1", "whatever")
        assert result is None

    async def test_empty_chunk_after_strip_returns_none(self, memory_with):
        mem = memory_with([{"role": "assistant", "content": "no importa"}])
        result = await resolve_full_response(mem, "c1", "\n-# ᵛ³·⁵·¹³")
        assert result is None


class TestVersionTagRegex:
    """The version tag strip is load-bearing — a loose match would steal real text."""

    def test_strips_suffix(self):
        text = "Contenido real.\n-# ᵛ³·⁵·¹³"
        assert _VERSION_TAG_RE.sub("", text) == "Contenido real."

    def test_does_not_strip_non_tag_lines(self):
        """Plain Discord spoiler/formatting or any \\n-# that is NOT our tag
        must be preserved. Our marker specifically starts with 'ᵛ'."""
        text = "Line one.\n-# Normal footer without marker.\nLine two."
        assert _VERSION_TAG_RE.sub("", text) == text

    def test_handles_trailing_whitespace_via_caller_strip(self):
        """The regex removes the tag line up to the final newline; the
        caller does .strip() afterwards. Contract verified end-to-end."""
        text = "Texto.\n-# ᵛ³·⁵·¹²   \n"
        assert _VERSION_TAG_RE.sub("", text).strip() == "Texto."
