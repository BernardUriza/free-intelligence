"""Tests for the TaskTracker — pure (no MCP SDK), unit-testable in isolation.

The MCP server module is a thin adapter over this; if the tracker is correct,
the server's surface is mechanically correct too. The contract itself
(MCP_TOOLS shape) is checked under test_task_tracker_contract.

Coverage includes the v2 surface:
  - DAG dependencies between steps (depends_on)
  - Terminal-state immutability (DONE/FAILED/SKIPPED/CANCELLED are append-only)
  - Idempotent start_step on RUNNING
  - Session auth binding (cross-session access raises SessionMismatch)
  - Replanning: insert_step, replan, cancel_plan, cancel_step
  - Notes append (note_step) and finalize_plan auto-SKIP
  - 64-bit plan IDs and TTL eviction
"""

from __future__ import annotations

import asyncio
import time

import pytest

from fi_core.task_tracker import (
    MCP_EVENTS,
    MCP_SERVER_NAME,
    MCP_TOOLS,
    DependencyUnmet,
    Plan,
    PlanAlreadyTerminal,
    PlanNotFound,
    PlanStatus,
    SessionMismatch,
    StepAlreadyTerminal,
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


def test_contract_exposes_the_full_toolset_with_descriptions():
    names = {t["name"] for t in MCP_TOOLS}
    # Lifecycle + replanning + closure + introspection — 11 tools total.
    assert names == {
        "declare_plan", "start_step", "complete_step", "fail_step",
        "cancel_step", "note_step",
        "insert_step", "replan",
        "cancel_plan", "finalize_plan",
        "list_plans",
    }
    # Every tool has a non-trivial description so the LLM picks the right one.
    assert all(len(t["description"]) > 40 for t in MCP_TOOLS)


def test_contract_documents_every_stream_event():
    # The wire-side companion: fi-runner emits these events; frontends switch
    # on the names. Names must stay stable — they're a public contract.
    event_names = {e["name"] for e in MCP_EVENTS}
    assert event_names == {
        "plan", "step_started", "step_done", "step_noted",
        "plan_amended",
        "plan_completed", "plan_failed", "plan_cancelled",
    }


# --- declare_plan: shape + validation ---------------------------------------


def test_declare_plan_creates_plan_with_pending_steps_from_string_labels():
    t = TaskTracker()
    plan = t.declare_plan(session_id="s1", steps=["search", "scrape", "synthesize"])
    assert isinstance(plan, Plan)
    assert plan.session_id == "s1"
    assert plan.status is PlanStatus.DECLARED
    assert plan.step_count == 3
    assert [s.label for s in plan.steps] == ["search", "scrape", "synthesize"]
    assert all(s.status is StepStatus.PENDING for s in plan.steps)
    assert all(s.duration_ms is None for s in plan.steps)
    assert all(s.depends_on == () for s in plan.steps)
    assert all(s.metadata is None for s in plan.steps)


def test_declare_plan_accepts_dict_specs_with_active_form_metadata_and_deps():
    t = TaskTracker()
    plan = t.declare_plan(session_id="s1", steps=[
        {"label": "search", "active_form": "Searching", "metadata": {"k": "v"}},
        {"label": "scrape", "depends_on": [0], "active_form": "Scraping"},
    ])
    assert plan.steps[0].active_form == "Searching"
    assert plan.steps[0].metadata == {"k": "v"}
    assert plan.steps[1].depends_on == (0,)


def test_declare_plan_empty_steps_raises_value_error():
    t = TaskTracker()
    with pytest.raises(ValueError, match="must not be empty"):
        t.declare_plan(session_id="s1", steps=[])


def test_declare_plan_forward_dependency_rejected_to_prevent_cycles():
    # A step can only depend on EARLIER steps — index >= self.index is illegal.
    t = TaskTracker()
    with pytest.raises(ValueError, match="invalid"):
        t.declare_plan(session_id="s1", steps=[
            {"label": "a", "depends_on": [1]},  # forward ref
            {"label": "b"},
        ])


def test_declare_plan_returns_64bit_unique_plan_ids():
    # 64 bits = 16 hex chars; was 48 bits (12 hex). Collision-safe for the
    # realistic in-memory volume.
    t = TaskTracker()
    a = t.declare_plan(session_id="s1", steps=["a"])
    b = t.declare_plan(session_id="s1", steps=["a"])
    assert len(a.plan_id) == 16
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


# --- G11 idempotency / G10 terminal immutability ----------------------------


def test_start_step_is_idempotent_on_running_step_and_preserves_t0():
    # Calling start_step twice on a RUNNING step must NOT reset t0 — otherwise
    # duration_ms would be wrong by the gap between the two calls.
    async def _run():
        t = TaskTracker()
        p = t.declare_plan(session_id="s1", steps=["a"])
        first = t.start_step(p.plan_id, 0)
        await asyncio.sleep(0.05)
        second = t.start_step(p.plan_id, 0)  # idempotent
        assert second.status is StepStatus.RUNNING
        # If we'd reset t0, duration would be ~0; instead it should be ~50ms+.
        step = t.complete_step(p.plan_id, 0)
        assert step.duration_ms is not None and step.duration_ms >= 40
        # Identity check: idempotent calls return the same step.
        assert first.index == second.index

    asyncio.run(_run())


def test_complete_step_after_complete_step_raises_terminal():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    t.complete_step(p.plan_id, 0)
    with pytest.raises(StepAlreadyTerminal):
        t.complete_step(p.plan_id, 0)


def test_complete_step_after_fail_step_raises_terminal_no_overwrite():
    # G10: terminal states are append-only. A late retry of complete after
    # the step failed must NOT silently overwrite FAILED with DONE.
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    t.start_step(p.plan_id, 0)
    t.fail_step(p.plan_id, 0, error="boom")
    with pytest.raises(StepAlreadyTerminal):
        t.complete_step(p.plan_id, 0, summary="recovered")
    # FAILED is preserved.
    assert t.get(p.plan_id).steps[0].status is StepStatus.FAILED
    assert t.get(p.plan_id).steps[0].error == "boom"


def test_start_step_on_terminal_step_raises():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    t.complete_step(p.plan_id, 0)
    with pytest.raises(StepAlreadyTerminal):
        t.start_step(p.plan_id, 0)


# --- G6 DAG dependencies ---------------------------------------------------


def test_start_step_raises_dependency_unmet_when_dep_not_done():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=[
        {"label": "build"},
        {"label": "test", "depends_on": [0]},
    ])
    with pytest.raises(DependencyUnmet, match="depends on step 0"):
        t.start_step(p.plan_id, 1)


