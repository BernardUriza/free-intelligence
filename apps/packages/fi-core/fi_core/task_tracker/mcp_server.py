"""FastMCP server for the task tracker — agent-facing.

Spawned as ``python -m fi_core.task_tracker.mcp_server`` by fi-runner's
``task_tracker`` capability. The server holds a SINGLE process-wide
:class:`TaskTracker` instance (so multiple sessions share storage but never
see each other's plans — scoping is by ``session_id`` on the tracker itself).

Each tool is a thin async wrapper around the tracker; the server's only job
is JSON-RPC framing + structured error responses. The agent calls these tools
and fi-runner observes the calls to emit ``plan`` / ``step_started`` /
``step_done`` stream events (see :mod:`mcp_contract` for the wire shape).

Requires ``fi-core[mcp]``."""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "fi_core.task_tracker.mcp_server requires the MCP SDK. Install via: pip install 'fi-core[mcp]'"
    ) from e

from .mcp_contract import MCP_SERVER_NAME
from .tracker import PlanNotFound, StepIndexInvalid, TaskTracker


# Process-wide singleton: every tool call in this server lands here. Cheap
# (in-memory dict) and intentionally non-persistent — plans live for a turn.
_TRACKER = TaskTracker()


def _get_tracker() -> TaskTracker:
    """Indirection so tests can swap the global tracker for an isolated one."""
    return _TRACKER


mcp = FastMCP(MCP_SERVER_NAME)


@mcp.tool()
async def declare_plan(session_id: str, steps: list[str]) -> dict:
    """Declare the ordered plan you're about to execute. Call this FIRST.

    Returns ``{"plan_id": str, "step_count": int}``.

    Raises (via structured error response) when ``steps`` is empty — a plan
    must have at least one step; otherwise the consumer's UI would show an
    empty checklist that never moves."""
    if not steps:
        return {"error": "steps must not be empty"}
    plan = _get_tracker().declare_plan(session_id=session_id, steps=steps)
    return {"plan_id": plan.plan_id, "step_count": plan.step_count}


@mcp.tool()
async def start_step(plan_id: str, step_index: int) -> dict:
    """Mark step ``step_index`` of ``plan_id`` as RUNNING. Returns the
    updated step as a dict, or an error payload on bad id / index."""
    try:
        step = _get_tracker().start_step(plan_id=plan_id, step_index=step_index)
    except PlanNotFound:
        return {"error": f"plan_id {plan_id!r} not found"}
    except StepIndexInvalid as e:
        return {"error": str(e)}
    return {"plan_id": plan_id, "step_index": step.index, "label": step.label, "status": step.status.value}


@mcp.tool()
async def complete_step(plan_id: str, step_index: int, summary: str = "") -> dict:
    """Mark step ``step_index`` DONE. ``summary`` is optional (one-line result)."""
    try:
        step = _get_tracker().complete_step(plan_id=plan_id, step_index=step_index, summary=summary)
    except PlanNotFound:
        return {"error": f"plan_id {plan_id!r} not found"}
    except StepIndexInvalid as e:
        return {"error": str(e)}
    return {
        "plan_id": plan_id,
        "step_index": step.index,
        "status": step.status.value,
        "duration_ms": step.duration_ms,
        "summary": step.summary,
    }


@mcp.tool()
async def fail_step(plan_id: str, step_index: int, error: str = "") -> dict:
    """Mark step ``step_index`` FAILED. The plan goes to FAILED overall."""
    try:
        step = _get_tracker().fail_step(plan_id=plan_id, step_index=step_index, error=error)
    except PlanNotFound:
        return {"error": f"plan_id {plan_id!r} not found"}
    except StepIndexInvalid as e:
        return {"error": str(e)}
    return {
        "plan_id": plan_id,
        "step_index": step.index,
        "status": step.status.value,
        "duration_ms": step.duration_ms,
        "error": step.error,
    }


if __name__ == "__main__":
    # stdio transport — what fi-runner's MCPServerSpec(command=python, args=[-m, ...]) spawns.
    mcp.run()
