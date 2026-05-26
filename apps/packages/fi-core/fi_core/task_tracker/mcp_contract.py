"""MCP tool contract for the task_tracker server — zero-dep metadata.

Separate from :mod:`fi_core.task_tracker.mcp_server` (which imports the MCP
SDK) so the contract is importable WITHOUT that dep. fi-runner's
``task_tracker`` capability reads this to build the ``mcp__<server>__<tool>``
allowlist, then spawns the server with
``python -m fi_core.task_tracker.mcp_server``.

The :data:`MCP_EVENTS` list is the WIRE counterpart — it documents the
stream events fi-runner emits when it observes these tool calls, so a
frontend (insult_ai's chat hook, etc.) has a single source of truth for the
event names it should switch on.

The toolset covers four lifecycles:
  - **Declaration** (``declare_plan``) — agent commits to a scope.
  - **Step progression** (``start_step``, ``complete_step``, ``fail_step``,
    ``cancel_step``, ``note_step``) — agent reports progress.
  - **Replanning** (``insert_step``, ``replan``) — agent amends an open plan
    when the world looks different than expected (plan-and-execute rigidity
    fix, per the LangChain plan-and-execute critique).
  - **Closure** (``finalize_plan``, ``cancel_plan``) — agent or harness
    settles the plan so the UI checklist can collapse.
  - **Introspection** (``list_plans``) — agent reads back its open plans
    when a turn resumes context."""

from __future__ import annotations

MCP_SERVER_NAME = "fi_core_task_tracker"

MCP_TOOLS: list[dict[str, str]] = [
    {
        "name": "declare_plan",
        "description": (
            "Declare the ordered plan you're about to execute. Call this FIRST every turn, "
            "BEFORE any other tool. `steps` is a list of either short imperative labels "
            "(e.g. 'Search SERP for acme.com') or objects with `label`, optional `active_form` "
            "(present-continuous verb shown while the step is running, e.g. 'Searching SERP'), "
            "optional `depends_on` (list of earlier step indexes that must complete first), "
            "and optional `metadata` (opaque dict for consumer-specific data). "
            "Returns {plan_id, step_count}. The plan is visible to the UI as a checklist."
        ),
    },
    {
        "name": "start_step",
        "description": (
            "Mark a declared step as RUNNING just before executing it. "
            "`plan_id` is from declare_plan; `step_index` is 0-based. "
            "Idempotent: calling twice on a RUNNING step is a no-op. "
            "Rejected if the step is already terminal or if any dependency hasn't completed."
        ),
    },
    {
        "name": "complete_step",
        "description": (
            "Mark a step as DONE. `summary` is an optional one-line result "
            "(e.g. 'Found 3 candidates including acme.com/about'); it surfaces "
            "in the UI checklist and feeds the next step's context. "
            "Rejected if the step is already terminal — late retries don't overwrite."
        ),
    },
    {
        "name": "fail_step",
        "description": (
            "Mark a step as FAILED. `error` is a short reason. The plan's overall "
            "status flips to FAILED once all steps settle — a plan with one failed "
            "step is failed overall. Rejected if the step is already terminal."
        ),
    },
    {
        "name": "cancel_step",
        "description": (
            "Mark a step as CANCELLED — for use when the client (or the agent itself) "
            "aborts a RUNNING step. `reason` is an optional short message. Distinct "
            "from fail_step: cancellation is not an error, just an interruption."
        ),
    },
    {
        "name": "note_step",
        "description": (
            "Append a progress note to a RUNNING step without ending it. Useful for "
            "long steps ('scraped page 2 of 4...'). Notes are append-only — never "
            "overwrite prior text. Rejected if the step is already terminal."
        ),
    },
    {
        "name": "insert_step",
        "description": (
            "Insert a new step right after `after_index` (use -1 to prepend at the head). "
            "Later steps' indexes are bumped automatically, including any `depends_on` "
            "references. `spec` is a string label or the same dict shape as declare_plan's "
            "steps. Use when the plan needs an extra step you didn't anticipate."
        ),
    },
    {
        "name": "replan",
        "description": (
            "Replace every step from `from_index` onwards with `new_steps`. Steps before "
            "`from_index` are kept (they must all be terminal — DONE/FAILED/SKIPPED/CANCELLED; "
            "you can't replan around a RUNNING step without cancelling it first). Use when "
            "the world looks different than the original plan assumed."
        ),
    },
    {
        "name": "cancel_plan",
        "description": (
            "Cancel the entire plan: every non-terminal step is marked CANCELLED, the "
            "plan flips to CANCELLED. `reason` is an optional short message. Use when "
            "the user interrupts or the agent decides the plan is no longer viable."
        ),
    },
    {
        "name": "finalize_plan",
        "description": (
            "Settle the plan: every still-PENDING-or-RUNNING step is marked SKIPPED, "
            "the plan flips to COMPLETED (or FAILED if any step failed). Call this at "
            "the end of a turn so the UI checklist closes cleanly."
        ),
    },
    {
        "name": "list_plans",
        "description": (
            "List every plan recorded for `session_id`, in declaration order. Returns "
            "[{plan_id, status, step_count, completed_count, failed_count}]. Useful at "
            "the start of a turn to recover context if the agent forgot its plan_ids."
        ),
    },
]


# Events emitted by fi-runner when it observes the matching tool calls. These
# are NOT MCP tools — they are stream events on Runner.run_stream(), but the
# names live here so frontends and the runner agree without round-trip search.
MCP_EVENTS: list[dict[str, str]] = [
    {
        "name": "plan",
        "description": "{plan_id?, session_id, steps:[{label, active_form?, depends_on?, metadata?},...]} — emitted right after declare_plan succeeds.",
    },
    {
        "name": "step_started",
        "description": "{plan_id, step_index, label?} — emitted right after start_step.",
    },
    {
        "name": "step_done",
        "description": "{plan_id, step_index, status:'done'|'failed'|'cancelled', duration_ms?, summary?, error?}.",
    },
    {
        "name": "step_noted",
        "description": "{plan_id, step_index, note} — emitted when note_step appends a progress note to a RUNNING step.",
    },
    {
        "name": "plan_amended",
        "description": "{plan_id, action:'insert'|'replan', step_count} — emitted after insert_step or replan reshapes the plan.",
    },
    {
        "name": "plan_completed",
        "description": "{plan_id, step_count, completed_count, failed_count, cancelled_count} — emitted when the plan reaches a successful terminal state (COMPLETED).",
    },
    {
        "name": "plan_failed",
        "description": "{plan_id, step_count, completed_count, failed_count, cancelled_count} — emitted when the plan reaches FAILED (any step failed).",
    },
    {
        "name": "plan_cancelled",
        "description": "{plan_id, reason?} — emitted when the plan is cancelled via cancel_plan or settles to CANCELLED without any DONE step.",
    },
]
