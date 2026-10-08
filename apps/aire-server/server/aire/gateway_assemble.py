"""Assemble an Anthropic SSE stream into its final message (#30) — pure functions.

The gateway relays bytes untouched; this module replays the SAME bytes on the
side into the message JSON the turn would have produced non-streaming, so the
mirror stores one readable document instead of a pile of deltas. Unknown event
and delta types are ignored on purpose: the wire format grows with every
Claude Code release, and the mirror must not break on what it does not know.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any


def assemble(raw: bytes, content_type: str) -> dict[str, Any] | None:
    """The final message from a response body — SSE stream or plain JSON."""
    text = raw.decode("utf-8", errors="replace")
    if "text/event-stream" not in content_type:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return _assemble_events(_events(text))


def _events(text: str) -> Iterator[dict[str, Any]]:
    for block in text.split("\n\n"):
        lines = [line[5:].strip() for line in block.splitlines() if line.startswith("data:")]
        if not lines:
            continue
        try:
            yield json.loads("\n".join(lines))
        except json.JSONDecodeError:
            continue


def _assemble_events(events: Iterator[dict[str, Any]]) -> dict[str, Any] | None:
    message: dict[str, Any] | None = None
    partial: dict[int, str] = {}
    for ev in events:
        kind = ev.get("type")
        if kind == "message_start":
            message = dict(ev.get("message") or {})
            message.setdefault("content", [])
        elif message is None:
            continue
        elif kind == "content_block_start":
            _put(message["content"], int(ev["index"]), dict(ev.get("content_block") or {}))
        elif kind == "content_block_delta":
            _delta(message["content"], int(ev["index"]), ev.get("delta") or {}, partial)
        elif kind == "content_block_stop":
            _close(message["content"], int(ev["index"]), partial)
        elif kind == "message_delta":
            message.update(ev.get("delta") or {})
            if ev.get("usage"):
                message.setdefault("usage", {}).update(ev["usage"])
    return message


def _put(content: list[dict[str, Any]], index: int, block: dict[str, Any]) -> None:
    while len(content) <= index:
        content.append({})
    content[index] = block


def _delta(content: list[dict[str, Any]], index: int, delta: dict[str, Any],
           partial: dict[int, str]) -> None:
    while len(content) <= index:
        content.append({})
    block, kind = content[index], delta.get("type")
    if kind == "text_delta":
        block["text"] = block.get("text", "") + delta.get("text", "")
    elif kind == "input_json_delta":
        partial[index] = partial.get(index, "") + delta.get("partial_json", "")
    elif kind == "thinking_delta":
        block["thinking"] = block.get("thinking", "") + delta.get("thinking", "")
    elif kind == "signature_delta":
        block["signature"] = block.get("signature", "") + delta.get("signature", "")


def _close(content: list[dict[str, Any]], index: int, partial: dict[int, str]) -> None:
    if index not in partial or index >= len(content):
        return
    buffered = partial.pop(index)
    try:
        content[index]["input"] = json.loads(buffered)
    except json.JSONDecodeError:
        content[index]["input_json"] = buffered
