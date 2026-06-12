"""Anthropic Messages API request/response shaping.

- `LLMResponse`: the structured shape that callers consume (text +
  tool calls + model_used + stop_reason).
- `WEB_SEARCH_TOOL`: the native server-side search tool definition
  passed on every turn. See note below for why source-quality
  steering for vulnerable users does NOT live as a second tool.
- `_build_system_blocks`: splits the system prompt on the
  CACHE_BOUNDARY marker into a cacheable stable prefix +
  dynamic tail so prompt caching attaches to the persona block.
- `_parse_response_content`: extracts text blocks + tool_use blocks
  from a Messages API response, skipping server-side blocks
  (web_search server_tool_use / web_search_tool_result).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from personas.insult.core.actions import ToolCall
from personas.insult.core.character import CACHE_BOUNDARY


@dataclass
class LLMResponse:
    """Structured response from the LLM — text + optional tool calls."""

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model_used: str = ""  # populated by chat() — reflects the model that actually produced the text
    stop_reason: str = ""  # raw API stop_reason; "max_tokens" / "end_turn" / "tool_use" / "pause_turn"


# Web search tool definition — Claude's native server-side search.
#
# A single open tool is registered every turn. We considered a
# domain-restricted "medical" variant for vulnerable users, but Anthropic's
# API rejects two tools with the same name in one request, and switching
# tool definitions between turns invalidates the prompt cache (tools →
# system → messages hierarchy). Source-quality steering for clinical
# queries lives in `_VULNERABLE_OVERLAY_PROMPT` (core/presets.py) instead,
# which lets the model reach authoritative sources for "what is quetiapine"
# while still surfacing useful results when the same user asks about a
# fintech or a hostel.
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 3,
}


def _build_system_blocks(system_prompt: str) -> list[dict] | str:
    """Build Anthropic system blocks with prompt caching on the stable prefix.

    If `system_prompt` contains the CACHE_BOUNDARY marker, split it into a
    cacheable stable block (everything before the marker, with
    cache_control=ephemeral) and a dynamic block (everything after, no cache).
    If the marker is absent, return the raw string (backwards compatible with
    callers that don't mark a boundary — e.g., simple utility calls).
    """
    if CACHE_BOUNDARY not in system_prompt:
        return system_prompt

    stable, dynamic = system_prompt.split(CACHE_BOUNDARY, 1)
    stable = stable.rstrip()
    dynamic = dynamic.lstrip()

    if not stable:
        return dynamic or system_prompt

    blocks: list[dict] = [
        {"type": "text", "text": stable, "cache_control": {"type": "ephemeral"}},
    ]
    if dynamic:
        blocks.append({"type": "text", "text": dynamic})
    return blocks


def _parse_response_content(content: list) -> LLMResponse:
    """Extract text and tool_use blocks from Claude API response content.

    Handles standard text, tool_use (channel creation), and server-side
    blocks (web_search server_tool_use / web_search_tool_result) which
    are processed transparently by the API — we just skip them.
    """
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []

    for block in content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))
        # server_tool_use and web_search_tool_result are handled server-side
        # by Claude — we just skip them in parsing

    return LLMResponse(text="\n".join(text_parts).strip(), tool_calls=tool_calls)
