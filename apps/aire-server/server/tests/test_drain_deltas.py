"""Text streams token by token, and never twice (OG118-EXTERNAL-TURN-2).

With `include_partial_messages=True` the SDK yields raw API events as
`StreamEvent`s and still yields the complete `TextBlock` afterwards. The drainer
must emit the deltas as they come, emit nothing more when the block completes,
and keep the result's text exactly as before. Blocks that never streamed (legacy
engines, subagents) keep the whole-block emission.
"""

from dataclasses import dataclass, field
from typing import Any

import pytest

from aire.engine.drain import drain


@dataclass
class TextBlock:
    text: str


@dataclass
class ToolUseBlock:
    name: str = "WebSearch"
    input: dict[str, Any] | None = None
    id: str = "t1"


@dataclass
class AssistantMessage:
    content: list[Any]
    model: str = "claude-opus-4-7"
    usage: dict[str, Any] | None = None
    message_id: str | None = None
    parent_tool_use_id: str | None = None


@dataclass
class StreamEvent:
    event: dict[str, Any]
    uuid: str = "u"
    session_id: str = "s1"
    parent_tool_use_id: str | None = None


@dataclass
class ResultMessage:
    subtype: str = "success"
    usage: dict[str, Any] | None = None
    total_cost_usd: float | None = 0.0
    session_id: str = "s1"


@dataclass
class _Client:
    messages: list[Any] = field(default_factory=list)

    async def receive_response(self):
        for m in self.messages:
            yield m


def _start(index: int = 0, block_type: str = "text") -> StreamEvent:
    return StreamEvent({"type": "content_block_start", "index": index, "content_block": {"type": block_type}})


def _delta(text: str) -> StreamEvent:
    return StreamEvent({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}})


def _stop() -> StreamEvent:
    return StreamEvent({"type": "content_block_stop", "index": 0})


async def _events(messages) -> list[dict[str, Any]]:
    return [ev async for ev in drain(_Client(messages))]


def _texts(events) -> list[str]:
    return [e["text"] for e in events if e["type"] == "text"]


@pytest.mark.asyncio
async def test_deltas_stream_and_the_completed_block_adds_nothing():
    events = await _events([
        _start(), _delta("Hola"), _delta(", "), _delta("Bern."),
        AssistantMessage([TextBlock("Hola, Bern.")]), _stop(),
        ResultMessage(),
    ])
    assert _texts(events) == ["Hola", ", ", "Bern."]
    assert events[-1]["result"].text == "Hola, Bern."
    assert events[-1]["result"].answer == "Hola, Bern."


@pytest.mark.asyncio
async def test_a_block_that_never_streamed_is_still_emitted_whole():
    events = await _events([AssistantMessage([TextBlock("sin deltas")]), ResultMessage()])
    assert _texts(events) == ["sin deltas"]


@pytest.mark.asyncio
async def test_the_tail_the_deltas_missed_is_emitted_once():
    events = await _events([
        _start(), _delta("Hola"), AssistantMessage([TextBlock("Hola, Bern.")]), _stop(), ResultMessage(),
    ])
    assert _texts(events) == ["Hola", ", Bern."]
    assert events[-1]["result"].text == "Hola, Bern."


@pytest.mark.asyncio
async def test_a_mismatched_block_is_not_doubled():
    events = await _events([
        _start(), _delta("otra cosa"), AssistantMessage([TextBlock("Hola, Bern.")]), _stop(), ResultMessage(),
    ])
    assert _texts(events) == ["otra cosa"]
    assert events[-1]["result"].text == "Hola, Bern.", "the result trusts the complete block"


@pytest.mark.asyncio
async def test_a_subagents_block_never_consumes_the_main_sessions_deltas():
    events = await _events([
        _start(), _delta("Hola"),
        AssistantMessage([TextBlock("nota del subagente")], parent_tool_use_id="t9"),
        _delta(", Bern."), AssistantMessage([TextBlock("Hola, Bern.")]), _stop(),
        ResultMessage(),
    ])
    assert _texts(events) == ["Hola", "nota del subagente", ", Bern."]


@pytest.mark.asyncio
async def test_tool_calls_keep_arriving_between_the_deltas_and_the_answer_is_what_follows_them():
    events = await _events([
        _start(), _delta("Déjame ver."), AssistantMessage([TextBlock("Déjame ver.")]), _stop(),
        _start(1, "tool_use"), AssistantMessage([ToolUseBlock()]),
        _start(), _delta("Listo: "), _delta("2026."), AssistantMessage([TextBlock("Listo: 2026.")]), _stop(),
        ResultMessage(),
    ])
    assert [e["type"] for e in events] == ["text", "tool_call", "text", "text", "result"]
    assert events[-1]["result"].text == "Déjame ver.Listo: 2026."
    assert events[-1]["result"].answer == "Listo: 2026."


@pytest.mark.asyncio
async def test_other_delta_kinds_are_ignored():
    events = await _events([
        _start(), StreamEvent({"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "hmm"}}),
        StreamEvent({"type": "message_delta", "delta": {"stop_reason": "end_turn"}}),
        AssistantMessage([TextBlock("ok")]), ResultMessage(),
    ])
    assert _texts(events) == ["ok"]
