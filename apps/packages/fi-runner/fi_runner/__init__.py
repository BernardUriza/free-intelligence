"""fi-runner — a backend-agnostic agent runner framework over fi-core.

A thin layer over agent HARNESSES (Claude Code, Codex): the ``AgentBackend``
port abstracts the runtime, ``Runner`` composes a backend + persona + fi-core
capabilities (wired as MCP servers), and ``ToolPolicy`` is the per-runner
security config (which built-in tools, which permission mode). Swap the backend,
keep the runner — Claude Code (Max subscription) ↔ Codex (ChatGPT) ↔ raw API.

Importing this package is dep-free; a backend pulls its harness SDK only when
you actually run a turn (extras: ``fi-runner[claude]`` / ``[codex]`` / ``[api]``).

    import asyncio
    from fi_runner import Runner, ClaudeCodeBackend, ToolPolicy, PermissionMode

    # A locked-down medical runner: cognitive tools only, no shell/file writes.
    medic = Runner(
        backend=ClaudeCodeBackend(default_model="claude-sonnet-4-5"),
        persona="You are a cardiology decision-support assistant. ...",
        capabilities=["cognitive"],
        tool_policy=ToolPolicy(
            builtin_disallowed=["Bash", "Write", "Edit"],   # PHI safety
            permission_mode=PermissionMode.DEFAULT,
        ),
    )
    print(asyncio.run(medic.run("70yo male, chest pain + dyspnea, HTN/DM")).text)
"""

from typing import Any

from . import capabilities, flow, guards, narrate, pipeline, router
from .backend import (
    AgentBackend,
    BackendError,
    MCPServerSpec,
    PermissionMode,
    ToolCall,
    ToolPolicy,
    TurnResult,
    mcp_server_of,
    mcp_server_token,
    mcp_tool_id,
)
from .backends import ClaudeCodeBackend, CodexBackend, ProviderConfig, SubprocessCLIBackend
from .flow import Event, events_to_mermaid
from .narrate import FlowNarrationError, narrate_flow
from .guards import (
    AntiDriftGuard,
    Guard,
    GuardOutcome,
    TriageGuard,
    antidrift_guard,
    triage_guard,
)
from .pipeline import (
    EventSink,
    MutationStage,
    OnViolation,
    PipelineViolationError,
    preserve_min_length,
    preserve_question_marks,
    run_pipeline,
    run_pipeline_sync,
)
from .router import ModelRouter
from .runner import FlowNarrator, RetryPolicy, Runner

__version__ = "0.8.0"

__all__ = [
    "AgentBackend",
    "BackendError",
    "MCPServerSpec",
    "PermissionMode",
    "ToolCall",
    "ToolPolicy",
    "TurnResult",
    "mcp_tool_id",
    "mcp_server_token",
    "mcp_server_of",
    "ClaudeCodeBackend",
    "CodexBackend",
    "ProviderConfig",
    "SubprocessCLIBackend",
    "Runner",
    "RetryPolicy",
    "FlowNarrator",
    "ModelRouter",
    "capabilities",
    "flow",
    "Event",
    "events_to_mermaid",
    "narrate",
    "narrate_flow",
    "FlowNarrationError",
    "guards",
    "router",
    "Guard",
    "GuardOutcome",
    "TriageGuard",
    "AntiDriftGuard",
    "triage_guard",
    "antidrift_guard",
    "pipeline",
    "MutationStage",
    "OnViolation",
    "PipelineViolationError",
    "EventSink",
    "preserve_min_length",
    "preserve_question_marks",
    "run_pipeline",
    "run_pipeline_sync",
    "packs",
    "GravityScore",
]


# Re-export the fi-core surface a runner needs to USE guards without importing
# fi-core itself (fi_runner is the single boundary): the persona pattern `packs`
# (compose anti-drift patterns) and `GravityScore` (the triage_guard's result
# type). Lazy via PEP 562 so plain `import fi_runner` stays free of fi-core.
def __getattr__(name: str) -> Any:
    if name == "packs":
        from fi_core.persona import packs

        return packs
    if name == "GravityScore":
        from fi_core.cognitive import GravityScore

        return GravityScore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
