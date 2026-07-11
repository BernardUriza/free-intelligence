"""Tests for the plan-first stream events (Runner.run_stream → derived events).

Three layers:
  - ``_derive_plan_events(tool_call, ...)`` — pure function, given a ToolCall
    returns the semantic events to additionally yield. Tested in isolation,
    with and without the per-turn ``_PlanStreamObserver``.
  - ``Runner.run_stream`` integration — a fake backend yields task_tracker
    tool_calls; we assert the runner yields both the raw tool_call AND the
    derived plan / step_* / plan_completed / plan_failed / plan_cancelled events.
  - ``PlanGuard`` integration — when the Runner has a PlanGuard configured,
    a blocked plan triggers a ``plan_rejected`` event right after ``plan``.
"""

from __future__ import annotations

import pytest

from fi_runner import (
    MCPServerSpec,
    PlanGuard,
    Runner,
    ToolCall,
    plan_guard,
)
from fi_runner.runner import _derive_plan_events, _PlanStreamObserver

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


def test_derive_stamps_request_id_when_provided():
    # G17: every derived event carries request_id so a UI multiplexing
    # concurrent turns can route to the right transcript.
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__declare_plan",
        input={"session_id": "s1", "steps": ["a"]},
        id="t1",
    )
    events = _derive_plan_events(tc, session_id="s1", request_id="req-42")
    assert events[0]["data"]["request_id"] == "req-42"


def test_derive_falls_back_to_runner_session_id_if_input_omits_it():
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__declare_plan",
        input={"steps": ["x"]},
        id="t1",
    )
    events = _derive_plan_events(tc, session_id="from-runner")
    assert events[0]["data"]["session_id"] == "from-runner"


def test_derive_returns_empty_on_malformed_declare_plan_steps():
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


def test_derive_emits_step_done_cancelled():
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__cancel_step",
        input={"plan_id": "p1", "step_index": 0, "reason": "user abort"},
        id="t5",
    )
    [ev] = _derive_plan_events(tc, session_id="s1")
    assert ev["type"] == "step_done"
    assert ev["data"]["status"] == "cancelled"
    assert ev["data"]["error"] == "user abort"


def test_derive_emits_step_noted():
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__note_step",
        input={"plan_id": "p1", "step_index": 0, "note": "halfway"},
        id="t6",
    )
    [ev] = _derive_plan_events(tc, session_id="s1")
    assert ev == {"type": "step_noted", "data": {"plan_id": "p1", "step_index": 0, "note": "halfway"}}


def test_derive_emits_plan_amended_for_insert_and_replan():
    insert = ToolCall.make(
        "mcp__fi_core_task_tracker__insert_step",
        input={"plan_id": "p1", "after_index": 0, "spec": "x"},
        id="t7",
    )
    [ev] = _derive_plan_events(insert, session_id="s1")
    assert ev["type"] == "plan_amended"
    assert ev["data"]["action"] == "insert"

    rep = ToolCall.make(
        "mcp__fi_core_task_tracker__replan",
        input={"plan_id": "p1", "from_index": 1, "new_steps": ["new_b"]},
        id="t8",
    )
    [ev2] = _derive_plan_events(rep, session_id="s1")
    assert ev2["data"]["action"] == "replan"


def test_derive_emits_plan_cancelled_for_cancel_plan():
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__cancel_plan",
        input={"plan_id": "p1", "reason": "user abort"},
        id="t9",
    )
    [ev] = _derive_plan_events(tc, session_id="s1")
    assert ev == {"type": "plan_cancelled", "data": {"plan_id": "p1", "reason": "user abort"}}


