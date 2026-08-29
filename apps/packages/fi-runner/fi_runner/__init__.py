"""fi-runner — the agent runner framework over fi-core, on AIRE's door.

``Runner`` composes a backend + a persona + guards + per-turn context bindings,
and owns the turn pipeline: one attempt loop shared by :meth:`Runner.run` and
:meth:`Runner.run_stream`, so retry, the guard verdict and the plan veto apply
whether or not the caller streams.

**One backend.** :class:`AIREBackend` talks HTTP to AIRE — Bernard's
always-up server that wraps the Agent SDK, owns the transcript in its Postgres
and mounts a vetted tool registry server-side. The local SDK/CLI hosts
(``ClaudeCodeBackend``, ``CodexBackend``, ``SubprocessCLIBackend``) were deleted
on 2026-08-29: aire-server had already forked the SDK host on purpose, so
keeping them here maintained a second, unexercised way to run a turn. See
:mod:`fi_runner.backends` for what went with them.

:class:`~fi_runner.backend.AgentBackend` is still a Protocol, so a second door
is a file away — what is gone is pretending three were maintained.

Importing this package is dep-free; the backend pulls its HTTP client only when
you actually run a turn (extra: ``fi-runner[aire]``).

    import asyncio
    from fi_runner import Runner, AIREBackend

    # A locked-down medical runner: the door's `complete` mode grants no
    # builtins at all, and the turn asks for one vetted registry tool.
    medic = Runner(
        backend=AIREBackend(
            project="cardio",
            default_model="claude-sonnet-4-5",
            default_mode="complete",
            registry_tools=("task_tracker",),
        ),
        persona="You are a cardiology decision-support assistant. ...",
    )
    print(asyncio.run(medic.run("70yo male, chest pain + dyspnea, HTN/DM")).text)
"""

from typing import Any

from . import capabilities, conversation, flow, guards, narrate, pipeline, router
from .backend import (
    COMPANION_BLOCKED_BUILTINS,
    AgentBackend,
    BackendError,
    MCPServerSpec,
    PermissionMode,
    ToolCall,
    ToolPolicy,
    TurnImage,
    TurnResult,
    mcp_server_of,
    pinned_arg_violation,
    mcp_server_token,
    mcp_tool_id,
)
from .backends import AIREBackend, AIREDoorError
from .conversation import (
    ConversationStore,
    InMemoryConversationStore,
    Message,
    RedisConversationStore,
    render_transcript,
    sanitize_history,
)
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
from .plan_guard import PlanGuard, PlanGuardOutcome, plan_guard
from .preflight import PreflightResult, probe_all, probe_mcp
from .router import ModelRouter
from .context_binding import (
    MAX_OWNER_INSTRUCTIONS_CHARS,
    ContextPrompt,
    active_corpus_binding,
    pinned_corpus_args,
    compose_bindings,
    owner_instructions_binding,
)
from .prompts import load_prompt
from .runner import FlowNarrator, RetryPolicy, Runner

__version__ = "0.21.1"

__all__ = [
    "AgentBackend",
    "BackendError",
    "COMPANION_BLOCKED_BUILTINS",
    "MCPServerSpec",
    "PermissionMode",
    "ToolCall",
    "ToolPolicy",
    "TurnImage",
    "TurnResult",
    "mcp_tool_id",
    "mcp_server_token",
    "mcp_server_of",
    "pinned_arg_violation",
    "AIREBackend",
    "AIREDoorError",
    "Runner",
    "RetryPolicy",
    "FlowNarrator",
    "ContextPrompt",
    "MAX_OWNER_INSTRUCTIONS_CHARS",
    "active_corpus_binding",
    "pinned_corpus_args",
    "compose_bindings",
    "owner_instructions_binding",
    "load_prompt",
    "ModelRouter",
    "capabilities",
    "conversation",
    "ConversationStore",
    "InMemoryConversationStore",
    "RedisConversationStore",
    "Message",
    "render_transcript",
    "sanitize_history",
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
    "PreflightResult",
    "probe_mcp",
    "probe_all",
    "PlanGuard",
    "PlanGuardOutcome",
    "plan_guard",
    "packs",
    "GravityScore",
]


# Re-export the fi-core surface a runner needs to USE guards without importing
# fi-core itself (fi_runner is the single boundary): the persona pattern `packs`
# (compose anti-drift patterns, via the fi_runner.packs submodule) and
# `GravityScore` (the triage_guard's result type). Lazy via PEP 562 so plain
# `import fi_runner` stays free of fi-core.
def __getattr__(name: str) -> Any:
    if name == "packs":
        # import_module (not `from . import packs`) — the latter re-enters this
        # __getattr__ via _handle_fromlist and recurses infinitely.
        import importlib

        return importlib.import_module(f"{__name__}.packs")
    if name == "GravityScore":
        from fi_core.cognitive import GravityScore

        return GravityScore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
