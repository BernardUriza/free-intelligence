"""Tests for live streaming — Runner.run_stream + backend run_turn_stream.

The headline: a consumer sees tool_call / text events AS THEY HAPPEN, then a
final result event after guards + post-processors settle. run() is unchanged;
a backend without run_turn_stream falls back to one result event.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from fi_runner import MutationStage, Runner, ToolCall, TurnResult, triage_guard


@dataclass
class _StreamBackend:
    """A streaming backend: emits a tool_call, two text deltas, then a result."""

    reply: str = "hello"

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003 - fallback path, unused here
        return TurnResult(text=self.reply)

    async def run_turn_stream(self, **kwargs):  # noqa: ANN003
        yield {"type": "tool_call", "tool": ToolCall.make("mcp__web__search", is_error=False)}
        yield {"type": "text", "text": self.reply[: len(self.reply) // 2]}
        yield {"type": "text", "text": self.reply[len(self.reply) // 2 :]}
        yield {"type": "result", "result": TurnResult(text=self.reply, tool_calls=[ToolCall.make("mcp__web__search")])}


@dataclass
class _NoStreamBackend:
    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        return TurnResult(text="oneshot")


def _event_sink() -> tuple[list[tuple[str, dict]], Callable[[str, dict], None]]:
    events: list[tuple[str, dict]] = []
    return events, lambda e, f: events.append((e, f))


@pytest.mark.asyncio
async def test_run_stream_emits_tool_calls_before_result():
    runner = Runner(backend=_StreamBackend(reply="hola mundo"), persona="p", flow_narrator=None)
    events = [ev async for ev in runner.run_stream("hi")]
    types = [ev["type"] for ev in events]
    assert types == ["tool_call", "text", "text", "result"]  # live order
    assert types.index("tool_call") < types.index("result")  # tool_call BEFORE the end
    assert events[0]["tool"].name == "mcp__web__search"
    assert "".join(ev["text"] for ev in events if ev["type"] == "text") == "hola mundo"  # deltas reassemble
    assert events[-1]["result"].text == "hola mundo"  # final result carries the full text


@pytest.mark.asyncio
async def test_run_stream_falls_back_to_one_result_for_nonstreaming_backend():
    runner = Runner(backend=_NoStreamBackend(), persona="p", flow_narrator=None)
    events = [ev async for ev in runner.run_stream("hi")]
    assert [ev["type"] for ev in events] == ["result"]
    assert events[-1]["result"].text == "oneshot"


@pytest.mark.asyncio
async def test_run_stream_runs_guards_and_post_processors_on_result():
    events, sink = _event_sink()
    runner = Runner(
        backend=_StreamBackend(reply="  el paciente refiere plan suicida  "),
        persona="p",
        guards=[triage_guard("psychiatry")],
        post_processors=[MutationStage(name="strip", apply=lambda t, c: t.strip(), max_shrink_pct=None)],
        on_event=sink,
        flow_narrator=None,
    )
    out = [ev async for ev in runner.run_stream("hola doc", request_id="s1")]
    # guards ran on the streamed result → CRITICAL surfaced + post-processor applied
    assert any(e == "guard_critical" for e, _ in events)
    assert [f for e, f in events if e == "turn_completed"][0]["guard_levels"]["triage"] == "CRITICAL"
    assert any(e == "mutation_applied" for e, _ in events)
    assert out[-1]["result"].text == "el paciente refiere plan suicida"  # stripped (post-processor)


@pytest.mark.asyncio
async def test_run_stream_emits_tool_called_telemetry():
    events, sink = _event_sink()
    runner = Runner(backend=_StreamBackend(), persona="p", on_event=sink, flow_narrator=None)
    _ = [ev async for ev in runner.run_stream("hi")]
    tool_events = [f for e, f in events if e == "tool_called"]
    assert tool_events and tool_events[0]["name"] == "mcp__web__search"
    assert [f for e, f in events if e == "turn_completed"][0]["streamed"] is True


@pytest.mark.asyncio
async def test_run_stream_rejects_empty_message():
    runner = Runner(backend=_StreamBackend(), persona="p", flow_narrator=None)
    with pytest.raises(ValueError, match="user_message"):
        _ = [ev async for ev in runner.run_stream("   ")]
