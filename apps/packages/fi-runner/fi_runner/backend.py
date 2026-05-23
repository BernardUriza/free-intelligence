"""The ``AgentBackend`` port — a backend-agnostic interface over agent harnesses.

A backend wraps ONE agent runtime (Claude Code, Codex, or a raw-API runner)
and runs a single turn given a system prompt, a user message, the MCP servers
to register, and a :class:`ToolPolicy` (the 3 knobs: which built-in tools are
auto-approved, which are blocked, and the permission mode). Runners depend on
this port — swap the backend, keep the runner.

Zero-dep: this module imports no harness SDK; the backends import theirs lazily.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class PermissionMode(str, Enum):
    """Permission behavior for a turn (maps to each harness's own modes)."""

    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    PLAN = "plan"
    DONT_ASK = "dontAsk"
    BYPASS = "bypassPermissions"


@dataclass(frozen=True)
class MCPServerSpec:
    """An MCP server: either a stdio subprocess (command+args) or an in-process
    server object (``server``), plus the tools it exposes."""

    name: str
    # stdio transport: the executable + args. Left empty when ``server`` is set.
    command: str = ""
    args: list[str] = field(default_factory=list)
    # Explicit tool names, used to build the allowlist. Empty = allow the whole
    # server (``mcp__<name>``).
    tools: tuple[str, ...] = ()
    # Inherit the parent process env into the subprocess (needed so the server
    # can import its package + read credentials).
    env_passthrough: bool = True
    # A pre-built IN-PROCESS MCP server object (e.g. an SDK SdkMcpServer like
    # insult's insult_db). When set, it is passed straight to the harness and
    # ``command``/``args`` are ignored.
    server: Any = None

    @property
    def is_in_process(self) -> bool:
        return self.server is not None


@dataclass
class ToolPolicy:
    """The 3 knobs every backend honors — the per-runner security config."""

    # Built-in harness tools to auto-approve (e.g. ["Read"]). Empty = none.
    builtin_allowed: list[str] = field(default_factory=list)
    # Built-in tools to BLOCK outright (e.g. ["Bash", "Write"] for a PHI runner).
    builtin_disallowed: list[str] = field(default_factory=list)
    permission_mode: PermissionMode = PermissionMode.DEFAULT


@dataclass(frozen=True)
class TurnResult:
    """The result of one turn."""

    text: str
    raw: Any = None
    # Token usage when the backend reports it (e.g. Codex turn.completed.usage).
    usage: dict[str, Any] | None = None
    # Backend session/thread id for continuity (e.g. Codex thread_id).
    session_id: str | None = None


@runtime_checkable
class AgentBackend(Protocol):
    """A swappable agent runtime (Claude Code, Codex, raw API, ...)."""

    async def run_turn(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
        session_id: str | None = None,
    ) -> TurnResult:
        """Run one turn. If ``session_id`` is given, a backend that supports it
        keeps a stateful session (conversation continuity) keyed by that id."""
        ...
