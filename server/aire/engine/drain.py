"""The turn-loop event drainer — copied from fi-runner's proven loop.

Types are identified via `type(m).__name__` (defensive across SDK versions),
and a tool's RESULT does not come back as an assistant message but as a
`ToolResultBlock` inside a USER message — paired by `tool_use_id`.
"""

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from typing import Any

from .contract import ToolCall, TurnResult


def turn_cost(event: dict[str, Any]) -> float:
    """The dollars a `result` event reports (0.0 when absent) — the engine's
    per-turn accounting reads it off the drained stream, not the SDK directly.

    The result reaches this in TWO shapes: the SDK's dataclass, straight from the
    turn loop, and a plain dict once the HTTP surface has flattened it for the
    wire. Reading only the first answered 0.0 to the second, so an invited key
    (#32d) billed nothing on every turn and its ceiling could never bite — a
    money function that silently returns 0 for a shape it does not know is
    indistinguishable from a free turn. Both shapes are read here."""
    result = event.get("result")
    usage = getattr(result, "usage", None)
    if usage is None and isinstance(result, dict):
        usage = result.get("usage")
    cost = usage.get("total_cost_usd") if isinstance(usage, dict) else None
    return float(cost) if cost else 0.0


@dataclass
class _State:
    parts: list[str] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    session_id: str | None = None
    tools: list[ToolCall] = field(default_factory=list)
    by_id: dict[str, int] = field(default_factory=dict)
    start_ts: dict[str, float] = field(default_factory=dict)


def _on_assistant(content: list, st: _State) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in content:
        btype = type(block).__name__
        if btype == "TextBlock":
            text = getattr(block, "text", "") or ""
            if text:
                st.parts.append(text)
                events.append({"type": "text", "text": text})
        elif btype == "ToolUseBlock":
            tc = ToolCall(name=getattr(block, "name", "") or "",
                          input=getattr(block, "input", None),
                          id=getattr(block, "id", None))
            if tc.id is not None:
                st.by_id[tc.id] = len(st.tools)
                st.start_ts[tc.id] = time.monotonic()
            st.tools.append(tc)
            events.append({"type": "tool_call", "tool": tc})
    return events


def _on_user(content: list, st: _State) -> None:
    for block in content:
        if type(block).__name__ != "ToolResultBlock":
            continue
        use_id = getattr(block, "tool_use_id", None)
        idx = st.by_id.get(use_id) if use_id is not None else None
        if idx is None:
            continue
        raw_err = getattr(block, "is_error", None)
        t0 = st.start_ts.get(use_id)
        st.tools[idx] = replace(
            st.tools[idx],
            is_error=None if raw_err is None else bool(raw_err),
            duration_ms=int((time.monotonic() - t0) * 1000) if t0 is not None else None,
        )


def _on_result(message: Any, st: _State) -> None:
    raw = getattr(message, "usage", None)
    if raw is not None:
        st.usage = dict(raw) if isinstance(raw, dict) else dict(getattr(raw, "__dict__", {}) or {})
        cost = getattr(message, "total_cost_usd", None)
        if cost is not None:
            st.usage["total_cost_usd"] = cost
    st.session_id = getattr(message, "session_id", None) or st.session_id


async def drain(client: Any) -> AsyncIterator[dict[str, Any]]:
    """Drains the SDK's response and emits {"type": ...} events as they happen."""
    st = _State()
    async for message in client.receive_response():
        kind = type(message).__name__
        content = getattr(message, "content", None)
        if kind == "AssistantMessage" and isinstance(content, list):
            for event in _on_assistant(content, st):
                yield event
        elif kind == "UserMessage" and isinstance(content, list):
            _on_user(content, st)
        elif kind == "ResultMessage":
            _on_result(message, st)
    yield {"type": "result",
           "result": TurnResult(text="".join(st.parts), usage=st.usage,
                                session_id=st.session_id, tool_calls=tuple(st.tools))}
