"""AIRE owns the SDK.

This file is a COPY of the `ClaudeCodeBackend` engine from fi-runner —the one
that already owned the Claude Agent SDK: it boots the `ClaudeSDKClient`, runs
the turn loop, drains the typed events— stripped of every fi-runner dependency,
plus the two things that make AIRE what it is:

- **MODES.** `complete` (no tools — the SUBSTITUTE for the raw Messages API)
  and `agent` (with tools — the ENHANCER: a Claude Code session that executes
  tools). The SDK is the engine of ONE mode, not AIRE's identity.
- **Its own MEMORY.** The Postgres `session_store`, sole owner, injected. The
  Claude API is stateless; AIRE is "the Claude API, but it remembers".

What is NOT done: importing fi-runner. AIRE owns this code. That is the whole
difference from the version that went wrong — before, AIRE *imported* the engine
and depended on a repo another agent was editing; now it owns it.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeSDKClient, project_key_for_directory

from .keys import sdk_session_uuid

WORKSPACES = Path(__file__).resolve().parent.parent / "workspaces"

SYSTEM_PROMPT = (
    "You are an agent working inside AIRE. Your work appears, live, on an HTML "
    "page the server keeps writing as you think. Use your tools whenever they "
    "help: every call is painted onto the page."
)

# The modes: the dial that makes AIRE both substitute AND enhancer.
#   complete → no tools, no agentic loop → the substitute for the raw API.
#   agent    → tools + BYPASS → the enhancer that executes tools.
# CAREFUL with BYPASS: it grants ALL builtins EXCEPT those in `disallowed` — the
# allowlist is decorative under that mode; what actually contains is `disallowed`.
# `Bash` stays out; the real filesystem confinement is `SandboxSettings`, not yet
# in place — `cwd` is NOT a cage.
MODES: dict[str, dict[str, Any]] = {
    "complete": {
        "allowed_tools": [],
        "disallowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch"],
        "permission_mode": "default",
    },
    "agent": {
        "allowed_tools": ["Read", "Write", "Glob", "Grep", "WebSearch", "WebFetch"],
        "disallowed_tools": ["Bash"],
        "permission_mode": "bypassPermissions",
    },
}
DEFAULT_MODE = "agent"


@dataclass(frozen=True)
class ToolCall:
    """A tool call, as painted onto the page. Copied from fi-runner's contract,
    minimal: only what the interface needs to show."""

    name: str
    input: dict[str, Any] | None = None
    id: str | None = None
    is_error: bool | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class TurnResult:
    text: str
    usage: dict[str, Any] | None = None
    session_id: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


class Engine:
    """AIRE's engine: owner of the SDK, the modes and the memory.

    One live `ClaudeSDKClient` per session (pool = hot cache). A miss does not
    mean the session died: it is rebuilt from the store with `resume=`, which is
    what makes the memory survive a process restart.
    """

    def __init__(self, session_store: Any) -> None:
        self.session_store = session_store
        self._pool: dict[str, ClaudeSDKClient] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()

    def _cwd(self, project: str) -> Path:
        ws = WORKSPACES / project
        ws.mkdir(parents=True, exist_ok=True)
        return ws

    def session_key(self, project: str, session: str) -> dict[str, str]:
        """The store key. The `project_key` is NOT invented: the SDK derives it
        from the `cwd` (`project_key_for_directory`) when it WRITES the transcript,
        so the READING side must derive it the same way or every `load()` misses."""
        return {
            "project_key": project_key_for_directory(str(self._cwd(project))),
            "session_id": sdk_session_uuid(session),
        }

    async def has_session(self, project: str, session: str) -> bool:
        return bool(await self.session_store.load(self.session_key(project, session)))

    def _build_options(self, project: str, session: str, mode: str, resuming: bool) -> Any:
        from claude_agent_sdk import ClaudeAgentOptions

        policy = MODES.get(mode, MODES[DEFAULT_MODE])
        sdk_uuid = sdk_session_uuid(session)
        env = {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
        if os.environ.get("AIRE_ISOLATE_CONFIG") == "1":
            # In a container: no Keychain, the credential comes in via env and
            # CLAUDE_CONFIG_DIR=/tmp keeps the container from storing anything.
            # NOT forced locally (the CLI's live credential lives in the macOS
            # Keychain).
            cfg = Path("/tmp/aire-config") / project
            cfg.mkdir(parents=True, exist_ok=True)
            env["CLAUDE_CONFIG_DIR"] = str(cfg)
        kwargs: dict[str, Any] = {
            "system_prompt": SYSTEM_PROMPT,
            "allowed_tools": list(policy["allowed_tools"]),
            "disallowed_tools": list(policy["disallowed_tools"]),
            "permission_mode": policy["permission_mode"],
            "cwd": str(self._cwd(project)),
            "setting_sources": [],  # do NOT inherit the machine's CLAUDE.md/settings
            "strict_mcp_config": True,  # do NOT inherit the host machine's MCP servers
            "env": env,
            "session_store": self.session_store,
            "session_store_flush": "eager",  # no loss window if the process dies
        }
        # session_id=<uuid> SETS the id of a session being BORN; resume=<uuid>
        # RECOVERS an existing one. They are mutually exclusive: passing session_id
        # on a continuation does NOT resume — it starts a new session, clobbering
        # the id and losing the memory. That is why we ask the store (has_session)
        # instead of guessing from the pool.
        if resuming:
            kwargs["resume"] = sdk_uuid
        else:
            kwargs["session_id"] = sdk_uuid
        return ClaudeAgentOptions(**kwargs)

    async def _client_for(self, project: str, session: str, mode: str) -> tuple[ClaudeSDKClient, asyncio.Lock]:
        pool_key = f"{project}/{session}"
        async with self._pool_lock:
            client = self._pool.get(pool_key)
            if client is None:
                resuming = await self.has_session(project, session)
                options = self._build_options(project, session, mode, resuming)
                client = ClaudeSDKClient(options=options)
                await client.__aenter__()
                self._pool[pool_key] = client
            lock = self._locks.setdefault(pool_key, asyncio.Lock())
        return client, lock

    async def run_stream(
        self, project: str, session: str, prompt: str, mode: str = DEFAULT_MODE
    ) -> AsyncIterator[dict[str, Any]]:
        """One turn, live. Emits {"type": "text"|"tool_call"|"result", ...} as it
        happens. The transcript mirrors itself to Postgres (session_store) — the
        agent's memory AND the page's memory are THE SAME transcript."""
        client, lock = await self._client_for(project, session, mode)
        async with lock:  # serializes turns on the same client (not concurrency-safe)
            await client.query(prompt)
            async for event in self._drain(client):
                yield event

    @staticmethod
    async def _drain(client: ClaudeSDKClient) -> AsyncIterator[dict[str, Any]]:
        """Drains the SDK's response and emits it live. Copied from fi-runner's
        proven turn loop: types are identified via `type(m).__name__` (defensive
        across SDK versions), and a tool's RESULT does not come back as an
        assistant message but as a `ToolResultBlock` inside a USER message — they
        are paired by `tool_use_id`."""
        parts: list[str] = []
        usage: dict[str, Any] | None = None
        session_id: str | None = None
        tools: list[ToolCall] = []
        by_id: dict[str, int] = {}
        start_ts: dict[str, float] = {}
        async for message in client.receive_response():
            kind = type(message).__name__
            content = getattr(message, "content", None)
            if kind == "AssistantMessage" and isinstance(content, list):
                for block in content:
                    btype = type(block).__name__
                    if btype == "TextBlock":
                        text = getattr(block, "text", "") or ""
                        if text:
                            parts.append(text)
                            yield {"type": "text", "text": text}
                    elif btype == "ToolUseBlock":
                        tc = ToolCall(
                            name=getattr(block, "name", "") or "",
                            input=getattr(block, "input", None),
                            id=getattr(block, "id", None),
                        )
                        if tc.id is not None:
                            by_id[tc.id] = len(tools)
                            start_ts[tc.id] = time.monotonic()
                        tools.append(tc)
                        yield {"type": "tool_call", "tool": tc}
            elif kind == "UserMessage" and isinstance(content, list):
                for block in content:
                    if type(block).__name__ != "ToolResultBlock":
                        continue
                    use_id = getattr(block, "tool_use_id", None)
                    idx = by_id.get(use_id)
                    if idx is not None:
                        raw_err = getattr(block, "is_error", None)
                        t0 = start_ts.get(use_id)
                        dur = int((time.monotonic() - t0) * 1000) if t0 is not None else None
                        tools[idx] = replace(
                            tools[idx],
                            is_error=None if raw_err is None else bool(raw_err),
                            duration_ms=dur,
                        )
            elif kind == "ResultMessage":
                raw = getattr(message, "usage", None)
                if raw is not None:
                    usage = dict(raw) if isinstance(raw, dict) else dict(getattr(raw, "__dict__", {}) or {})
                    cost = getattr(message, "total_cost_usd", None)
                    if cost is not None:
                        usage["total_cost_usd"] = cost
                session_id = getattr(message, "session_id", None) or session_id
        yield {
            "type": "result",
            "result": TurnResult(text="".join(parts), usage=usage, session_id=session_id, tool_calls=tuple(tools)),
        }

    async def load_transcript(self, project: str, session: str) -> list[dict[str, Any]]:
        """What the agent remembers, which is the same thing the page repaints.
        The transcript does not live in the HTTP connection: it lives in Postgres."""
        return await self.session_store.load(self.session_key(project, session)) or []

    async def aclose(self) -> None:
        async with self._pool_lock:
            for client in self._pool.values():
                try:
                    await client.__aexit__(None, None, None)
                except Exception:  # noqa: BLE001 - best-effort teardown
                    pass
            self._pool.clear()
            self._locks.clear()
