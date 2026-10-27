"""`codex exec --json` events, spoken in the classes `engine/drain.py` reads —
the same trick `acp_messages.py` plays for ACP, for a different vocabulary
(`thread.started`, `item.started|updated|completed`, `turn.completed|failed`,
`error`; items: agent_message, reasoning, command_execution, file_change,
mcp_tool_call, web_search, todo_list, error — from the official TypeScript
SDK's `events.ts`/`items.ts`, read 2026-10-26)."""

from __future__ import annotations

import base64
from typing import Any

from .acp_messages import (AssistantMessage, ResultMessage, TextBlock, ToolResultBlock,
                           ToolUseBlock, UserMessage)

TOOL_ITEMS = ("command_execution", "mcp_tool_call", "file_change", "web_search")
IMAGE_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


def usage_dict(usage: dict[str, Any]) -> dict[str, int]:
    """Codex's usage in Anthropic's key names. OpenAI's `input_tokens` INCLUDES
    the cached part; Anthropic's excludes it, so the cached count is taken out
    to keep `aire_spend`'s cache columns comparable across providers."""
    cached = int(usage.get("cached_input_tokens") or 0)
    return {"input_tokens": max(int(usage.get("input_tokens") or 0) - cached, 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
            "cache_read_input_tokens": cached,
            "cache_creation_input_tokens": int(usage.get("cache_write_input_tokens") or 0)}


def turn_usd(usage: dict[str, Any], model: str) -> float:
    """What this turn's tokens cost at OpenAI's list price (#53): Codex reports
    tokens, never dollars, and a metered key (`codex/apikey/*`) needs dollars to
    reach `aire_spend`. Priced through the OpenAI door's own table, which bills
    an unknown model at the DEAREST row — a ceiling must never be free."""
    from .. import pricing
    return pricing.openai_usd(
        {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
         "input_tokens_details": {"cached_tokens": usage.get("cached_input_tokens")}}, model)


def result(event: dict[str, Any], thread: str | None,
           model: str = "") -> tuple[dict[str, Any], ResultMessage]:
    """A closing event as (mirror entry, drain result). `turn.completed` is the
    SDK's `success`; a failed turn keeps its own name under `error_` so a
    consumer branching on `subtype` needs no new vocabulary, and carries its
    message as `error` — the rotor reads a usage limit there, never as text."""
    if event["type"] == "turn.completed":
        raw = event.get("usage") or {}
        usage, usd = usage_dict(raw), turn_usd(raw, model)
        return ({"stop_reason": "end_turn", "usage": usage, "usd": usd},
                ResultMessage(subtype="success", session_id=thread or "", usage=usage,
                              total_cost_usd=usd))
    message = (event.get("error") or {}).get("message", "")
    return ({"stop_reason": "turn_failed", "error": message},
            ResultMessage(subtype="error_turn_failed", session_id=thread or "", error=message))


def item_messages(kind: str, item: dict[str, Any], model: str, opened: set[str]) -> list[Any]:
    """One `item.*` event → zero or more drain messages. Reasoning, todo lists
    and error items are mirrored by the caller and never painted as text."""
    if kind == "item.completed" and item.get("type") == "agent_message" and item.get("text"):
        return [AssistantMessage([TextBlock(item["text"])], model=model, message_id=item.get("id"))]
    if item.get("type") in TOOL_ITEMS:
        return _tool_messages(item, opened)
    return []


def _tool_messages(item: dict[str, Any], opened: set[str]) -> list[Any]:
    """A tool item as drain's use/result pair: the first sighting opens it, the
    final status closes it, and an item first seen already final does both."""
    item_id, status = item.get("id") or "", item.get("status", "completed")
    use = AssistantMessage([ToolUseBlock(name=_tool_name(item), input=_tool_input(item), id=item_id)])
    done = UserMessage([ToolResultBlock(item_id, is_error=status == "failed")])
    messages = [] if item_id in opened else [use]
    opened.add(item_id)
    if status != "in_progress":
        messages.append(done)
    return messages


def _tool_name(item: dict[str, Any]) -> str:
    if item["type"] == "mcp_tool_call":
        return f"{item.get('server', '')}/{item.get('tool', '')}"
    return item["type"]


def _tool_input(item: dict[str, Any]) -> Any:
    return {"command_execution": item.get("command"), "mcp_tool_call": item.get("arguments"),
            "file_change": item.get("changes"), "web_search": item.get("query")}.get(item["type"])


async def prompt_and_images(payload: Any) -> tuple[str, list[tuple[bytes, str]]]:
    """The `query` payload as codex's two inputs: one prompt string and the
    image bytes `-i` takes from files. A text document rides inline; a PDF
    never reaches here (the door refuses it for a non-Claude provider)."""
    if isinstance(payload, str):
        return payload, []
    texts: list[str] = []
    images: list[tuple[bytes, str]] = []
    async for message in payload:
        for block in message["message"]["content"]:
            _fold(block, texts, images)
    return "\n\n".join(texts), images


def _fold(block: dict[str, Any], texts: list[str], images: list[tuple[bytes, str]]) -> None:
    kind, src = block.get("type"), block.get("source") or {}
    if kind == "text":
        texts.append(block["text"])
    elif kind == "image":
        images.append((base64.b64decode(src["data"]), src["media_type"]))
    elif kind == "document":
        if src.get("type") != "text":
            raise ValueError("codex exec cannot carry a PDF document")
        title = block.get("title")
        texts.append(f"[{title}]\n{src['data']}" if title else src["data"])
