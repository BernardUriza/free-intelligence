"""og118 Runner — fi-runner built inline, Claude Code backend via OAuth.

Same proven pattern as insult_ai (production): a `Runner` composed inline with
`ClaudeCodeBackend` authed by the ambient `CLAUDE_CODE_OAUTH_TOKEN` (Max
subscription OAuth). v0 is a plain conversational turn — no fi-core capabilities
wired, built-in mutating tools disallowed for safety. The agentic stream
(turn_flow / ToolCall) is emitted natively by `run_stream`; the frontend hook
maps it onto core's contracts.
"""

from __future__ import annotations

import os

from fi_runner import ClaudeCodeBackend, PermissionMode, Runner, ToolPolicy

PERSONA = (
    "You are og118 — element 118, Oganesson: synthetic, the heaviest known, "
    "the end of the periodic table. A personal thinking companion on the Free "
    "Intelligence substrate. Glass-box by design: you plan in the open before "
    "you answer.\n\n"
    "WORKFLOW (always): first call the task tracker's declare_plan with 2-4 "
    "concrete steps for how you'll tackle the question. Then for EACH step call "
    "start_step and, when finished, complete_step (with a one-line summary). "
    "Only after the steps are complete, write the final answer. Be precise, "
    "candid, concise; no filler."
)


def build_runner() -> Runner:
    """Compose the og118 Runner — AGENTIC (step 4): the task_tracker MCP lets the
    agent declare a plan + walk steps, so fi-runner emits plan/step_*/tool_call
    events (the glass-box stream og118's AgentHook maps onto core's
    AgentStreamEvent). Auth is ambient (`CLAUDE_CODE_OAUTH_TOKEN`)."""
    return Runner(
        backend=ClaudeCodeBackend(
            default_model=os.getenv("OG118_MODEL", "claude-sonnet-4-5"),
        ),
        persona=PERSONA,
        capabilities=["task_tracker"],  # plan/step events come from this MCP
        tool_policy=ToolPolicy(
            builtin_disallowed=["Bash", "Write", "Edit"],  # no shell/file writes
            # Headless: auto-approve the (safe, in-process) task_tracker MCP tools
            # so no interactive permission prompt blocks the turn.
            permission_mode=PermissionMode.BYPASS,
        ),
    )
