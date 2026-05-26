"""Tests for the plan-first stream events (Runner.run_stream → derived events).

Two layers:
  - ``_derive_plan_events(tool_call)`` — pure function, given a ToolCall returns
    the semantic events to additionally yield. Tested in isolation.
  - ``Runner.run_stream`` integration — a fake backend yields task_tracker
    tool_calls; we assert the runner yields both the raw tool_call AND the
    derived plan/step_* events.
"""

from __future__ import annotations

import pytest

from fi_runner import (
    MCPServerSpec,
    Runner,
    ToolCall,
)
from fi_runner.runner import _derive_plan_events

# --- _derive_plan_events: pure ---------------------------------------------


def test_derive_ignores_non_task_tracker_calls():
    tc = ToolCall.make("mcp__brightdata__search_engine", input={"q": "x"}, id="t1")
    assert _derive_plan_events(tc, session_id="s1") == []


def test_derive_ignores_builtin_tools():
    tc = ToolCall.make("Bash", input={"command": "ls"}, id="t1")
    assert _derive_plan_events(tc, session_id="s1") == []


def test_derive_emits_plan_event_for_declare_plan():
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__declare_plan",
        input={"session_id": "s1", "steps": ["a", "b", "c"]},
        id="t1",
    )
    events = _derive_plan_events(tc, session_id="s1")
    assert events == [{"type": "plan", "data": {"session_id": "s1", "steps": ["a", "b", "c"]}}]


def test_derive_falls_back_to_runner_session_id_if_input_omits_it():
    # Some agents pass steps without session_id; the runner knows it anyway.
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__declare_plan",
        input={"steps": ["x"]},
        id="t1",
    )
    events = _derive_plan_events(tc, session_id="from-runner")
    assert events[0]["data"]["session_id"] == "from-runner"


def test_derive_returns_empty_on_malformed_declare_plan_steps():
    # Agent passed a string instead of a list — drop silently; raw tool_call
    # still goes through above (UI shows the tool error from the MCP response).
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__declare_plan",
        input={"session_id": "s1", "steps": "not-a-list"},
        id="t1",
    )
    assert _derive_plan_events(tc, session_id="s1") == []


def test_derive_emits_step_started():
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__start_step",
        input={"plan_id": "p1", "step_index": 0},
        id="t2",
    )
    assert _derive_plan_events(tc, session_id="s1") == [
        {"type": "step_started", "data": {"plan_id": "p1", "step_index": 0}}
    ]


def test_derive_emits_step_done_done():
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__complete_step",
        input={"plan_id": "p1", "step_index": 1, "summary": "found 3"},
        id="t3",
    )
    assert _derive_plan_events(tc, session_id="s1") == [
        {"type": "step_done", "data": {"plan_id": "p1", "step_index": 1, "status": "done", "summary": "found 3"}}
    ]


def test_derive_emits_step_done_failed():
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__fail_step",
        input={"plan_id": "p1", "step_index": 1, "error": "timeout"},
        id="t4",
    )
    assert _derive_plan_events(tc, session_id="s1") == [
        {"type": "step_done", "data": {"plan_id": "p1", "step_index": 1, "status": "failed", "error": "timeout"}}
    ]


def test_derive_drops_silently_when_input_missing():
    # Codex doesn't capture MCP tool inputs — server is parsed from the name
    # so it routes here, but input is None. We can't reconstruct payload; drop.
    tc = ToolCall(
        name="mcp__fi_core_task_tracker__declare_plan",
        server="fi_core_task_tracker",
        input=None,
        id="t1",
    )
    assert _derive_plan_events(tc, session_id="s1") == []


# --- Runner.run_stream: integration ----------------------------------------


class _FakeStreamingBackend:
    """Backend that yields the events the SDK would yield for a turn where the
    agent first declares a plan, starts a step, and completes it. No SDK."""

    async def run_turn_stream(self, **_kw):
        from fi_runner import TurnResult

        plan_tc = ToolCall.make(
            "mcp__fi_core_task_tracker__declare_plan",
            input={"session_id": "s1", "steps": ["search", "scrape"]},
            id="t1",
        )
        start_tc = ToolCall.make(
            "mcp__fi_core_task_tracker__start_step",
            input={"plan_id": "p1", "step_index": 0},
            id="t2",
        )
        done_tc = ToolCall.make(
            "mcp__fi_core_task_tracker__complete_step",
            input={"plan_id": "p1", "step_index": 0, "summary": "got it"},
            id="t3",
        )
        yield {"type": "tool_call", "tool": plan_tc}
        yield {"type": "tool_call", "tool": start_tc}
        yield {"type": "text", "text": "trabajando..."}
        yield {"type": "tool_call", "tool": done_tc}
        yield {"type": "result", "result": TurnResult(text="listo", tool_calls=[plan_tc, start_tc, done_tc])}


@pytest.mark.asyncio
async def test_run_stream_emits_derived_plan_events_alongside_tool_calls():
    runner = Runner(
        backend=_FakeStreamingBackend(),  # type: ignore[arg-type]
        persona="t",
        extra_mcp_servers=[MCPServerSpec(name="dummy")],
    )
    events = [ev async for ev in runner.run_stream("hola", session_id="s1")]

    # The 3 tool_calls should pass through AND each spawn its derived event.
    types = [e["type"] for e in events]
    # Each tool_call is immediately followed by its derived semantic event.
    assert "plan" in types
    assert "step_started" in types
    assert "step_done" in types
    # And the raw tool_calls still went through (UI keeps generic step view).
    assert types.count("tool_call") == 3

    plan_ev = next(e for e in events if e["type"] == "plan")
    assert plan_ev["data"] == {"session_id": "s1", "steps": ["search", "scrape"]}

    done_ev = next(e for e in events if e["type"] == "step_done")
    assert done_ev["data"]["status"] == "done"
    assert done_ev["data"]["summary"] == "got it"


def test_capability_task_tracker_resolves_to_correct_spec():
    # The capability factory builds a spec pointing at the fi-core MCP server
    # module with the contract-declared name + tools.
    from fi_runner.capabilities import resolve, task_tracker

    spec = task_tracker()
    assert spec.name == "fi_core_task_tracker"
    assert spec.args == ["-m", "fi_core.task_tracker.mcp_server"]
    assert set(spec.tools) >= {"declare_plan", "start_step", "complete_step", "fail_step"}

    # resolve() includes it in the registry.
    [resolved] = resolve(["task_tracker"])
    assert resolved.name == "fi_core_task_tracker"
