"""Tests for fi_runner turn telemetry — turn_completed + guard_critical.

The happy path must be observable, not just errors: every turn emits a
``turn_completed`` event (latency, tokens, model, mcp_count, guard levels) under
a correlating ``request_id``, and a CRITICAL guard outcome emits
``guard_critical`` even though the guard is observational and never edits text.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from fi_runner import MutationStage, Runner, TurnResult, triage_guard


@dataclass
class _FakeBackend:
    text: str = "ok"
    usage: dict | None = None

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        return TurnResult(text=self.text, usage=self.usage)


def _sink() -> tuple[list[tuple[str, dict]], Callable[[str, dict], None]]:
    events: list[tuple[str, dict]] = []
    return events, lambda e, f: events.append((e, f))


def _only(events: list[tuple[str, dict]], name: str) -> list[dict]:
    return [f for e, f in events if e == name]


# --- turn_completed -----------------------------------------------------------


@pytest.mark.asyncio
async def test_turn_completed_emitted_with_fields():
    events, sink = _sink()
    runner = Runner(
        backend=_FakeBackend("hola", usage={"input_tokens": 10, "output_tokens": 3}),
        persona="p",
        model="m1",
        on_event=sink,
    )
    await runner.run("hi")
    completed = _only(events, "turn_completed")
    assert len(completed) == 1
    f = completed[0]
    assert f["model"] == "m1"
    assert f["tokens"] == {"input_tokens": 10, "output_tokens": 3}
    assert f["mcp_count"] == 0
    assert f["attempts"] == 1
    assert isinstance(f["latency_ms"], float)
    assert f["request_id"]  # non-empty
    assert f["guard_levels"] == {}


@pytest.mark.asyncio
async def test_request_id_generated_then_respected():
    events, sink = _sink()
    runner = Runner(backend=_FakeBackend(), persona="p", on_event=sink)
    await runner.run("hi")
    auto = _only(events, "turn_completed")[0]["request_id"]
    assert len(auto) >= 8  # a generated short id

    events2, sink2 = _sink()
    runner2 = Runner(backend=_FakeBackend(), persona="p", on_event=sink2)
    await runner2.run("hi", request_id="my-req-123")
    assert _only(events2, "turn_completed")[0]["request_id"] == "my-req-123"


@pytest.mark.asyncio
async def test_request_id_threads_into_pipeline_events():
    events, sink = _sink()
    runner = Runner(
        backend=_FakeBackend("  hola  "),
        persona="p",
        on_event=sink,
        post_processors=[MutationStage(name="strip", apply=lambda t, c: t.strip(), max_shrink_pct=None)],
    )
    await runner.run("hi", request_id="req-xyz")
    # same id correlates the pipeline event with the turn
    assert _only(events, "mutation_applied")[0]["request_id"] == "req-xyz"
    assert _only(events, "turn_completed")[0]["request_id"] == "req-xyz"


# --- guard_critical -----------------------------------------------------------


@pytest.mark.asyncio
async def test_guard_critical_emitted_on_critical_triage():
    events, sink = _sink()
    runner = Runner(
        backend=_FakeBackend("el paciente refiere plan suicida"),
        persona="p",
        guards=[triage_guard("psychiatry")],
        on_event=sink,
    )
    result = await runner.run("hola doc", request_id="r1")
    crit = _only(events, "guard_critical")
    assert len(crit) == 1
    assert crit[0]["guard"] == "triage"
    assert crit[0]["level"] == "CRITICAL"
    assert crit[0]["request_id"] == "r1"
    # observational: the text is untouched despite the critical signal
    assert result.text == "el paciente refiere plan suicida"
    # and the level shows up in turn_completed.guard_levels
    assert _only(events, "turn_completed")[0]["guard_levels"]["triage"] == "CRITICAL"


@pytest.mark.asyncio
async def test_no_guard_critical_on_calm_text():
    events, sink = _sink()
    runner = Runner(
        backend=_FakeBackend("ánimo estable y buen sueño"),
        persona="p",
        guards=[triage_guard("psychiatry")],
        on_event=sink,
    )
    await runner.run("hola", request_id="r2")
    assert _only(events, "guard_critical") == []
    assert _only(events, "turn_completed")[0]["guard_levels"]["triage"] != "CRITICAL"
