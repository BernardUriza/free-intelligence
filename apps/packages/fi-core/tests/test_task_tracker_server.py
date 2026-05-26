"""Tests for the task_tracker MCP server's tool handlers (boundary layer).

The tracker is the pure core — these tests verify the JSON-shape contract
of every MCP tool: success payloads, structured error codes, session
mismatch mapping, and that the handlers route to the correct tracker method.

We swap the module-level ``_TRACKER`` for an isolated instance per test via
the ``_get_tracker()`` indirection so tests don't share state. Skipped
entirely when ``fi-core[mcp]`` isn't installed (the server module imports
the SDK at module load time)."""

from __future__ import annotations

import asyncio

import pytest

mcp_server = pytest.importorskip("fi_core.task_tracker.mcp_server", exc_type=ImportError)
from fi_core.task_tracker import TaskTracker  # noqa: E402
from fi_core.task_tracker._server import registry as _registry  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_tracker(monkeypatch):
    """Reset the singleton tracker before each test for isolation.

    The actual storage lives in :mod:`fi_core.task_tracker._server.registry`;
    ``mcp_server.py`` reads it via ``get_tracker()``. Patch the registry's
    module-level ``_TRACKER`` so every handler picks up the fresh instance."""
    fresh = TaskTracker()
    monkeypatch.setattr(_registry, "_TRACKER", fresh)
    return fresh


def _run(coro):
    return asyncio.run(coro)


# --- declare_plan -----------------------------------------------------------


def test_declare_plan_returns_plan_id_and_step_count():
    result = _run(mcp_server.declare_plan("s1", ["a", "b"]))
    assert set(result.keys()) == {"plan_id", "step_count"}
    assert result["step_count"] == 2
    assert len(result["plan_id"]) == 16  # 64-bit hex


def test_declare_plan_empty_steps_returns_structured_error():
    result = _run(mcp_server.declare_plan("s1", []))
    assert result["code"] == "invalid_steps"
    assert "empty" in result["error"]


def test_declare_plan_invalid_forward_dep_returns_structured_error():
    result = _run(mcp_server.declare_plan("s1", [{"label": "a", "depends_on": [1]}, {"label": "b"}]))
    assert result["code"] == "invalid_steps"


def test_declare_plan_accepts_dict_specs_with_active_form_and_metadata():
    result = _run(mcp_server.declare_plan("s1", [
        {"label": "search", "active_form": "Searching", "metadata": {"src": "serp"}},
    ]))
    assert result["step_count"] == 1


# --- start_step / complete_step --------------------------------------------


def test_start_step_returns_step_dict_with_status_running():
    plan = _run(mcp_server.declare_plan("s1", ["a"]))
    result = _run(mcp_server.start_step(plan["plan_id"], 0, session_id="s1"))
    assert result["status"] == "running"
    assert result["plan_id"] == plan["plan_id"]
    assert result["label"] == "a"


def test_complete_step_returns_done_and_includes_summary_if_provided():
    plan = _run(mcp_server.declare_plan("s1", ["a"]))
    _run(mcp_server.start_step(plan["plan_id"], 0))
    result = _run(mcp_server.complete_step(plan["plan_id"], 0, "found it"))
    assert result["status"] == "done"
    assert result["summary"] == "found it"


def test_complete_step_omits_summary_field_when_empty():
    plan = _run(mcp_server.declare_plan("s1", ["a"]))
    result = _run(mcp_server.complete_step(plan["plan_id"], 0))
    assert "summary" not in result  # only present when non-empty


def test_start_step_unknown_plan_returns_structured_not_found():
    result = _run(mcp_server.start_step("ghost", 0))
    assert result["code"] == "plan_not_found"


def test_start_step_with_wrong_session_returns_session_mismatch():
    plan = _run(mcp_server.declare_plan("alice", ["a"]))
    result = _run(mcp_server.start_step(plan["plan_id"], 0, session_id="bob"))
    assert result["code"] == "session_mismatch"


