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
from pathlib import Path

from fi_runner import (
    ClaudeCodeBackend,
    PermissionMode,
    Runner,
    ToolPolicy,
    active_corpus_binding,
    load_prompt,
)

PERSONA_PATH = Path(__file__).parent / "prompts" / "persona.md"


def build_runner(persona_path: Path = PERSONA_PATH) -> Runner:
    """Compose the og118 Runner — AGENTIC (step 4): the task_tracker MCP lets the
    agent declare a plan + walk steps, so fi-runner emits plan/step_*/tool_call
    events (the glass-box stream og118's AgentHook maps onto core's
    AgentStreamEvent). Auth is ambient (`CLAUDE_CODE_OAUTH_TOKEN`).

    `persona_path` selects the system prompt: the default is the base og118
    companion; an "elemento" (OG118-ELEMENTS-ADR-1) passes its own persona `.md`
    (e.g. `008-o-oxigeno.md` = Vultur). Everything else — capabilities, the
    corpus binding, the COMPANION tool policy — is identical across elements, so a
    persona swap never widens the filesystem guarantee."""
    return Runner(
        backend=ClaudeCodeBackend(
            default_model=os.getenv("OG118_MODEL", "claude-sonnet-4-5"),
        ),
        persona=load_prompt(persona_path),
        # task_tracker → plan/step glass-box events. rag_store → the agent can
        # ingest/search a project corpus (the Projects-for-the-papelería canary);
        # backend + path resolve from FI_RAG_BACKEND / FI_RAG_STORE_PATH, hdf5 +
        # hashing zero-model embedder by default (no LLM, no network for retrieval).
        capabilities=["task_tracker", "rag_store"],
        # proj-corpusbind consumer wiring: when /chat/stream carries a corpus_id
        # (the user's active project), this binding folds "search ONLY corpus X"
        # into the turn's system prompt so the agent's rag_store tools retrieve
        # from the active project's corpus. No active project → no addendum, the
        # persona is byte-identical to before. The framework primitive is agnostic
        # to WHAT the id is; og118's local-first project id is the corpus_id.
        context_prompt=active_corpus_binding(),
        # DD-002C → og118-continuity canary: conversation continuity by CLIENT-SENT
        # history replay. og118 is local-first — the transcript lives in the
        # browser's IndexedDB and the client replays it on each /chat/stream turn
        # (ChatRequest.history). The Runner folds + re-sanitizes it (untrusted
        # context, never authorization) via sanitize_history. So there is NO
        # server-side store and the backend is STATELESS: continuity survives an ACA
        # replica recycle/redeploy/scale automatically (the prior InMemory store was
        # wiped on restart → the model lost the thread mid-conversation). The
        # client_history_max_messages / _chars caps bound per-turn token cost.
        tool_policy=ToolPolicy(
            # og118 is a thinking companion, not a coding agent. BYPASS mode grants
            # every built-in EXCEPT these, so the repo/filesystem tools must be
            # named explicitly — otherwise the model reaches the host container's
            # source (a user asking "show me your code" made it Glob+Read app.py /
            # runner.py on the shared papelería host: a real exposure). Blocking the
            # read/navigation builtins too makes the persona's "you have no
            # filesystem" TRUE, not merely asserted. rag_store (project corpus) is an
            # MCP tool, not a builtin, so document search is unaffected.
            builtin_disallowed=[
                "Bash", "Write", "Edit", "NotebookEdit",  # no shell / file mutation
                "Read", "Grep", "Glob", "LS", "Task",     # no host filesystem / repo
            ],
            # Headless: auto-approve the (safe, in-process) task_tracker MCP tools
            # so no interactive permission prompt blocks the turn.
            permission_mode=PermissionMode.BYPASS,
        ),
    )
