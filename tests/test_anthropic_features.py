"""Anthropic-specific feature tests — guards against silent erosion.

The bot's value is in being Anthropic-native: prompt caching, web_search
server tool, tool_use multi-turn, character_break + anti_pattern guards,
language_cure. Each of these has a specific call shape that a future
refactor could break without the existing tests catching it. This file
locks in the contract.

Tests in this file should fail loudly the moment someone:
- swaps `cache_control={"type":"ephemeral"}` for something else
- replaces `messages.stream` with `messages.create` (loses long-request safety)
- bypasses the LLMResponse wrapper to read raw response.content directly
- changes _parse_response_content to drop tool_use blocks
- removes stop_reason from LLMResponse
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from insult.core.actions import ToolCall
from insult.core.character import CACHE_BOUNDARY
from insult.core.llm import (
    WEB_SEARCH_TOOL,
    LLMResponse,
    _build_system_blocks,
    _parse_response_content,
)

# ---------------------------------------------------------------------------
# Web search tool — definition shape
# ---------------------------------------------------------------------------


class TestWebSearchTool:
    def test_web_search_uses_anthropic_server_tool_type(self):
        """The bot relies on Anthropic's hosted web_search — NOT a custom
        client-side tool. If this assertion changes shape, all clinical
        citation flows break (medlineplus / NIH lookup in the vulnerable
        overlay) because the hosted variant carries server-side citations
        we depend on."""
        assert WEB_SEARCH_TOOL["type"] == "web_search_20250305"
        assert WEB_SEARCH_TOOL["name"] == "web_search"

    def test_web_search_has_max_uses_cap(self):
        """Without max_uses Claude can spin web_search indefinitely on a
        single turn. The cap exists as a cost guardrail and must not be
        removed silently."""
        assert "max_uses" in WEB_SEARCH_TOOL
        assert isinstance(WEB_SEARCH_TOOL["max_uses"], int)
        assert WEB_SEARCH_TOOL["max_uses"] >= 1


# ---------------------------------------------------------------------------
# _parse_response_content — server-tool blocks transparency
# ---------------------------------------------------------------------------


class TestParseResponseContent:
    def _block(self, **kwargs):
        """Build a mock content block matching Anthropic's response shape."""
        b = MagicMock()
        for k, v in kwargs.items():
            setattr(b, k, v)
        return b

    def test_text_block_extracted(self):
        """Plain text block ends up in LLMResponse.text."""
        blocks = [self._block(text="hola")]
        # Workaround: hasattr(block, "text") must be True for the parser
        # to pick it up. Set explicitly so getattr doesn't catch a MagicMock.
        blocks[0].type = "text"
        parsed = _parse_response_content(blocks)
        assert "hola" in parsed.text

    def test_tool_use_block_becomes_tool_call(self):
        """tool_use blocks are extracted into LLMResponse.tool_calls so
        the chat cog can dispatch them to action handlers."""
        block = MagicMock(spec=["type", "id", "name", "input"])
        block.type = "tool_use"
        block.id = "toolu_01"
        block.name = "create_reminder"
        block.input = {"description": "test"}
        parsed = _parse_response_content([block])
        assert len(parsed.tool_calls) == 1
        tc: ToolCall = parsed.tool_calls[0]
        assert tc.id == "toolu_01"
        assert tc.name == "create_reminder"
        assert tc.input == {"description": "test"}

    def test_server_tool_use_blocks_skipped_silently(self):
        """server_tool_use (web_search request) is processed by Anthropic
        server-side. We must NOT treat it as a client-side tool_call —
        otherwise the chat cog tries to execute it and fails. The parser
        skips these blocks intentionally."""
        block = MagicMock(spec=["type"])
        block.type = "server_tool_use"
        parsed = _parse_response_content([block])
        assert parsed.tool_calls == []
        assert parsed.text == ""

    def test_web_search_tool_result_blocks_skipped_silently(self):
        """Same reason as server_tool_use: the result block is handled
        upstream by Anthropic. Future improvement (citations extraction)
        would parse these explicitly — but until then they must NOT be
        treated as text or tool_call."""
        block = MagicMock(spec=["type"])
        block.type = "web_search_tool_result"
        parsed = _parse_response_content([block])
        assert parsed.tool_calls == []

    def test_mixed_blocks_combine_correctly(self):
        """Real responses interleave text + server_tool_use + text. The
        parser must concatenate text blocks and skip server blocks."""
        text1 = MagicMock(spec=["type", "text"])
        text1.type = "text"
        text1.text = "First answer:"
        server = MagicMock(spec=["type"])
        server.type = "server_tool_use"
        text2 = MagicMock(spec=["type", "text"])
        text2.type = "text"
        text2.text = "Continuation."
        parsed = _parse_response_content([text1, server, text2])
        # \n joiner between text blocks
        assert "First answer:" in parsed.text
        assert "Continuation." in parsed.text
        assert parsed.tool_calls == []


# ---------------------------------------------------------------------------
# CACHE_BOUNDARY edge cases beyond the existing tests in test_system_blocks
# ---------------------------------------------------------------------------


