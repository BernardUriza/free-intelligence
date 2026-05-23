"""ClaudeCodeBackend — wraps the Claude Agent SDK (a.k.a. Claude Code).

Runs on a Claude Pro/Max subscription via OAuth (or an API key), brings the
full Claude Code toolset (Bash/Read/Write/Edit/…) gated by the ToolPolicy, and
has the deepest MCP integration. The turn loop mirrors the proven pattern in
the insult runner (``type(message).__name__`` checks for resilience across SDK
versions).

Supports what a real runner needs:
- **Stateful sessions** (``session_id``): keeps a long-lived, pooled
  ``ClaudeSDKClient`` per session for conversation continuity (the client
  auto-continues its session across ``query()`` calls); a per-session lock
  serializes turns. Omit ``session_id`` for a one-shot turn.
- **In-process MCP servers**: an ``MCPServerSpec`` with ``server`` set is passed
  straight through (e.g. insult's insult_db), alongside stdio specs.
- **cwd + setting_sources** (constructor) so the agent can load a project
  CLAUDE.md, like insult does.

Requires the ``claude`` extra::

    pip install 'fi-runner[claude]'
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from ..backend import MCPServerSpec, ToolPolicy, TurnResult


class ClaudeCodeBackend:
    """Agent backend backed by the Claude Agent SDK (Claude Code)."""

    def __init__(
        self,
        default_model: str | None = None,
        *,
        cwd: str | None = None,
        setting_sources: list[str] | None = None,
    ) -> None:
        self.default_model = default_model
        self.cwd = cwd
        self.setting_sources = setting_sources
        self._pool: dict[str, Any] = {}  # session_id -> entered ClaudeSDKClient
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()

    # --- SDK-free builders (unit-testable without the SDK installed) ---------

    def _allowlist(self, mcp_servers: list[MCPServerSpec], tool_policy: ToolPolicy) -> list[str]:
        allowed = list(tool_policy.builtin_allowed)
        for spec in mcp_servers:
            if spec.tools:
                allowed.extend(f"mcp__{spec.name}__{tool}" for tool in spec.tools)
            else:
                allowed.append(f"mcp__{spec.name}")
        return allowed

    def _mcp_dict(self, mcp_servers: list[MCPServerSpec]) -> dict[str, Any]:
        """Build the SDK ``mcp_servers`` mapping (in-process objects or stdio dicts)."""
        out: dict[str, Any] = {}
        for spec in mcp_servers:
            if spec.is_in_process:
                out[spec.name] = spec.server
            else:
                entry: dict[str, Any] = {"command": spec.command, "args": spec.args}
                if spec.env_passthrough:
                    entry["env"] = dict(os.environ)
                out[spec.name] = entry
        return out

    def build_options(
        self,
        *,
        system_prompt: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
    ) -> Any:
        """Build ``ClaudeAgentOptions``. The seam a pooled consumer (e.g. insult)
        can call to construct options for its own long-lived client."""
        from claude_agent_sdk import ClaudeAgentOptions

        kwargs: dict[str, Any] = {
            "system_prompt": system_prompt,
            "mcp_servers": self._mcp_dict(mcp_servers),
            "allowed_tools": self._allowlist(mcp_servers, tool_policy),
            "disallowed_tools": list(tool_policy.builtin_disallowed),
            "permission_mode": tool_policy.permission_mode.value,
        }
        chosen_model = model or self.default_model
        if chosen_model:
            kwargs["model"] = chosen_model
        if self.cwd:
            kwargs["cwd"] = str(self.cwd)
        if self.setting_sources is not None:
            kwargs["setting_sources"] = list(self.setting_sources)
        return ClaudeAgentOptions(**kwargs)

    @staticmethod
    async def _collect(client: Any) -> str:
        parts: list[str] = []
        async for message in client.receive_response():
            if type(message).__name__ == "AssistantMessage":
                for block in getattr(message, "content", []) or []:
                    if type(block).__name__ == "TextBlock":
                        parts.append(getattr(block, "text", ""))
        return "".join(parts)

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
        try:
            from claude_agent_sdk import ClaudeSDKClient
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise ImportError(
                "ClaudeCodeBackend requires the Claude Agent SDK. "
                "Install via: pip install 'fi-runner[claude]'"
            ) from exc

        options = self.build_options(
            system_prompt=system_prompt,
            mcp_servers=mcp_servers,
            tool_policy=tool_policy,
            model=model,
        )

        # One-shot: fresh client, no continuity.
        if session_id is None:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_message)
                return TurnResult(text=await self._collect(client))

        # Stateful: reuse a pooled, long-lived client for this session.
        async with self._pool_lock:
            client = self._pool.get(session_id)
            if client is None:
                client = ClaudeSDKClient(options=options)
                await client.__aenter__()
                self._pool[session_id] = client
            lock = self._session_locks.setdefault(session_id, asyncio.Lock())
        async with lock:  # serialize turns on the same client (not concurrency-safe)
            await client.query(user_message)
            return TurnResult(text=await self._collect(client))

    async def aclose(self) -> None:
        """Close all pooled clients (call on shutdown / idle reap)."""
        async with self._pool_lock:
            for client in self._pool.values():
                try:
                    await client.__aexit__(None, None, None)
                except Exception:  # noqa: BLE001 - best-effort teardown
                    pass
            self._pool.clear()
            self._session_locks.clear()
