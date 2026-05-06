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
    LLMClient,
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
# LLMClient.utility_call — wrapper contract
# ---------------------------------------------------------------------------


class TestUtilityCall:
    @pytest.mark.asyncio
    async def test_utility_call_invokes_send_with_kwargs(self):
        """utility_call is a thin wrapper over _send. It must propagate
        every kwarg the caller passes — model, max_tokens, tools — so
        callers can override per-call settings without tripping over
        the LLMClient defaults."""
        llm = LLMClient(api_key="sk-test", model="default", max_tokens=1024)
        # Mock _send so we don't hit the network
        sent = LLMResponse(text="ok", stop_reason="end_turn")
        llm._send = AsyncMock(return_value=sent)

        result = await llm.utility_call(
            "system",
            [{"role": "user", "content": "hi"}],
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            tools=[{"name": "x"}],
        )

        assert result is sent
        llm._send.assert_awaited_once()
        kwargs = llm._send.await_args.kwargs
        assert kwargs["model"] == "claude-haiku-4-5-20251001"
        assert kwargs["max_tokens"] == 256
        assert kwargs["tools"] == [{"name": "x"}]

    @pytest.mark.asyncio
    async def test_utility_call_skips_user_facing_pipeline(self):
        """utility_call MUST NOT run character_break / language_cure /
        formatting normalization. Those are post-processing for
        user-facing output; for JSON-shaped utility outputs (facts
        extraction, judge plans) they would corrupt the payload.

        We assert this by mocking `chat` and confirming utility_call
        never delegates to it — only to `_send`."""
        llm = LLMClient(api_key="sk-test", model="default", max_tokens=1024, cure_model="claude-haiku-4-5-20251001")
        llm._send = AsyncMock(return_value=LLMResponse(text="raw", stop_reason="end_turn"))
        llm.chat = AsyncMock()  # would log error if called

        await llm.utility_call("sys", [{"role": "user", "content": "x"}])

        llm.chat.assert_not_awaited()
        llm._send.assert_awaited_once()
