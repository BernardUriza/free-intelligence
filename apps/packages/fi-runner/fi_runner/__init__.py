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

from . import capabilities
from .backend import (
    AgentBackend,
    MCPServerSpec,
    PermissionMode,
    ToolPolicy,
    TurnResult,
)
from .backends import ClaudeCodeBackend, CodexBackend, ProviderConfig
from .runner import Runner

__version__ = "0.4.0"

__all__ = [
    "AgentBackend",
    "MCPServerSpec",
    "PermissionMode",
    "ToolPolicy",
    "TurnResult",
    "ClaudeCodeBackend",
    "CodexBackend",
    "ProviderConfig",
    "Runner",
    "capabilities",
]
