"""Assemble an OpenAI-wire response into one document (#51) — pure functions.

The OpenAI door relays bytes untouched, like the Anthropic one; this module
replays the same bytes on the side for two readers: the biller, which needs
`model` and `usage`, and the mirror, which stores one readable document instead
of a pile of chunks. Two wires share the prefix:

- Chat Completions streams `chat.completion.chunk` objects; the usage arrives
  only in a final chunk with no choices, and only when the request asked for it
  (`stream_options.include_usage` — the door makes sure it did).
- Responses streams typed events; `response.completed` carries the whole final
  response, usage included, so it is returned as it came.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any


def assemble(raw: bytes, content_type: str) -> dict[str, Any] | None:
    text = raw.decode("utf-8", errors="replace")
    if "text/event-stream" not in content_type:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return _fold(_events(text))


def _events(text: str) -> Iterator[dict[str, Any]]:
    for block in text.split("\n\n"):
        lines = [line[5:].strip() for line in block.splitlines() if line.startswith("data:")]
        payload = "\n".join(lines)
        if not payload or payload == "[DONE]":
            continue
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


def _fold(events: Iterator[dict[str, Any]]) -> dict[str, Any] | None:
    chat: dict[str, Any] | None = None
    parts: list[str] = []
    for ev in events:
        if ev.get("type") == "response.completed":
            return ev.get("response")
        if ev.get("object") != "chat.completion.chunk":
            continue
        chat = chat or {"id": ev.get("id"), "object": "chat.completion", "model": ev.get("model")}
        for choice in ev.get("choices") or []:
            parts.append((choice.get("delta") or {}).get("content") or "")
            chat["finish_reason"] = choice.get("finish_reason") or chat.get("finish_reason")
        if ev.get("usage"):
            chat["usage"] = ev["usage"]
    if chat is not None:
        chat["choices"] = [{"index": 0, "finish_reason": chat.pop("finish_reason", None),
                            "message": {"role": "assistant", "content": "".join(parts)}}]
    return chat


def with_usage(body: bytes) -> bytes:
    """A streamed Chat Completions request that did not ask for usage gets asked:
    without it the stream carries no token counts, the turn prices at $0, and
    the key's ceiling never bites. Anything that is not such a request passes
    through byte for byte."""
    try:
        parsed = json.loads(body) if body else None
    except json.JSONDecodeError:
        return body
    if not isinstance(parsed, dict) or not parsed.get("stream"):
        return body
    options = parsed.get("stream_options") or {}
    if options.get("include_usage"):
        return body
    parsed["stream_options"] = {**options, "include_usage": True}
    return json.dumps(parsed).encode("utf-8")