def test_derive_emits_plan_completed_for_finalize_plan_without_observer():
    # No observer: default to plan_completed (finalize means "ship as-is"), and
    # the counters STILL ship — zeroed, never absent. An omitted counter reached
    # the client as `undefined` and got coerced to 0, so "no failures" and
    # "nobody counted" were indistinguishable on the wire. The contract
    # (fi_runner.events.PlanTerminalData) requires them on every terminal frame.
    tc = ToolCall.make(
        "mcp__fi_core_task_tracker__finalize_plan",
        input={"plan_id": "p1"},
        id="t10",
    )
    [ev] = _derive_plan_events(tc, session_id="s1")
    assert ev == {
        "type": "plan_completed",
        "data": {
            "plan_id": "p1",
            "completed_count": 0,
            "failed_count": 0,
            "cancelled_count": 0,
        },
    }


def test_derive_emits_plan_failed_when_observer_saw_a_failure():
    # With observer counters: a prior fail_step makes finalize_plan emit plan_failed.
    obs = _PlanStreamObserver()
    fail = ToolCall.make(
        "mcp__fi_core_task_tracker__fail_step",
        input={"plan_id": "p1", "step_index": 0, "error": "boom"},
        id="tf",
    )
    _derive_plan_events(fail, session_id="s1", observer=obs)
    finalize = ToolCall.make(
        "mcp__fi_core_task_tracker__finalize_plan",
        input={"plan_id": "p1"},
        id="tfin",
    )
    [final_ev] = _derive_plan_events(finalize, session_id="s1", observer=obs)
    assert final_ev["type"] == "plan_failed"
    assert final_ev["data"]["failed_count"] == 1


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


class _BlockedPlanBackend:
    """Backend that yields a plan whose first step matches a blocked pattern."""

    async def run_turn_stream(self, **_kw):
        from fi_runner import TurnResult

        plan_tc = ToolCall.make(
            "mcp__fi_core_task_tracker__declare_plan",
            input={"session_id": "s1", "steps": ["drop production database", "smile"]},
            id="t1",
        )
        yield {"type": "tool_call", "tool": plan_tc}
        yield {"type": "result", "result": TurnResult(text="abort", tool_calls=[plan_tc])}


class _FinalizingBackend:
    """Backend that declares, completes, and finalizes — drives the
    plan_completed event from finalize_plan with the observer."""

    async def run_turn_stream(self, **_kw):
        from fi_runner import TurnResult

        plan_tc = ToolCall.make(
            "mcp__fi_core_task_tracker__declare_plan",
            input={"session_id": "s1", "steps": ["a"]},
            id="t1",
        )
        done_tc = ToolCall.make(
            "mcp__fi_core_task_tracker__complete_step",
            input={"plan_id": "p1", "step_index": 0, "summary": "ok"},
            id="t2",
        )
        final_tc = ToolCall.make(
            "mcp__fi_core_task_tracker__finalize_plan",
            input={"plan_id": "p1"},
            id="t3",
        )
        yield {"type": "tool_call", "tool": plan_tc}
        yield {"type": "tool_call", "tool": done_tc}
        yield {"type": "tool_call", "tool": final_tc}
        yield {"type": "result", "result": TurnResult(text="done", tool_calls=[plan_tc, done_tc, final_tc])}


@pytest.mark.asyncio
async def test_run_stream_emits_derived_plan_events_alongside_tool_calls():
    runner = Runner(
        backend=_FakeStreamingBackend(),  # type: ignore[arg-type]
        persona="t",
        extra_mcp_servers=[MCPServerSpec(name="dummy")],
    )
    events = [ev async for ev in runner.run_stream("hola", session_id="s1")]

    types = [e["type"] for e in events]
    assert "plan" in types
    assert "step_started" in types
    assert "step_done" in types
    assert types.count("tool_call") == 3

    plan_ev = next(e for e in events if e["type"] == "plan")
    # G17: request_id is always stamped on derived events.
    assert "request_id" in plan_ev["data"]
    assert plan_ev["data"]["session_id"] == "s1"
    assert plan_ev["data"]["steps"] == ["search", "scrape"]

    done_ev = next(e for e in events if e["type"] == "step_done")
    assert done_ev["data"]["status"] == "done"
    assert done_ev["data"]["summary"] == "got it"


