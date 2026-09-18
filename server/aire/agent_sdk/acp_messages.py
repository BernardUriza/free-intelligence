"""ACP session updates, spoken in the shapes `engine/drain.py` already reads.

drain types its messages by CLASS NAME (`AssistantMessage`, `TextBlock`,
`ToolUseBlock`, `ToolResultBlock`, `UserMessage`, `ResultMessage`) and reads
attributes with `getattr` — deliberately, "defensive across SDK versions". So a
second backend needs no changes in drain: it needs classes with those names.
These are them, and `translate` is the whole mapping from ACP's vocabulary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import acp

FINAL_TOOL_STATES = ("completed", "failed")


@dataclass
class TextBlock:
    text: str


@dataclass
class ToolUseBlock:
    name: str
    input: Any = None
    id: str | None = None


@dataclass
class ToolResultBlock:
    tool_use_id: str
    is_error: bool | None = None


@dataclass
class AssistantMessage:
    content: list[Any]
    model: str | None = None
    message_id: str | None = None
    usage: dict[str, Any] | None = None


@dataclass
class UserMessage:
    content: list[Any] = field(default_factory=list)


@dataclass
class ResultMessage:
    subtype: str
    session_id: str
    usage: dict[str, Any] | None = None
    total_cost_usd: float | None = None


def translate(update: Any, agent: str) -> list[Any]:
    """One ACP `session/update` → zero or more drain messages. `model` carries
    the AGENT's name: ACP reports which agent answered, not which weights —
    provenance at the resolution the protocol gives, never a guess."""
    kind = type(update).__name__
    if kind == "AgentMessageChunk":
        text = getattr(getattr(update, "content", None), "text", None)
        if not text:
            return []
        return [AssistantMessage([TextBlock(text)], model=agent,
                                 message_id=getattr(update, "message_id", None))]
    if kind == "ToolCallStart":
        block = ToolUseBlock(name=update.title or update.kind or "tool",
                             input=update.raw_input, id=update.tool_call_id)
        return [AssistantMessage([block], model=agent)]
    if kind == "ToolCallProgress" and update.status in FINAL_TOOL_STATES:
        return [UserMessage([ToolResultBlock(update.tool_call_id,
                                             is_error=update.status == "failed")])]
    return []


def usage_dict(usage: Any) -> dict[str, int] | None:
    """ACP's `Usage` in Anthropic's key names, because that is what `drain`,
    `turn_tokens` and `aire_spend` already read. Absent stays absent: a None
    here is "the agent reported nothing", never a zero."""
    if usage is None:
        return None
    return {"input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "cache_read_input_tokens": int(getattr(usage, "cached_read_tokens", 0) or 0),
            "cache_creation_input_tokens": int(getattr(usage, "cached_write_tokens", 0) or 0)}


def result_message(response: Any, session_id: str, cost: float | None) -> ResultMessage:
    """`end_turn` is the SDK's `success`; every other stop reason keeps its own
    name under the SDK's `error_*` prefix, so a consumer that already branches
    on `subtype` needs no new vocabulary."""
    reason = getattr(response, "stop_reason", None) or "unknown"
    subtype = "success" if reason == "end_turn" else f"error_{reason}"
    return ResultMessage(subtype=subtype, session_id=session_id,
                         usage=usage_dict(getattr(response, "usage", None)),
                         total_cost_usd=cost)


def _blocks(payload: Any) -> list[Any]:
    """The `query` payload as ACP content blocks: a string, or the streaming-
    input dicts `engine/vision.py` folds an image turn into."""
    if isinstance(payload, str):
        return [acp.text_block(payload)]
    blocks: list[Any] = []
    for block in payload:
        if block.get("type") == "image":
            src = block["source"]
            blocks.append(acp.image_block(src["data"], src["media_type"]))
        elif block.get("type") == "text":
            blocks.append(acp.text_block(block["text"]))
    return blocks


async def collect_blocks(payload: Any) -> list[Any]:
    if isinstance(payload, str):
        return _blocks(payload)
    blocks: list[Any] = []
    async for message in payload:
        blocks.extend(_blocks(message["message"]["content"]))
    return blocks
