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
    """The dollars a `result` event reports (0.0 when absent) — per-turn
    accounting reads it off the drained stream, not the SDK directly. The result
    arrives in TWO shapes: the SDK dataclass straight from the turn loop, and a
    plain dict once the HTTP surface flattened it for the wire. Reading only the
    first answered 0.0 to the second, so an invited key (#32d) billed nothing and
    its ceiling could never bite — a money function that silently returns 0 for a
    shape it does not know is indistinguishable from a free turn. Both are read."""
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
    streamed: dict[str, Any] = field(default_factory=dict)
    streamed_ids: set[str] = field(default_factory=set)
    subtype: str | None = None
    session_id: str | None = None
    model: str | None = None
    tools: list[ToolCall] = field(default_factory=list)
    by_id: dict[str, int] = field(default_factory=dict)
    start_ts: dict[str, float] = field(default_factory=dict)
    answer_from: int = 0  #: índice en `parts` donde empieza la respuesta (ver contract.TurnResult)


def _tokens_spent(usage: dict[str, Any] | None) -> bool:
    return bool(usage) and any(bool(usage.get(k)) for k in ("input_tokens", "output_tokens"))


def _bank_streamed(message: Any, st: _State) -> None:
    """Sum the INPUT-side usage the SDK stamps on every AssistantMessage. It
    yields one message per CONTENT BLOCK of an API call (thinking, then text),
    all carrying that call's usage, so an API call counts once — by message id.
    `output_tokens` is NOT banked: on the stream it is the `message_start`
    placeholder (measured 1 against a result of 233), not a count."""
    raw = getattr(message, "usage", None)
    if not isinstance(raw, dict):
        return
    key = str(getattr(message, "message_id", None) or sorted(raw.items()))
    if key in st.streamed_ids:
        return
    st.streamed_ids.add(key)
    for k, v in raw.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and not k.startswith("output_tokens"):
            st.streamed[k] = st.streamed.get(k, 0) + v


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
            st.answer_from = len(st.parts)  # lo dicho hasta aquí fue camino, no respuesta
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
    """The result's usage, unless the CLI zeroed it under an answer it DID stream.

    `error_max_budget_usd` (SDK 0.2.123, measured 2026-09-03): the call completes,
    the text streams, and the result arrives with every token count at 0 — the
    shape consumers rightly read as "text no model generated" (discord-bot's
    gateway refused eight of Insult's answers in two days on it). When the result
    denies any spend, the streamed INPUT usage leaves here and the output count
    leaves ABSENT — unknown, never a zero, never the stream's placeholder. A
    burned credential (`limit_hit`) streams nothing, so it stays all-zero."""
    raw = getattr(message, "usage", None)
    if raw is not None:
        st.usage = dict(raw) if isinstance(raw, dict) else dict(getattr(raw, "__dict__", {}) or {})
    if not _tokens_spent(st.usage) and _tokens_spent(st.streamed):
        st.usage = {k: v for k, v in {**(st.usage or {}), **st.streamed}.items()
                    if not k.startswith("output_tokens")}
    cost = getattr(message, "total_cost_usd", None)
    if cost is not None and st.usage is not None:
        st.usage["total_cost_usd"] = cost
    st.subtype = getattr(message, "subtype", None)
    st.session_id = getattr(message, "session_id", None) or st.session_id


async def drain(client: Any) -> AsyncIterator[dict[str, Any]]:
    """Drains the SDK's response and emits {"type": ...} events as they happen."""
    st = _State()
    async for message in client.receive_response():
        kind = type(message).__name__
        content = getattr(message, "content", None)
        if kind == "AssistantMessage" and isinstance(content, list):
            st.model = getattr(message, "model", None) or st.model
            _bank_streamed(message, st)
            for event in _on_assistant(content, st):
                yield event
        elif kind == "UserMessage" and isinstance(content, list):
            _on_user(content, st)
        elif kind == "ResultMessage":
            _on_result(message, st)
    yield {"type": "result",
           "result": TurnResult(text="".join(st.parts), usage=st.usage,
                                answer="".join(st.parts[st.answer_from:]),
                                session_id=st.session_id, tool_calls=tuple(st.tools),
                                model=st.model, subtype=st.subtype)}
