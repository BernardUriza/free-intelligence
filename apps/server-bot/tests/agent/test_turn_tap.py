"""`run_turn_tapped` — el drenado de fi-runner con un tap por `tool_call`.

Misma tabla que `AIREBackend.run_turn`: el `result` es lo que vuelve; el
`budget_exhausted` emitido después de un resultado con texto no lo tira; sin
texto sigue siendo error; un stream que cierra sin `result` es error.
"""

from __future__ import annotations

import pytest
from fi_runner.backend import BackendError, ToolCall, TurnResult
from fi_runner.backends.aire import AIREDoorError

from persona_runner.engine.turn_tap import run_turn_tapped, wire_tool_call


class _Backend:
    def __init__(self, events, raise_after=None):
        self._events, self._raise = events, raise_after

    async def run_turn_stream(self, **_kwargs):
        for ev in self._events:
            yield ev
        if self._raise is not None:
            raise self._raise


def _tool(name: str, tool_id: str) -> dict:
    return {"type": "tool_call", "tool": ToolCall(name=name, id=tool_id, input={"q": "secreto"})}


async def test_each_tool_call_reaches_the_tap_and_the_result_comes_back():
    seen: list[str] = []
    backend = _Backend(
        [
            _tool("mcp__memory__recall", "a"),
            {"type": "text", "text": "pensando"},
            _tool("WebSearch", "b"),
            {"type": "result", "result": TurnResult(text="hola")},
        ]
    )
    result = await run_turn_tapped(backend, on_event=lambda ev: seen.append(ev["tool"].name))
    assert result.text == "hola"
    assert seen == ["mcp__memory__recall", "WebSearch"]


async def test_budget_exhausted_after_a_result_with_text_keeps_the_answer():
    backend = _Backend(
        [{"type": "result", "result": TurnResult(text="respuesta")}],
        raise_after=AIREDoorError("cut", code="budget_exhausted"),
    )
    result = await run_turn_tapped(backend, on_event=lambda _ev: None)
    assert result.text == "respuesta"


async def test_budget_exhausted_without_text_is_still_an_error():
    backend = _Backend(
        [{"type": "result", "result": TurnResult(text="")}], raise_after=AIREDoorError("cut", code="budget_exhausted")
    )
    with pytest.raises(AIREDoorError):
        await run_turn_tapped(backend, on_event=lambda _ev: None)


async def test_a_stream_without_result_is_an_error_not_an_empty_success():
    backend = _Backend([_tool("WebSearch", "a")])
    with pytest.raises(BackendError):
        await run_turn_tapped(backend, on_event=lambda _ev: None)


def test_the_wire_frame_names_the_tool_and_never_carries_its_input():
    frame = wire_tool_call(_tool("mcp__memory__recall", "a"))
    assert frame == {
        "type": "tool_call",
        "tool": {"name": "mcp__memory__recall", "id": "a", "server": None, "is_error": None},
    }
    assert "secreto" not in str(frame)