def test_start_step_allows_dependent_once_dep_is_done():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=[
        {"label": "build"},
        {"label": "test", "depends_on": [0]},
    ])
    t.complete_step(p.plan_id, 0)
    step = t.start_step(p.plan_id, 1)
    assert step.status is StepStatus.RUNNING


# --- G12 session auth binding ----------------------------------------------


def test_get_with_wrong_session_id_raises_session_mismatch():
    t = TaskTracker()
    p = t.declare_plan(session_id="alice", steps=["a"])
    with pytest.raises(SessionMismatch):
        t.get(p.plan_id, session_id="bob")


def test_start_step_with_wrong_session_id_raises_session_mismatch():
    t = TaskTracker()
    p = t.declare_plan(session_id="alice", steps=["a"])
    with pytest.raises(SessionMismatch):
        t.start_step(p.plan_id, 0, session_id="bob")


def test_get_without_session_id_skips_check_for_internal_callers():
    # The MCP boundary always passes session_id; internal callers (e.g.
    # tests, the runner's introspection) may omit it.
    t = TaskTracker()
    p = t.declare_plan(session_id="alice", steps=["a"])
    assert t.get(p.plan_id) is t.get(p.plan_id)  # no raise


# --- fail_step / cancel_step ------------------------------------------------


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


def test_cancel_step_marks_cancelled_and_flips_plan_to_cancelled_when_no_done():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    t.start_step(p.plan_id, 0)
    step = t.cancel_step(p.plan_id, 0, reason="user abort")
    assert step.status is StepStatus.CANCELLED
    assert step.error == "user abort"
    assert t.get(p.plan_id).status is PlanStatus.CANCELLED


def test_cancel_step_yields_completed_plan_when_other_steps_succeeded():
    # cancellation isn't an error — a plan with 1 DONE + 1 CANCELLED is
    # COMPLETED (no FAILED, and we have at least one DONE).
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b"])
    t.complete_step(p.plan_id, 0)
    t.cancel_step(p.plan_id, 1, reason="not needed")
    assert t.get(p.plan_id).status is PlanStatus.COMPLETED


# --- G16 note_step (append-only) -------------------------------------------


def test_note_step_appends_without_overwriting():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    t.start_step(p.plan_id, 0)
    t.note_step(p.plan_id, 0, "first")
    t.note_step(p.plan_id, 0, "second")
    step = t.get(p.plan_id).steps[0]
    assert step.notes == ("first", "second")
    # Step is still RUNNING — notes don't settle it.
    assert step.status is StepStatus.RUNNING


