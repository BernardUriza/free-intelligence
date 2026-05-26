"""MCP tool contract for the task_tracker server — zero-dep metadata.

Separate from :mod:`fi_core.task_tracker.mcp_server` (which imports the MCP
SDK) so the contract is importable WITHOUT that dep. fi-runner's
``task_tracker`` capability reads this to build the ``mcp__<server>__<tool>``
allowlist, then spawns the server with
``python -m fi_core.task_tracker.mcp_server``.

The :data:`MCP_EVENTS` list is the WIRE counterpart — it documents the
stream events fi-runner emits when it observes these tool calls, so a
frontend (insult_ai's chat hook, etc.) has a single source of truth for the
event names it should switch on."""

from __future__ import annotations

MCP_SERVER_NAME = "fi_core_task_tracker"

MCP_TOOLS: list[dict[str, str]] = [
    {
        "name": "declare_plan",
        "description": (
            "Declare the ordered plan you're about to execute. Call this FIRST every turn, "
            "BEFORE any other tool. `steps` is a list of short imperative labels "
            "(e.g. 'Search SERP for acme.com'). Returns {plan_id, step_count}. "
            "The plan is visible to the UI as a checklist while you work through it."
        ),
    },
    {
        "name": "start_step",
        "description": (
            "Mark a declared step as RUNNING just before executing it. "
            "`plan_id` is from declare_plan; `step_index` is 0-based. "
            "Returns the updated step. UI flips its row to in-progress."
        ),
    },
    {
        "name": "complete_step",
        "description": (
            "Mark a step as DONE. `summary` is an optional one-line result "
            "(e.g. 'Found 3 candidates including acme.com/about'); it surfaces "
            "in the UI checklist and feeds the next step's context."
        ),
    },
    {
        "name": "fail_step",
        "description": (
            "Mark a step as FAILED. `error` is a short reason. The plan's overall "
            "status flips to FAILED — a plan with one failed step is failed overall."
        ),
    },
]


# Events emitted by fi-runner when it observes the matching tool calls. These
# are NOT MCP tools — they are stream events on Runner.run_stream(), but the
# names live here so frontends and the runner agree without round-trip search.
MCP_EVENTS: list[dict[str, str]] = [
    {
        "name": "plan",
        "description": "{plan_id, session_id, steps:[label,...]} — emitted right after declare_plan succeeds.",
    },
    {
        "name": "step_started",
        "description": "{plan_id, step_index, label} — emitted right after start_step.",
    },
    {
        "name": "step_done",
        "description": "{plan_id, step_index, status:'done'|'failed', duration_ms, summary?, error?}.",
    },
]
