"""fi_core.task_tracker — plan-first chain-of-thought tracker.

The agent declares its plan BEFORE acting, then marks each step started/done.
The runner intercepts the resulting MCP tool calls and emits stream events
(``plan``, ``step_started``, ``step_done``, ``plan_completed``, ``plan_failed``,
``plan_cancelled``, ``plan_amended``, ``step_noted``) so the UI can paint a
real checklist with progress, not a sequence of disconnected tool steps.

Why plan-first? An agent that has to *write down* its plan before executing
commits to scope. A user watching a 4-step checklist with progress (2/4 ✓)
trusts the system far more than one watching 'thinking…'. And a plan-guard
can reject prohibited plans BEFORE any tool runs — anti-drift moves UP from
post-hoc text sanitization into pre-execution review.

State is in-memory with TTL eviction (1h default) and per-session scoping;
terminal states are append-only (DONE/FAILED/SKIPPED/CANCELLED for steps,
COMPLETED/FAILED/CANCELLED for plans), so late retries can never regress.
A small DAG is supported via ``Step.depends_on`` — start_step refuses to
start a step whose dependencies aren't DONE yet.

The contract (server name + tool list) is in :mod:`mcp_contract` (zero-dep,
importable without the MCP SDK); the live FastMCP server is in
:mod:`mcp_server` (requires ``fi-core[mcp]``). fi-runner's ``task_tracker``
capability reads the contract to build the allowlist; the optional
``fi_runner.guards.plan_guard.PlanGuard`` (in fi-runner, not here) inspects
declared plans against the runner's tool policy before any step starts."""

from __future__ import annotations

from .mcp_contract import MCP_EVENTS, MCP_SERVER_NAME, MCP_TOOLS
from .models import (
    Plan,
    PlanStatus,
    Step,
    StepStatus,
    TERMINAL_PLAN_STATES,
    TERMINAL_STEP_STATES,
)
from .tracker import (
    DependencyUnmet,
    PlanAlreadyTerminal,
    PlanNotFound,
    SessionMismatch,
    StepAlreadyTerminal,
    StepIndexInvalid,
    TaskTracker,
)

__all__ = [
    # contract
    "MCP_SERVER_NAME",
    "MCP_TOOLS",
    "MCP_EVENTS",
    # types
    "Plan",
    "PlanStatus",
    "Step",
    "StepStatus",
    "TERMINAL_PLAN_STATES",
    "TERMINAL_STEP_STATES",
    # tracker + errors
    "TaskTracker",
    "PlanNotFound",
    "StepIndexInvalid",
    "StepAlreadyTerminal",
    "PlanAlreadyTerminal",
    "DependencyUnmet",
    "SessionMismatch",
]