def test_complete_step_twice_returns_step_terminal_error():
    plan = _run(mcp_server.declare_plan("s1", ["a"]))
    _run(mcp_server.complete_step(plan["plan_id"], 0))
    result = _run(mcp_server.complete_step(plan["plan_id"], 0))
    assert result["code"] == "step_terminal"


def test_start_step_with_unmet_dependency_returns_dependency_unmet():
    plan = _run(mcp_server.declare_plan("s1", [
        {"label": "build"}, {"label": "test", "depends_on": [0]},
    ]))
    result = _run(mcp_server.start_step(plan["plan_id"], 1))
    assert result["code"] == "dependency_unmet"


# --- fail / cancel / note --------------------------------------------------


def test_fail_step_returns_failed_with_error_field():
    plan = _run(mcp_server.declare_plan("s1", ["a"]))
    _run(mcp_server.start_step(plan["plan_id"], 0))
    result = _run(mcp_server.fail_step(plan["plan_id"], 0, "boom"))
    assert result["status"] == "failed"
    assert result["error"] == "boom"


def test_cancel_step_returns_cancelled():
    plan = _run(mcp_server.declare_plan("s1", ["a"]))
    _run(mcp_server.start_step(plan["plan_id"], 0))
    result = _run(mcp_server.cancel_step(plan["plan_id"], 0, "user abort"))
    assert result["status"] == "cancelled"


def test_note_step_returns_step_with_notes_list():
    plan = _run(mcp_server.declare_plan("s1", ["a"]))
    _run(mcp_server.start_step(plan["plan_id"], 0))
    _run(mcp_server.note_step(plan["plan_id"], 0, "halfway"))
    result = _run(mcp_server.note_step(plan["plan_id"], 0, "almost done"))
    assert result["notes"] == ["halfway", "almost done"]


# --- replanning ------------------------------------------------------------


def test_insert_step_at_head_returns_updated_plan_summary():
    plan = _run(mcp_server.declare_plan("s1", ["build", "test"]))
    result = _run(mcp_server.insert_step(plan["plan_id"], -1, "lint"))
    assert result["step_count"] == 3
    assert result["status"] == "declared"


def test_insert_step_on_terminal_plan_returns_plan_terminal_error():
    plan = _run(mcp_server.declare_plan("s1", ["a"]))
    _run(mcp_server.complete_step(plan["plan_id"], 0))
    result = _run(mcp_server.insert_step(plan["plan_id"], 0, "b"))
    assert result["code"] == "plan_terminal"


def test_replan_replaces_tail():
    plan = _run(mcp_server.declare_plan("s1", ["a", "b", "c"]))
    _run(mcp_server.complete_step(plan["plan_id"], 0))
    result = _run(mcp_server.replan(plan["plan_id"], 1, ["new_b", "new_c"]))
    assert result["step_count"] == 3


def test_replan_with_empty_new_steps_returns_invalid():
    plan = _run(mcp_server.declare_plan("s1", ["a"]))
    result = _run(mcp_server.replan(plan["plan_id"], 0, []))
    assert result["code"] == "invalid_new_steps"


# --- closure ---------------------------------------------------------------


def test_cancel_plan_returns_cancelled_plan_summary():
    plan = _run(mcp_server.declare_plan("s1", ["a", "b"]))
    result = _run(mcp_server.cancel_plan(plan["plan_id"], "user abort"))
    assert result["status"] == "cancelled"


def test_finalize_plan_returns_completed_when_all_settled_clean():
    plan = _run(mcp_server.declare_plan("s1", ["a", "b"]))
    _run(mcp_server.complete_step(plan["plan_id"], 0))
    result = _run(mcp_server.finalize_plan(plan["plan_id"]))
    assert result["status"] == "completed"


# --- introspection ---------------------------------------------------------


def test_list_plans_returns_plans_for_session_only():
    _run(mcp_server.declare_plan("alice", ["a"]))
    _run(mcp_server.declare_plan("bob", ["b"]))
    result = _run(mcp_server.list_plans("alice"))
    assert len(result["plans"]) == 1
    assert result["plans"][0]["status"] == "declared"


def test_list_plans_empty_session_returns_empty_list():
    result = _run(mcp_server.list_plans("nobody"))
    assert result == {"plans": []}
