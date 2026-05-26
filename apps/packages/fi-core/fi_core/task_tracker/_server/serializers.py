"""Wire serializers — turn :class:`Plan` / :class:`Step` into the JSON shape
the MCP server returns to the agent.

Kept pure (no MCP SDK, no tracker dep) so they're trivially unit-testable
and a future non-MCP transport (e.g. a REST shim) can reuse them without
pulling FastMCP."""

from __future__ import annotations

from typing import Any

from ..models import Plan, Step


def step_dict(plan_id: str, step: Step) -> dict[str, Any]:
    """Serialize a :class:`Step` for the wire.

    Optional fields are OMITTED rather than sent as null/empty — keeps the
    payload tight and makes the receiver's job easier (a missing key is
    "doesn't apply", not "the value was nullish"). ``status`` is always the
    enum's string value (the enum subclasses ``str``)."""
    out: dict[str, Any] = {
        "plan_id": plan_id,
        "step_index": step.index,
        "label": step.label,
        "status": step.status.value,
    }
    if step.duration_ms is not None:
        out["duration_ms"] = step.duration_ms
    if step.summary:
        out["summary"] = step.summary
    if step.error:
        out["error"] = step.error
    if step.active_form:
        out["active_form"] = step.active_form
    if step.depends_on:
        out["depends_on"] = list(step.depends_on)
    if step.notes:
        out["notes"] = list(step.notes)
    if step.metadata:
        out["metadata"] = step.metadata
    return out


def plan_summary_dict(plan: Plan) -> dict[str, Any]:
    """Serialize a :class:`Plan` as a compact summary — counters only, no
    nested step list. Used by ``list_plans`` and by replanning tools that
    return the updated shape without forcing the agent to re-walk every step."""
    return {
        "plan_id": plan.plan_id,
        "status": plan.status.value,
        "step_count": plan.step_count,
        "completed_count": plan.completed_count,
        "failed_count": plan.failed_count,
        "cancelled_count": plan.cancelled_count,
    }


def error_payload(message: str, *, code: str = "task_tracker_error") -> dict[str, Any]:
    """Structured error payload — same shape across every tool.

    The contract is ``{"error": <str>, "code": <str>}``; the boundary's
    consumers (fi-runner, custom clients) can branch on ``code`` without
    parsing the prose."""
    return {"error": message, "code": code}