def test_note_step_on_terminal_step_raises():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    t.complete_step(p.plan_id, 0)
    with pytest.raises(StepAlreadyTerminal):
        t.note_step(p.plan_id, 0, "too late")


def test_note_step_empty_note_is_noop():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    t.start_step(p.plan_id, 0)
    t.note_step(p.plan_id, 0, "")
    assert t.get(p.plan_id).steps[0].notes == ()


# --- G2 finalize_plan + G8 insert_step / replan ----------------------------


def test_finalize_plan_skips_pending_and_flips_to_completed():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b", "c"])
    t.complete_step(p.plan_id, 0)
    # 1 DONE, 2 PENDING. Finalize should SKIP the pending and settle COMPLETED.
    final = t.finalize_plan(p.plan_id)
    assert final.status is PlanStatus.COMPLETED
    assert [s.status for s in final.steps] == [
        StepStatus.DONE, StepStatus.SKIPPED, StepStatus.SKIPPED,
    ]


def test_finalize_plan_with_failure_settles_to_failed():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b"])
    t.start_step(p.plan_id, 0)
    t.fail_step(p.plan_id, 0)
    final = t.finalize_plan(p.plan_id)
    assert final.status is PlanStatus.FAILED


def test_finalize_plan_is_idempotent_on_terminal():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    t.complete_step(p.plan_id, 0)
    first = t.finalize_plan(p.plan_id)
    second = t.finalize_plan(p.plan_id)
    assert first.status is second.status


def test_insert_step_at_head_renumbers_and_bumps_deps():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=[
        {"label": "build"},
        {"label": "test", "depends_on": [0]},
    ])
    new_plan = t.insert_step(p.plan_id, after_index=-1, spec="lint")
    assert [s.label for s in new_plan.steps] == ["lint", "build", "test"]
    # The "test" step depended on index 0 (build); after prepending,
    # build is at index 1 and the dep should bump to 1.
    assert new_plan.steps[2].depends_on == (1,)


def test_insert_step_in_middle_shifts_only_later_steps():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b", "c"])
    new_plan = t.insert_step(p.plan_id, after_index=0, spec="aa")
    assert [s.label for s in new_plan.steps] == ["a", "aa", "b", "c"]
    assert [s.index for s in new_plan.steps] == [0, 1, 2, 3]


def test_insert_step_on_terminal_plan_raises():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a"])
    t.complete_step(p.plan_id, 0)
    with pytest.raises(PlanAlreadyTerminal):
        t.insert_step(p.plan_id, after_index=0, spec="b")


def test_replan_replaces_tail_keeping_terminal_prefix():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b", "c"])
    t.complete_step(p.plan_id, 0)
    new_plan = t.replan(p.plan_id, from_index=1, new_steps=["new_b", "new_c", "new_d"])
    labels = [s.label for s in new_plan.steps]
    assert labels == ["a", "new_b", "new_c", "new_d"]
    # The kept prefix's DONE step is preserved as DONE.
    assert new_plan.steps[0].status is StepStatus.DONE


def test_replan_refuses_when_kept_step_is_running():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b"])
    t.start_step(p.plan_id, 0)
    # Can't replan past a RUNNING step without cancelling it first.
    with pytest.raises(StepAlreadyTerminal):
        t.replan(p.plan_id, from_index=1, new_steps=["new_b"])


def test_cancel_plan_marks_in_flight_steps_cancelled():
    t = TaskTracker()
    p = t.declare_plan(session_id="s1", steps=["a", "b", "c"])
    t.complete_step(p.plan_id, 0)
    t.start_step(p.plan_id, 1)
    cancelled = t.cancel_plan(p.plan_id, reason="user abort")
    assert cancelled.status is PlanStatus.CANCELLED
    # DONE stays DONE; RUNNING and PENDING flip to CANCELLED.
    assert cancelled.steps[0].status is StepStatus.DONE
    assert cancelled.steps[1].status is StepStatus.CANCELLED
    assert cancelled.steps[2].status is StepStatus.CANCELLED


# --- G1 TTL eviction -------------------------------------------------------


def test_ttl_eviction_purges_expired_plans():
    # Very short TTL so the test runs fast. The tracker should evict on the
    # next read after the TTL window.
    t = TaskTracker(ttl_seconds=0.05)
    p = t.declare_plan(session_id="s1", steps=["a"])
    time.sleep(0.10)
    with pytest.raises(PlanNotFound):
        t.get(p.plan_id)


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