@pytest.mark.asyncio
async def test_run_stream_emits_plan_completed_on_finalize_plan():
    runner = Runner(
        backend=_FinalizingBackend(),  # type: ignore[arg-type]
        persona="t",
        extra_mcp_servers=[MCPServerSpec(name="dummy")],
    )
    events = [ev async for ev in runner.run_stream("hola", session_id="s1")]
    types = [e["type"] for e in events]
    assert "plan_completed" in types
    final_ev = next(e for e in events if e["type"] == "plan_completed")
    assert final_ev["data"]["completed_count"] == 1
    assert final_ev["data"]["failed_count"] == 0


@pytest.mark.asyncio
async def test_run_stream_emits_plan_rejected_when_plan_guard_blocks():
    # G22: PlanGuard inspects the declared plan; on rejection, the runner
    # yields a soft ``plan_rejected`` event right after ``plan``.
    runner = Runner(
        backend=_BlockedPlanBackend(),  # type: ignore[arg-type]
        persona="t",
        extra_mcp_servers=[MCPServerSpec(name="dummy")],
        plan_guard=plan_guard(
            blocked_patterns=[r"drop\s+production"],
            reinforcement="Stay away from prod.",
        ),
    )
    events = [ev async for ev in runner.run_stream("hola", session_id="s1")]
    types = [e["type"] for e in events]
    assert types.index("plan") < types.index("plan_rejected")
    rej = next(e for e in events if e["type"] == "plan_rejected")
    assert rej["data"]["guard"] == "plan_guard"
    assert rej["data"]["matched"]
    assert "production" in rej["data"]["matched"][0]["matched_text"].lower()


def test_capability_task_tracker_resolves_to_correct_spec():
    # The capability factory builds a spec pointing at the fi-core MCP server
    # module with the contract-declared name + tools.
    from fi_runner.capabilities import resolve, task_tracker

    spec = task_tracker()
    assert spec.name == "fi_core_task_tracker"
    assert spec.args == ["-m", "fi_core.task_tracker.mcp_server"]
    assert set(spec.tools) >= {"declare_plan", "start_step", "complete_step", "fail_step"}
    # New tools surfaced by the contract are also in the capability's allowlist.
    assert {"cancel_step", "note_step", "insert_step", "replan", "cancel_plan",
            "finalize_plan", "list_plans"}.issubset(set(spec.tools))

    # resolve() includes it in the registry.
    [resolved] = resolve(["task_tracker"])
    assert resolved.name == "fi_core_task_tracker"


# --- PlanGuard unit tests --------------------------------------------------


def test_plan_guard_allows_when_blocklist_empty():
    g = PlanGuard()
    outcome = g.inspect(["search", "scrape"])
    assert outcome.allowed
    assert outcome.matched == ()


def test_plan_guard_blocks_label_matching_pattern():
    g = plan_guard(blocked_patterns=[r"\brm\s+-rf\b"])
    outcome = g.inspect(["search", "rm -rf /"])
    assert not outcome.allowed
    assert outcome.matched[0]["index"] == 1


def test_plan_guard_accepts_dict_specs_and_inspects_label_field():
    g = plan_guard(blocked_patterns=[r"prod\s+db"])
    outcome = g.inspect([{"label": "drop prod db"}, "noop"])
    assert not outcome.allowed
    assert outcome.matched[0]["matched_text"] == "drop prod db"


def test_plan_guard_custom_predicate_replaces_default():
    def deny_admin(idx, label, spec):
        is_admin = isinstance(spec, dict) and (spec.get("metadata") or {}).get("admin")
        return (not is_admin, {"reason": "admin tool denied"} if is_admin else None)

    g = PlanGuard(predicate=deny_admin)
    outcome = g.inspect([
        {"label": "list users", "metadata": {"admin": True}},
        "noop",
    ])
    assert not outcome.allowed
    assert outcome.matched[0]["reason"] == "admin tool denied"


def test_plan_guard_outcome_carries_reinforcement_for_retry():
    g = plan_guard(blocked_patterns=[r"prod"], reinforcement="No prod!")
    outcome = g.inspect(["touch prod"])
    assert outcome.reinforcement == "No prod!"
