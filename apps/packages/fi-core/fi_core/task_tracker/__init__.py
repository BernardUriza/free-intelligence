"""fi_core.task_tracker — plan-first chain-of-thought tracker.

The agent declares its plan BEFORE acting, then marks each step started/done.
The runner intercepts the resulting MCP tool calls and emits stream events
(``plan``, ``step_started``, ``step_done``) so the UI can paint a real
checklist with progress, not a sequence of disconnected tool steps.

Why plan-first? An agent that has to *write down* its plan before executing
commits to scope. A user watching a 4-step checklist with progress (2/4 ✓)
trusts the system far more than one watching 'thinking…'. And a plan-guard
can reject prohibited plans BEFORE any tool runs — anti-drift moves UP from
post-hoc text sanitization into pre-execution review.

The contract (server name + tool list) is in :mod:`mcp_contract` (zero-dep,
importable without the MCP SDK); the live FastMCP server is in
:mod:`mcp_server` (requires ``fi-core[mcp]``). fi-runner's ``task_tracker``
capability reads the contract to build the allowlist."""

from __future__ import annotations

from .mcp_contract import MCP_EVENTS, MCP_SERVER_NAME, MCP_TOOLS
from .models import Plan, PlanStatus, Step, StepStatus
from .tracker import PlanNotFound, StepIndexInvalid, TaskTracker

__all__ = [
    "MCP_SERVER_NAME",
    "MCP_TOOLS",
    "MCP_EVENTS",
    "Plan",
    "PlanStatus",
    "Step",
    "StepStatus",
    "TaskTracker",
    "PlanNotFound",
    "StepIndexInvalid",
]
