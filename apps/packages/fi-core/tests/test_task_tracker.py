"""Tests for the TaskTracker — pure (no MCP SDK), unit-testable in isolation.

The MCP server module is a thin adapter over this; if the tracker is correct,
the server's surface is mechanically correct too. The contract itself
(MCP_TOOLS shape) is checked under test_task_tracker_contract."""

from __future__ import annotations

import asyncio

import pytest

from fi_core.task_tracker import (
    MCP_EVENTS,
    MCP_SERVER_NAME,
    MCP_TOOLS,
    Plan,
    PlanNotFound,
    PlanStatus,
    StepIndexInvalid,
    StepStatus,
    TaskTracker,
)


# --- contract: zero-dep metadata -------------------------------------------


def test_contract_server_name_matches_convention():
    # The runner builds mcp__<server>__<tool> ids from this name; ``__`` in the
    # server name would break round-tripping. Single-token name only.
    assert "__" not in MCP_SERVER_NAME
    assert MCP_SERVER_NAME == "fi_core_task_tracker"


def test_contract_exposes_the_four_tools_with_descriptions():
    names = [t["name"] for t in MCP_TOOLS]
    assert names == ["declare_plan", "start_step", "complete_step", "fail_step"]
    # Every tool has a non-trivial description so the LLM picks the right one.
    assert all(len(t["description"]) > 40 for t in MCP_TOOLS)


def test_contract_documents_the_stream_events():
    # The wire-side companion: fi-runner emits these events; frontends switch
    # on the names. Names must stay stable — they're a public contract.
    event_names = {e["name"] for e in MCP_EVENTS}
    assert event_names == {"plan", "step_started", "step_done"}


# --- declare_plan ----------------------------------------------------------


def test_declare_plan_creates_plan_with_pending_steps():
    t = TaskTracker()
    plan = t.declare_plan(session_id="s1", steps=["search", "scrape", "synthesize"])
    assert isinstance(plan, Plan)
    assert plan.session_id == "s1"
    assert plan.status is PlanStatus.DECLARED
    assert plan.step_count == 3
    assert [s.label for s in plan.steps] == ["search", "scrape", "synthesize"]
    assert all(s.status is StepStatus.PENDING for s in plan.steps)
    assert all(s.duration_ms is None for s in plan.steps)


def test_declare_plan_returns_unique_plan_ids():
    t = TaskTracker()
    a = t.declare_plan(session_id="s1", steps=["a"])
    b = t.declare_plan(session_id="s1", steps=["a"])
    assert a.plan_id != b.plan_id


def test_list_for_session_scopes_by_session_id():
    t = TaskTracker()
    a = t.declare_plan(session_id="s1", steps=["x"])
    _ = t.declare_plan(session_id="s2", steps=["y"])
    s1_plans = t.list_for_session("s1")
    assert len(s1_plans) == 1 and s1_plans[0].plan_id == a.plan_id


# --- start_step / complete_step --------------------------------------------


def test_start_step_flips_step_to_running_and_plan_to_running():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b"])
    step = t.start_step(p.plan_id, 0)
    assert step.status is StepStatus.RUNNING
    assert t.get(p.plan_id).status is PlanStatus.RUNNING


def test_complete_step_records_duration_and_keeps_plan_running_if_more_pending():
    async def _run():
        t = TaskTracker()
        p = t.declare_plan(session_id="s1", steps=["a", "b"])
        t.start_step(p.plan_id, 0)
        await asyncio.sleep(0.04)  # 40ms; CI-safe margin
        step = t.complete_step(p.plan_id, 0, summary="found 3")
        assert step.status is StepStatus.DONE
        assert step.duration_ms is not None and step.duration_ms >= 30
        assert step.summary == "found 3"
        # 1 of 2 done — plan stays RUNNING
        assert t.get(p.plan_id).status is PlanStatus.RUNNING

    asyncio.run(_run())


def test_complete_step_flips_plan_to_completed_when_all_done():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b"])
    t.start_step(p.plan_id, 0)
    t.complete_step(p.plan_id, 0)
    t.start_step(p.plan_id, 1)
    t.complete_step(p.plan_id, 1)
    assert t.get(p.plan_id).status is PlanStatus.COMPLETED


def test_complete_step_without_start_leaves_duration_none():
    # An agent that skips start_step still gets a clean DONE — the tracker
    # doesn't fabricate a t0. duration_ms None signals "unknown", not zero.
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    step = t.complete_step(p.plan_id, 0)
    assert step.status is StepStatus.DONE
    assert step.duration_ms is None


# --- fail_step --------------------------------------------------------------


def test_fail_step_propagates_to_plan_status_failed():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b"])
    t.start_step(p.plan_id, 0)
    t.fail_step(p.plan_id, 0, error="boom")
    t.start_step(p.plan_id, 1)
    t.complete_step(p.plan_id, 1)
    # One failed step → plan failed, even if the other one succeeded.
    final = t.get(p.plan_id)
    assert final.status is PlanStatus.FAILED
    assert final.failed_count == 1
    assert final.completed_count == 1
    assert final.steps[0].error == "boom"


# --- error paths ------------------------------------------------------------


def test_unknown_plan_id_raises_plan_not_found():
    t = TaskTracker()
    with pytest.raises(PlanNotFound):
        t.start_step("no-such-plan", 0)


def test_out_of_range_step_index_raises():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["only-one"])
    with pytest.raises(StepIndexInvalid):
        t.start_step(p.plan_id, 5)
    with pytest.raises(StepIndexInvalid):
        t.complete_step(p.plan_id, -1)
