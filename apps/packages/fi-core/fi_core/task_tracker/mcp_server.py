"""FastMCP server for the task tracker — agent-facing.

Spawned as ``python -m fi_core.task_tracker.mcp_server`` by fi-runner's
``task_tracker`` capability. Each ``@mcp.tool()`` here is a thin adapter:

  1. Open a :func:`tracker_call` context (maps tracker exceptions to MCP
     error codes — see :mod:`._server.errors`).
  2. Call exactly one tracker method.
  3. Serialize the result via :func:`step_dict` / :func:`plan_summary_dict`
     (see :mod:`._server.serializers`).

All the boilerplate (try/except per error type, JSON shape) lives in
``_server/``; this file is the wire surface only. Requires ``fi-core[mcp]``.

Backward-compat note: tests import ``_TRACKER`` from this module and
``monkeypatch.setattr(mcp_server, "_TRACKER", fresh)`` to isolate state.
We re-export the registry singleton + ``_get_tracker`` indirection so
existing tests keep working without changes."""

from __future__ import annotations

from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "fi_core.task_tracker.mcp_server requires the MCP SDK. Install via: pip install 'fi-core[mcp]'"
    ) from e

from ._server import (
    get_tracker as _get_tracker,
    plan_summary_dict,
    step_dict,
    tracker_call,
)
from ._server import registry as _registry
from .mcp_contract import MCP_SERVER_NAME

# Backward-compat: keep the module-level ``_TRACKER`` name so existing
# tests' monkeypatching keeps working. Both lookups route through the
# same singleton in ``_server.registry``.
_TRACKER = _registry._TRACKER  # noqa: SLF001 — intentional cross-module alias for test hooks


mcp = FastMCP(MCP_SERVER_NAME)


# --- lifecycle tools --------------------------------------------------------


@mcp.tool()
async def declare_plan(session_id: str, steps: list[Any]) -> dict[str, Any]:
    """Declare the ordered plan you're about to execute. Call this FIRST.

    Returns ``{"plan_id": str, "step_count": int}``."""
    with tracker_call(value_error_code="invalid_steps") as r:
        plan = _get_tracker().declare_plan(session_id=session_id, steps=steps)
    if r.failed:
        return r.error  # type: ignore[return-value]
    return {"plan_id": plan.plan_id, "step_count": plan.step_count}


@mcp.tool()
async def start_step(plan_id: str, step_index: int, session_id: str | None = None) -> dict[str, Any]:
    """Mark step ``step_index`` of ``plan_id`` as RUNNING. Idempotent on RUNNING."""
    with tracker_call() as r:
        step = _get_tracker().start_step(plan_id, step_index, session_id=session_id)
    return r.error if r.failed else step_dict(plan_id, step)  # type: ignore[return-value]


@mcp.tool()
async def complete_step(
    plan_id: str,
    step_index: int,
    summary: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Mark step ``step_index`` DONE. ``summary`` is optional (one-line result)."""
    with tracker_call() as r:
        step = _get_tracker().complete_step(plan_id, step_index, summary, session_id=session_id)
    return r.error if r.failed else step_dict(plan_id, step)  # type: ignore[return-value]


@mcp.tool()
async def fail_step(
    plan_id: str,
    step_index: int,
    error: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Mark step ``step_index`` FAILED. The plan goes to FAILED overall."""
    with tracker_call() as r:
        step = _get_tracker().fail_step(plan_id, step_index, error, session_id=session_id)
    return r.error if r.failed else step_dict(plan_id, step)  # type: ignore[return-value]


@mcp.tool()
async def cancel_step(
    plan_id: str,
    step_index: int,
    reason: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Mark step ``step_index`` CANCELLED — client/agent aborted it mid-run."""
    with tracker_call() as r:
        step = _get_tracker().cancel_step(plan_id, step_index, reason, session_id=session_id)
    return r.error if r.failed else step_dict(plan_id, step)  # type: ignore[return-value]


@mcp.tool()
async def note_step(
    plan_id: str,
    step_index: int,
    note: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Append a progress note to a RUNNING step — never overwrites."""
    with tracker_call() as r:
        step = _get_tracker().note_step(plan_id, step_index, note, session_id=session_id)
    return r.error if r.failed else step_dict(plan_id, step)  # type: ignore[return-value]


# --- replanning tools -------------------------------------------------------


@mcp.tool()
async def insert_step(
    plan_id: str,
    after_index: int,
    spec: Any,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Insert a new step right after ``after_index`` (use ``-1`` to prepend)."""
    with tracker_call(value_error_code="invalid_step_spec") as r:
        plan = _get_tracker().insert_step(plan_id, after_index, spec, session_id=session_id)
    return r.error if r.failed else plan_summary_dict(plan)  # type: ignore[return-value]


@mcp.tool()
async def replan(
    plan_id: str,
    from_index: int,
    new_steps: list[Any],
    session_id: str | None = None,
) -> dict[str, Any]:
    """Replace every step from ``from_index`` onwards with ``new_steps``."""
    with tracker_call(value_error_code="invalid_new_steps") as r:
        plan = _get_tracker().replan(plan_id, from_index, new_steps, session_id=session_id)
    return r.error if r.failed else plan_summary_dict(plan)  # type: ignore[return-value]


# --- closure tools ----------------------------------------------------------


@mcp.tool()
async def cancel_plan(
    plan_id: str,
    reason: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Cancel the entire plan — every non-terminal step → CANCELLED."""
    with tracker_call() as r:
        plan = _get_tracker().cancel_plan(plan_id, reason, session_id=session_id)
    return r.error if r.failed else plan_summary_dict(plan)  # type: ignore[return-value]


@mcp.tool()
async def finalize_plan(
    plan_id: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Settle the plan — every still-PENDING-or-RUNNING step → SKIPPED."""
    with tracker_call() as r:
        plan = _get_tracker().finalize_plan(plan_id, session_id=session_id)
    return r.error if r.failed else plan_summary_dict(plan)  # type: ignore[return-value]


# --- introspection ----------------------------------------------------------


@mcp.tool()
async def list_plans(session_id: str) -> dict[str, Any]:
    """List every plan for ``session_id`` — useful to recover context."""
    plans = _get_tracker().list_for_session(session_id)
    return {"plans": [plan_summary_dict(p) for p in plans]}


if __name__ == "__main__":
    # stdio transport — what fi-runner's MCPServerSpec(command=python, args=[-m, ...]) spawns.
    mcp.run()
