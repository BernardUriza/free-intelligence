"""ClaudeCodeBackend — wraps the Claude Agent SDK (a.k.a. Claude Code).

Runs on a Claude Pro/Max subscription via OAuth (or an API key), brings the
full Claude Code toolset (Bash/Read/Write/Edit/…) gated by the ToolPolicy, and
has the deepest MCP integration. The turn loop mirrors the proven pattern in
the insult runner (``type(message).__name__`` checks for resilience across SDK
versions).

Like Codex, this backend has two modes — but the Claude Agent SDK selects them
from the ENVIRONMENT, not from CLI args, so the duality is mostly automatic:
- **Subscription**: a Claude Max/Pro OAuth login (the default — what insult uses).
- **API motor**: ``ANTHROPIC_API_KEY`` set → direct Anthropic API; or
  ``CLAUDE_CODE_USE_BEDROCK=1`` / ``CLAUDE_CODE_USE_VERTEX=1`` → Bedrock / Vertex;
  ``ANTHROPIC_BASE_URL`` points at a proxy/custom endpoint.

Pass ``env=`` (constructor) to declare any of those explicitly on the backend
instead of relying on the ambient process env. The SDK MERGES ``options.env`` on
top of the inherited ``os.environ`` (it does not replace it), so a partial dict
like ``{"ANTHROPIC_API_KEY": "..."}`` overrides only that key and leaves PATH,
the OAuth config dir, etc. intact.

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
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from ..backend import MCPServerSpec, ToolCall, ToolPolicy, TurnResult, mcp_server_token, mcp_tool_id


class ClaudeCodeBackend:
    """Agent backend backed by the Claude Agent SDK (Claude Code)."""

    def __init__(
        self,
        default_model: str | None = None,
        *,
        cwd: str | None = None,
        setting_sources: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.default_model = default_model
        self.cwd = cwd
        self.setting_sources = setting_sources
        # Explicit provider/auth env (merged on top of os.environ by the SDK).
        # e.g. {"ANTHROPIC_API_KEY": "..."} for API mode, or
        # {"CLAUDE_CODE_USE_BEDROCK": "1"} for Bedrock. None = ambient env only.
        self.env = env
        self._pool: dict[str, Any] = {}  # session_id -> entered ClaudeSDKClient
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()

    # --- SDK-free builders (unit-testable without the SDK installed) ---------

    def _allowlist(self, mcp_servers: list[MCPServerSpec], tool_policy: ToolPolicy) -> list[str]:
        allowed = list(tool_policy.builtin_allowed)
        for spec in mcp_servers:
            if spec.tools:
                allowed.extend(mcp_tool_id(spec.name, tool) for tool in spec.tools)
            else:
                allowed.append(mcp_server_token(spec.name))
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
        if self.env is not None:
            kwargs["env"] = dict(self.env)  # SDK merges this over os.environ
        return ClaudeAgentOptions(**kwargs)

    @staticmethod
    async def _collect(
        client: Any,
    ) -> tuple[str, dict[str, Any] | None, str | None, list[ToolCall]]:
        """Drain the SDK response: assistant text, the tool-trace, plus the final
        ResultMessage's token usage / cost / session id, so a turn reports what it
        spent AND what it did (the gaps a Claude-backed run otherwise leaves in
        turn telemetry). Tool calls arrive as ``ToolUseBlock``s in an
        ``AssistantMessage``; their success/failure comes back as
        ``ToolResultBlock``s in the following ``UserMessage`` — matched by id."""
        parts: list[str] = []
        usage: dict[str, Any] | None = None
        session_id: str | None = None
        tool_calls: list[ToolCall] = []
        by_id: dict[str, int] = {}  # tool_use_id -> index in tool_calls
        async for message in client.receive_response():
            kind = type(message).__name__
            content = getattr(message, "content", None)
            if kind == "AssistantMessage" and isinstance(content, list):
                for block in content:
                    btype = type(block).__name__
                    if btype == "TextBlock":
                        parts.append(getattr(block, "text", ""))
                    elif btype == "ToolUseBlock":
                        tc = ToolCall.make(
                            getattr(block, "name", "") or "",
                            input=getattr(block, "input", None),
                            id=getattr(block, "id", None),
                        )
                        if tc.id is not None:
                            by_id[tc.id] = len(tool_calls)
                        tool_calls.append(tc)
            elif kind == "UserMessage" and isinstance(content, list):
                for block in content:  # tool RESULTS feed back as ToolResultBlocks
                    if type(block).__name__ != "ToolResultBlock":
                        continue
                    idx = by_id.get(getattr(block, "tool_use_id", None))
                    if idx is not None:
                        # Respect the contract: None = unknown. A missing is_error
                        # stays None (don't claim success); only a present value coerces.
                        raw_err = getattr(block, "is_error", None)
                        tool_calls[idx] = replace(
                            tool_calls[idx], is_error=None if raw_err is None else bool(raw_err)
                        )
            elif kind == "ResultMessage":
                # Final message of a turn — carries usage, cost and session id.
                raw = getattr(message, "usage", None)
                if raw is not None:
                    usage = dict(raw) if isinstance(raw, dict) else dict(getattr(raw, "__dict__", {}) or {})
                    cost = getattr(message, "total_cost_usd", None)
                    if cost is not None:
                        usage["total_cost_usd"] = cost
                session_id = getattr(message, "session_id", None) or session_id
        return "".join(parts), usage, session_id, tool_calls

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
                text, usage, sess, tools = await self._collect(client)
                return TurnResult(text=text, usage=usage, session_id=sess, tool_calls=tools)

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
            text, usage, sess, tools = await self._collect(client)
            return TurnResult(text=text, usage=usage, session_id=sess or session_id, tool_calls=tools)

    @staticmethod
    async def _iter_events(client: Any) -> AsyncIterator[dict[str, Any]]:
        """Stream the SDK response as events AS THEY ARRIVE, then a final result.

        Mirrors :meth:`_collect` but YIELDS live: ``{"type":"text","text":delta}``
        per TextBlock, ``{"type":"tool_call","tool":ToolCall}`` per ToolUseBlock,
        and a closing ``{"type":"result","result":TurnResult}`` with the full text,
        tool-trace (with result status), usage and session id."""
        parts: list[str] = []
        usage: dict[str, Any] | None = None
        session_id: str | None = None
        tool_calls: list[ToolCall] = []
        by_id: dict[str, int] = {}
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
                        tc = ToolCall.make(
                            getattr(block, "name", "") or "",
                            input=getattr(block, "input", None),
                            id=getattr(block, "id", None),
                        )
                        if tc.id is not None:
                            by_id[tc.id] = len(tool_calls)
                        tool_calls.append(tc)
                        yield {"type": "tool_call", "tool": tc}
            elif kind == "UserMessage" and isinstance(content, list):
                for block in content:
                    if type(block).__name__ != "ToolResultBlock":
                        continue
                    idx = by_id.get(getattr(block, "tool_use_id", None))
                    if idx is not None:
                        raw_err = getattr(block, "is_error", None)
                        tool_calls[idx] = replace(tool_calls[idx], is_error=None if raw_err is None else bool(raw_err))
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
            "result": TurnResult(text="".join(parts), usage=usage, session_id=session_id, tool_calls=tool_calls),
        }

    async def run_turn_stream(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Live-streaming counterpart of :meth:`run_turn`: yields tool_call / text
        events as the turn unfolds, then a final result event. run_turn is
        unchanged."""
        try:
            from claude_agent_sdk import ClaudeSDKClient
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise ImportError(
                "ClaudeCodeBackend requires the Claude Agent SDK. Install via: pip install 'fi-runner[claude]'"
            ) from exc
        options = self.build_options(
            system_prompt=system_prompt, mcp_servers=mcp_servers, tool_policy=tool_policy, model=model
        )
        if session_id is None:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_message)
                async for event in self._iter_events(client):
                    yield event
            return
        # Stateful: reuse a pooled client (same pool + lock as run_turn).
        async with self._pool_lock:
            client = self._pool.get(session_id)
            if client is None:
                client = ClaudeSDKClient(options=options)
                await client.__aenter__()
                self._pool[session_id] = client
            lock = self._session_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            await client.query(user_message)
            async for event in self._iter_events(client):
                if event.get("type") == "result" and event["result"].session_id is None:
                    event = {"type": "result", "result": replace(event["result"], session_id=session_id)}
                yield event

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