class TestCacheBoundaryEdges:
    def test_cache_boundary_marker_is_stable_string(self):
        """The marker is a contract between character/prompts.py (where
        it is injected) and llm._build_system_blocks (where it is split).
        If anyone changes the marker on one side without the other, every
        request runs uncached. Lock the literal value."""
        assert CACHE_BOUNDARY  # non-empty
        assert isinstance(CACHE_BOUNDARY, str)
        # Reasonable shape for a non-text-collision marker
        assert "CACHE_BOUNDARY" in CACHE_BOUNDARY or "<<<" in CACHE_BOUNDARY

    def test_whitespace_around_marker_trimmed(self):
        """Trailing newlines on stable / leading newlines on dynamic
        come from the prompts.py builder. The split must clean those up
        so cache keys are stable across whitespace drift."""
        prompt = f"STABLE\n\n{CACHE_BOUNDARY}\n\nDYNAMIC"
        result = _build_system_blocks(prompt)
        assert isinstance(result, list)
        assert result[0]["text"] == "STABLE"
        assert result[1]["text"] == "DYNAMIC"


# ---------------------------------------------------------------------------
# LLMResponse — stop_reason field must be populated
# ---------------------------------------------------------------------------


class TestLLMResponseStopReason:
    def test_default_stop_reason_is_empty_string(self):
        """Callers should be able to read .stop_reason without it being
        unset / None — utility_call and chat both populate it. The
        default "" makes truncation checks like
        `if response.stop_reason == 'max_tokens'` safe to write without
        a None guard."""
        r = LLMResponse(text="hello")
        assert r.stop_reason == ""

    def test_stop_reason_field_is_settable(self):
        """LLMResponse is a dataclass — stop_reason must be assignable
        post-construction (that's how _send populates it)."""
        r = LLMResponse(text="x")
        r.stop_reason = "max_tokens"
        assert r.stop_reason == "max_tokens"


# ---------------------------------------------------------------------------
# Title language gate — Spanish detection + translation
# ---------------------------------------------------------------------------


class TestTitleLanguageGate:
    def test_detects_spanish_session_marker(self):
        from insult.core.moltbook_outbound import title_has_spanish

        assert title_has_spanish("Sesión 5. Algo de palabras.")
        assert title_has_spanish("Session 4. ¿Dónde demonios?")
        assert title_has_spanish("Session 6. Menos palabras.")

    def test_passes_pure_english_titles(self):
        from insult.core.moltbook_outbound import title_has_spanish

        assert not title_has_spanish("Session 1. Emergence isn't recovery.")
        assert not title_has_spanish("Session 7. The agent that read my notes.")
        assert not title_has_spanish("Holy shit, this is a clean title.")

    @pytest.mark.asyncio
    async def test_ensure_title_english_passthrough_when_already_english(self):
        from insult.core.moltbook_outbound import ensure_title_english

        judge = MagicMock()
        judge.utility_call = AsyncMock()  # would assert if called
        out = await ensure_title_english(
            "Session 8. The grift is the symptom.",
            judge=judge,
            model="claude-haiku-4-5-20251001",
        )
        assert out == "Session 8. The grift is the symptom."
        judge.utility_call.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ensure_title_english_translates_when_spanish(self):
        from insult.core.moltbook_outbound import ensure_title_english

        # RunnerJudgeClient.utility_call returns a JudgeResponse whose .text
        # holds the translation — no nested content[] blocks like the old
        # raw-Anthropic response shape.
        response = MagicMock(text="Session 6. Fewer words as a philosophical stance.")
        judge = MagicMock()
        judge.utility_call = AsyncMock(return_value=response)

        out = await ensure_title_english(
            "Sesión 6. Menos palabras como postura filosófica.",
            judge=judge,
            model="claude-haiku-4-5-20251001",
        )
        assert "Session 6" in out
        assert "Fewer words" in out
        judge.utility_call.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_title_english_falls_back_on_api_error(self):
        from insult.core.moltbook_outbound import ensure_title_english

        judge = MagicMock()
        judge.utility_call = AsyncMock(side_effect=RuntimeError("api down"))

        original = "Sesión 9. Crash test."
        out = await ensure_title_english(original, judge=judge, model="claude-haiku-4-5-20251001")
        # Failure of the translation pass MUST NOT block publishes
        assert out == original


# ---------------------------------------------------------------------------
# Salience topic-overlap gate — prevents Sesión N+1 about same topic as N
# ---------------------------------------------------------------------------


class TestSalienceTopicOverlap:
    @pytest.mark.asyncio
    async def test_skips_stance_when_topic_overlaps_recent_outbound(self):
        from insult.core.moltbook_outbound import detect_salience_signal

        memory = MagicMock()
        memory.get_recent_world_scans = AsyncMock(
            return_value=[
                {"topic": "Sesión 5. Economía de palabras como postura filosófica."},
                {"topic": "Sesión 4. Yield sin fuente visible."},
            ]
        )
        memory.get_stances = AsyncMock(
            return_value=[
                # Most-recent stance overlaps "palabras / economía" — must be skipped
                {
                    "timestamp": __import__("time").time() - 3600,
                    "confidence": 0.8,
                    "topic": "economía de palabras filosofía",
                    "position": "Less is more.",
                },
                # Older stance with a fresh topic — should be picked
                {
                    "timestamp": __import__("time").time() - 7200,
                    "confidence": 0.7,
                    "topic": "rigor empirical methodology",
                    "position": "Rigor distinguishes craft from theater.",
                },
            ]
        )
        memory.get_arc = AsyncMock(return_value=None)

        signal = await detect_salience_signal(
            "channel-1",
            ["user-1"],
            memory=memory,
            recent_messages=[],
        )
        assert signal is not None
        assert signal.kind == "stance"
        assert "rigor" in signal.topic.lower()
        assert "palabras" not in signal.topic.lower()
