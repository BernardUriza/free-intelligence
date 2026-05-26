"""Plan-first stream events derived from task_tracker tool calls.

The agent declares its plan via ``mcp__fi_core_task_tracker__declare_plan``
and reports each step via the related tools (see
:mod:`fi_core.task_tracker.mcp_contract`). The Runner observes those tool
calls in its stream and, for each one, re-emits a SEMANTIC event (``plan``,
``step_started``, ``step_done``, ``step_noted``, ``plan_amended``,
``plan_completed`` / ``plan_failed`` / ``plan_cancelled``) so a frontend
gets a checklist without parsing tool names.

This module is the pure translation layer (no Runner state, no MCP SDK).
The :class:`_PlanStreamObserver` is the only mutable piece, and it lives
for one turn — instantiated per :meth:`Runner.run_stream` call, dropped
when the coroutine exits."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Server name from fi_core.task_tracker.mcp_contract.MCP_SERVER_NAME. Inlined
# as a literal (not imported) to keep fi-runner dep-free of fi-core — the
# capability resolver pulls the spec lazily; this module just sees tool names.
_TASK_TRACKER_SERVER = "fi_core_task_tracker"


@dataclass
class _PlanStreamObserver:
    """Per-turn mutable state that lets the runner emit the FINAL
    ``plan_completed`` / ``plan_failed`` / ``plan_cancelled`` event when the
    agent calls ``finalize_plan`` or ``cancel_plan``.

    Why a separate object: ``_derive_plan_events`` is otherwise pure, but
    picking the terminal event type requires counting failed/cancelled steps
    seen during the turn. The observer aggregates per plan_id; on
    ``finalize_plan`` we consult the counts to choose the event.

    A note on plan_id: the value isn't in ``declare_plan``'s input (it's
    only in the tool RESULT, which the runner doesn't see). We discover
    plan_ids from ``start_step`` / ``complete_step`` / etc. — the first
    settlement that arrives bootstraps the counter."""

    # plan_id -> {"failed": int, "cancelled": int, "done": int}
    plans: dict[str, dict[str, int]] = field(default_factory=dict)

    def settle_step(self, plan_id: str | None, status: str) -> None:
        """Bump the per-plan counters. Idempotent on unknown plan_ids
        (creates the entry lazily so we don't lose a count just because
        ``declare_plan``'s id never surfaced)."""
        if not plan_id:
            return
        st = self.plans.setdefault(plan_id, {"failed": 0, "cancelled": 0, "done": 0})
        if status == "done":
            st["done"] += 1
        elif status == "failed":
            st["failed"] += 1
        elif status == "cancelled":
            st["cancelled"] += 1

    def snapshot(self, plan_id: str | None) -> dict[str, int]:
        if not plan_id or plan_id not in self.plans:
            return {"done": 0, "failed": 0, "cancelled": 0}
        return dict(self.plans[plan_id])


def _final_plan_status(snap: dict[str, int]) -> str:
    """Pick the terminal plan event from per-plan counters."""
    if snap["failed"] > 0:
        return "plan_failed"
    if snap["cancelled"] > 0 and snap["done"] == 0:
        return "plan_cancelled"
    return "plan_completed"


def _derive_plan_events(
    tool_call: Any,
    *,
    session_id: str | None,
    request_id: str | None = None,
    observer: _PlanStreamObserver | None = None,
) -> list[dict[str, Any]]:
    """Translate a task_tracker tool call into semantic stream events.

    Returns a list (often empty) of events to yield ADDITIONALLY to the raw
    ``tool_call`` event. The original tool_call still goes through — these are
    a higher-level VIEW for UIs that want a checklist instead of step soup.

    Mapping (tool → event):
      - ``declare_plan``       → ``plan``
      - ``start_step``         → ``step_started``
      - ``complete_step``      → ``step_done`` (status="done")
      - ``fail_step``          → ``step_done`` (status="failed")
      - ``cancel_step``        → ``step_done`` (status="cancelled")
      - ``note_step``          → ``step_noted``
      - ``insert_step``        → ``plan_amended`` (action="insert")
      - ``replan``             → ``plan_amended`` (action="replan")
      - ``cancel_plan``        → ``plan_cancelled``
      - ``finalize_plan``      → ``plan_completed`` (or ``plan_failed`` if the observer saw failures)

    Every event payload carries ``request_id`` when provided — UIs that
    multiplex concurrent turns key state on it.

    Robust to a missing ``tool.input`` (codex doesn't capture inputs for MCP
    tool calls — see ``CodexBackend._tool_call_from_item``). Without input we
    can't reconstruct the payload, so we drop silently (the raw tool_call
    still goes through for the generic UI)."""
    if getattr(tool_call, "server", None) != _TASK_TRACKER_SERVER:
        return []
    name = getattr(tool_call, "name", "") or ""
    # name is mcp__fi_core_task_tracker__<tool>; strip prefix to get the tool.
    suffix = name.rsplit("__", 1)[-1]
    inp = getattr(tool_call, "input", None) or {}

    def _data(**fields: Any) -> dict[str, Any]:
        # Stamp request_id when present so a UI multiplexing concurrent turns
        # can route events to the right transcript without re-parsing names.
        if request_id is not None:
            return {"request_id": request_id, **fields}
        return fields

    if suffix == "declare_plan":
        steps = inp.get("steps")
        if not isinstance(steps, list):
            return []
        return [{"type": "plan", "data": _data(
            session_id=inp.get("session_id") or session_id,
            steps=list(steps),
        )}]

    if suffix == "start_step":
        return [{"type": "step_started", "data": _data(
            plan_id=inp.get("plan_id"),
            step_index=inp.get("step_index"),
        )}]

    if suffix in ("complete_step", "fail_step", "cancel_step"):
        status = {"complete_step": "done", "fail_step": "failed", "cancel_step": "cancelled"}[suffix]
        plan_id = inp.get("plan_id")
        payload: dict[str, Any] = {
            "plan_id": plan_id,
            "step_index": inp.get("step_index"),
            "status": status,
        }
        if status == "done":
            payload["summary"] = inp.get("summary", "")
        else:
            # both fail_step and cancel_step carry a reason in ``error`` /
            # ``reason``; we surface either under ``error`` for the wire.
            payload["error"] = inp.get("error") or inp.get("reason", "")
        if observer is not None:
            observer.settle_step(plan_id, status)
        return [{"type": "step_done", "data": _data(**payload)}]

    if suffix == "note_step":
        return [{"type": "step_noted", "data": _data(
            plan_id=inp.get("plan_id"),
            step_index=inp.get("step_index"),
            note=inp.get("note", ""),
        )}]

    if suffix in ("insert_step", "replan"):
        return [{"type": "plan_amended", "data": _data(
            plan_id=inp.get("plan_id"),
            action="insert" if suffix == "insert_step" else "replan",
        )}]

    if suffix == "cancel_plan":
        return [{"type": "plan_cancelled", "data": _data(
            plan_id=inp.get("plan_id"),
            reason=inp.get("reason", ""),
        )}]

    if suffix == "finalize_plan":
        # Pick the terminal event from observer counters when available; fall
        # back to ``plan_completed`` since finalize without prior failures
        # means "ship as-is".
        plan_id = inp.get("plan_id")
        if observer is not None:
            snap = observer.snapshot(plan_id)
            return [{"type": _final_plan_status(snap), "data": _data(
                plan_id=plan_id,
                completed_count=snap["done"],
                failed_count=snap["failed"],
                cancelled_count=snap["cancelled"],
            )}]
        return [{"type": "plan_completed", "data": _data(plan_id=plan_id)}]

    return []


__all__ = [
    "_PlanStreamObserver",
    "_derive_plan_events",
    "_final_plan_status",
    "_TASK_TRACKER_SERVER",
]
