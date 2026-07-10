"""The ``AgentBackend`` port — a backend-agnostic interface over agent harnesses.

A backend wraps ONE agent runtime (Claude Code, Codex, or a raw-API runner)
and runs a single turn given a system prompt, a user message, the MCP servers
to register, and a :class:`ToolPolicy` (the 3 knobs: which built-in tools are
auto-approved, which are blocked, and the permission mode). Runners depend on
this port — swap the backend, keep the runner.

Zero-dep: this module imports no harness SDK; the backends import theirs lazily.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

_logger = logging.getLogger(__name__)

# Shell wrappers that hide the real MCP server PID from the harness's child
# tracker — if ``command`` is one of these, the wrapper exits and the actual
# python child becomes invisible (orphan/zombie risk on harness shutdown).
_SHELL_WRAPPERS: frozenset[str] = frozenset({
    "sh", "bash", "zsh", "/bin/sh", "/bin/bash", "/bin/zsh",
    "/usr/bin/sh", "/usr/bin/bash", "/usr/bin/zsh",
})


#: Env vars that are safe to forward from the runner's environment to an MCP
#: subprocess by default. PATH (find executables), HOME (config files), USER
#: (logging), LANG/LC_* (locale), PYTHONPATH+VIRTUAL_ENV (find the installed
#: fi_core package), TERM (TTY apps), TZ (timezone-aware logs). Everything
#: else — AWS_*, AZURE_*, OPENAI_API_KEY, ANTHROPIC_API_KEY, GITHUB_TOKEN,
#: etc. — is BLOCKED unless the consumer opts in via ``env_passthrough=True``
#: or a custom whitelist. This matches the industry convention (Docker MCP
#: gateway, Hermes, Claude Code) for stopping accidental secret leakage to
#: third-party MCP servers spawned as subprocesses.
DEFAULT_SAFE_ENV_VARS: frozenset[str] = frozenset({
    "PATH", "HOME", "USER", "LOGNAME",
    "LANG", "LC_ALL", "LC_CTYPE", "LC_COLLATE", "LC_MESSAGES",
    "PYTHONPATH", "PYTHONHOME", "PYTHONUNBUFFERED", "VIRTUAL_ENV",
    "TERM", "TZ", "SHELL",
})


def safe_subprocess_env(
    *,
    extra: dict[str, str] | None = None,
    whitelist: frozenset[str] | None = None,
) -> dict[str, str]:
    """Build a subprocess env dict that includes ONLY safe vars from os.environ.

    ``whitelist`` overrides the default safe set; ``extra`` is merged on top
    (use for vars an MCP server legitimately needs that aren't safe by
    default — pass them EXPLICITLY rather than blanket-leak everything)."""
    safe = whitelist if whitelist is not None else DEFAULT_SAFE_ENV_VARS
    # Also honor LC_* prefix wildcards beyond the explicit names above.
    env = {k: v for k, v in os.environ.items() if k in safe or k.startswith("LC_")}
    if extra:
        env.update(extra)
    return env


class BackendError(RuntimeError):
    """Raised when a backend's ``run_turn`` fails (SDK error, CLI non-zero exit,
    missing dependency, timeout). The Runner wraps any backend exception in this
    type with the original chained as ``__cause__`` — a consumer catches one
    error class and still has the root cause. A crash becomes a legible,
    typed failure instead of a backend-specific traceback leaking out."""


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
    # SECURITY: when ``True`` the FULL parent ``os.environ`` is forwarded to
    # the MCP subprocess — including AWS_*, OPENAI_API_KEY, GITHUB_TOKEN, and
    # any other secret the runner can see. The default remains ``True`` only
    # for backward compatibility with consumers that already construct
    # :class:`MCPServerSpec` directly. **fi-runner's own capability factories
    # default to ``False``** (see :mod:`fi_runner.capabilities`), which uses
    # :func:`safe_subprocess_env` to forward ONLY a whitelisted safe set
    # (PATH, HOME, USER, LANG, PYTHONPATH, etc.). Set this to ``True`` only
    # when the MCP server legitimately needs more — and prefer adding the
    # specific vars to an ``extra`` dict via a custom spawn site over
    # blanket-leaking everything.
    env_passthrough: bool = True
    # A pre-built IN-PROCESS MCP server object (e.g. an SDK SdkMcpServer like
    # insult's insult_db). When set, it is passed straight to the harness and
    # ``command``/``args`` are ignored.
    server: Any = None

    @property
    def is_in_process(self) -> bool:
        return self.server is not None

    def __post_init__(self) -> None:
        # Lint: wrapping the MCP server in a shell ("/bin/bash -c python ...")
        # makes the real PID invisible to the harness's child tracker — when
        # the wrapper exits, the python child becomes a zombie/orphan instead
        # of being reaped. Prefer ``command=sys.executable, args=["-m", ...]``
        # so the harness owns the actual server process. Warning, not error,
        # because legitimate shim use-cases exist (env munging, conditional
        # execs); the consumer can suppress it via a custom logger filter.
        if self.is_in_process or not self.command:
            return
        cmd_basename = self.command.rsplit("/", 1)[-1]
        if self.command in _SHELL_WRAPPERS or cmd_basename in {"sh", "bash", "zsh"}:
            _logger.warning(
                "MCPServerSpec(name=%r, command=%r): shell-wrapped commands "
                "hide the child PID from the harness's process tracker and risk "
                "zombie accumulation on shutdown. Prefer `command=sys.executable, "
                "args=['-m', '<module>']` so the harness owns the real PID. "
                "See fi-runner robustness roadmap R7.",
                self.name,
                self.command,
            )


# The built-ins a non-coding COMPANION must never reach: shell, file mutation,
# and host-filesystem / repo navigation. Under BYPASS (which grants every builtin
# EXCEPT the disallowed list) these MUST be named explicitly, or a chat persona on
# ClaudeCodeBackend can Glob+Read its own deployment source when asked to "show
# your code" — a real exposure seen on og118. Naming them makes the persona's "you
# have no filesystem" TRUE, not merely asserted. MCP tools (a project's rag_store,
# task_tracker) are NOT builtins and stay available.
# The harness's OWN task builtins are blocked for a different reason than the rest:
# they COMPETE with the task_tracker MCP and win. Told to "declare a plan", the
# agent reaches for the always-present TaskCreate instead of
# mcp__fi_core_task_tracker__declare_plan. Those calls arrive with `server: None`,
# so `_plan_events.derive` drops them and the glass-box plan/step stream is never
# emitted — the agent plans, and the UI shows nothing. Blocking them leaves the
# MCP as the only way to declare a plan, which is exactly what the trace needs.
COMPANION_BLOCKED_BUILTINS: tuple[str, ...] = (
    "Bash", "Write", "Edit", "NotebookEdit",  # no shell / file mutation
    "Read", "Grep", "Glob", "LS", "Task",     # no host filesystem / repo
    "TaskCreate", "TaskUpdate", "TaskGet",    # no harness task tools: they shadow
    "TaskList", "TaskOutput", "TaskStop",     # the task_tracker MCP (glass-box)
)


@dataclass
class ToolPolicy:
    """The 3 knobs every backend honors — the per-runner security config."""

    # Built-in harness tools to auto-approve (e.g. ["Read"]). Empty = none.
    builtin_allowed: list[str] = field(default_factory=list)
    # Built-in tools to BLOCK outright (e.g. ["Bash", "Write"] for a PHI runner).
    builtin_disallowed: list[str] = field(default_factory=list)
    permission_mode: PermissionMode = PermissionMode.DEFAULT

    @classmethod
    def companion(
        cls,
        *,
        builtin_allowed: list[str] | None = None,
        permission_mode: PermissionMode = PermissionMode.BYPASS,
    ) -> "ToolPolicy":
        """The non-coding COMPANION profile: every shell / file-mutation /
        host-filesystem builtin (:data:`COMPANION_BLOCKED_BUILTINS`) is blocked, so
        a chat persona can never read the host's source or mutate files. This is the
        framework home of the og118 #277 fix — every companion (alice, ferboli,
        activist-os, future wrappers) inherits the same guarantee instead of
        re-listing the blocked builtins per consumer. Opt extra builtins in via
        ``builtin_allowed``; a consumer that genuinely needs filesystem access uses a
        plain :class:`ToolPolicy` instead of this profile."""
        return cls(
            builtin_allowed=list(builtin_allowed or []),
            builtin_disallowed=list(COMPANION_BLOCKED_BUILTINS),
            permission_mode=permission_mode,
        )


# --- MCP tool-id convention (single source of truth) -------------------------
#
# Every backend AND the tool-trace identify MCP tools the same way:
# ``mcp__<server>__<tool>`` for one tool, ``mcp__<server>`` to allow a whole
# server. Build and parse it ONLY through these helpers — never hand-roll the
# ``mcp__`` / ``__`` strings in a backend, so the convention lives in one place.

_MCP_PREFIX = "mcp__"
_MCP_SEP = "__"


def mcp_tool_id(server: str, tool: str) -> str:
    """The allowlist id for one MCP tool: ``mcp__<server>__<tool>``."""
    return f"{_MCP_PREFIX}{server}{_MCP_SEP}{tool}"


def mcp_server_token(server: str) -> str:
    """The token that allows a WHOLE MCP server: ``mcp__<server>``."""
    return f"{_MCP_PREFIX}{server}"


def mcp_server_of(tool_name: str) -> str | None:
    """The MCP server a tool name belongs to, or ``None`` for a built-in tool
    (e.g. ``Bash``). Recovers the server from :func:`mcp_tool_id` /
    :func:`mcp_server_token` output — round-trips exactly as long as the server
    name has no ``__`` (true for MCP server names; the separator is reserved)."""
    if not tool_name.startswith(_MCP_PREFIX):
        return None
    return tool_name[len(_MCP_PREFIX) :].split(_MCP_SEP, 1)[0] or None


@dataclass(frozen=True)
class ToolCall:
    """One tool invocation the agent made during a turn (the tool-trace).

    Backend-agnostic: ClaudeCodeBackend builds these from the SDK's
    ``ToolUseBlock`` / ``ToolResultBlock``, CodexBackend from ``item.completed``
    events. ``server`` is the MCP server parsed from an ``mcp__<server>__<tool>``
    name (``None`` for a built-in tool like ``Bash``). ``is_error`` is the result
    status when the backend reports it (``None`` = unknown). ``input`` is kept for
    the consumer but is NEVER put into telemetry/diagrams — it may carry PHI.

    ``duration_ms`` is wall-clock time between the tool USE and its matching
    RESULT, when the backend can pair them. Claude Code fills it in (paired by
    ``tool_use_id``); Codex leaves it ``None`` (the JSONL stream has no per-item
    timestamps). Use it to colour slow steps in the Mermaid turn-flow."""

    name: str
    server: str | None = None
    input: dict[str, Any] | None = None
    id: str | None = None
    is_error: bool | None = None
    duration_ms: int | None = None

    @classmethod
    def make(
        cls,
        name: str,
        *,
        input: dict[str, Any] | None = None,
        id: str | None = None,
        is_error: bool | None = None,
        duration_ms: int | None = None,
    ) -> ToolCall:
        """Build a ToolCall, parsing the MCP ``server`` out of an
        ``mcp__<server>__<tool>`` name (``None`` for built-in tools)."""
        return cls(
            name=name,
            server=mcp_server_of(name),
            input=input,
            id=id,
            is_error=is_error,
            duration_ms=duration_ms,
        )


@dataclass(frozen=True)
class TurnResult:
    """The result of one turn."""

    text: str
    raw: Any = None
    # Token usage when the backend reports it (e.g. Codex turn.completed.usage).
    usage: dict[str, Any] | None = None
    # Backend session/thread id for continuity (e.g. Codex thread_id).
    session_id: str | None = None
    # Outcome of each guard the Runner ran post-turn, keyed by guard name. Values
    # are fi_runner.guards.GuardOutcome (kept as Any to avoid coupling the port to
    # the guards module). Empty when the runner declared no guards.
    guard_outcomes: dict[str, Any] = field(default_factory=dict)
    # The tool-trace: every tool the agent called this turn, in order. Empty when
    # the agent used no tools (or a backend can't report them).
    tool_calls: list[ToolCall] = field(default_factory=list)


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
