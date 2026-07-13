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
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from ..backend import (
    MCPServerSpec,
    ToolCall,
    ToolPolicy,
    TurnImage,
    TurnResult,
    mcp_server_token,
    mcp_tool_id,
)


class ClaudeCodeBackend:
    """Agent backend backed by the Claude Agent SDK (Claude Code)."""

    def __init__(
        self,
        default_model: str | None = None,
        *,
        cwd: str | None = None,
        setting_sources: list[str] | None = None,
        env: dict[str, str] | None = None,
        session_store: Any | None = None,
        session_store_flush: str = "eager",
        session_project_key: str = "fi-runner",
    ) -> None:
        self.default_model = default_model
        self.cwd = cwd
        self.setting_sources = setting_sources
        # Explicit provider/auth env (merged on top of os.environ by the SDK).
        # e.g. {"ANTHROPIC_API_KEY": "..."} for API mode, or
        # {"CLAUDE_CODE_USE_BEDROCK": "1"} for Bedrock. None = ambient env only.
        self.env = env
        # The SDK's own durable transcript (SessionStore, SDK >= 0.1.64). INJECTED,
        # never constructed here: the deploy owns the DSN, the credentials and the
        # lifetime — fi-runner owns neither, exactly like `Runner(conversation_store=)`.
        #
        # Why it matters: without it the ONLY memory is `self._pool` (a dict in RAM,
        # gone the moment the process restarts) plus the text history-replay, which
        # persists `Message(role, content)` — PLAIN TEXT. That type cannot represent
        # a `tool_use` or a `tool_result`, so every tool the agent ran is reported in
        # the TurnResult and then thrown away: on the next turn it re-reads its own
        # prose but does NOT remember that it already ran the bash, nor what came
        # back. The native store keeps the real transcript, blocks included.
        self.session_store = session_store
        # "batched" (the SDK default) coalesces writes and can LOSE entries if the
        # process dies mid-turn. "eager" writes each entry as it arrives — no loss
        # window. A runner in a container gets recycled without warning, so eager is
        # our default, not the SDK's.
        self.session_store_flush = session_store_flush
        # The store namespaces sessions by project; one key for this runner's fleet.
        self.session_project_key = session_project_key
        # The pool is a HOT CACHE, not the truth. A hit skips re-spawning the CLI
        # subprocess (the fast path, unchanged). A miss no longer means the session
        # is gone — it is rebuilt from the store with `resume=`. That is the safety
        # net this backend never had.
        self._pool: dict[str, Any] = {}  # session_id -> entered ClaudeSDKClient
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()

    # --- SDK-free builders (unit-testable without the SDK installed) ---------

    #: Namespace for deriving the SDK's session UUID from fi-runner's session id.
    #: Frozen: change it and every existing session becomes unreachable.
    SESSION_NAMESPACE = uuid.UUID("6f1e6f4c-6f5a-5f4b-9c2a-5f1e6f4c6f5a")

    @classmethod
    def sdk_session_uuid(cls, session_id: str) -> str:
        """fi-runner's session id → the UUID the SDK demands.

        The SDK requires a valid UUID (`types.py:1649`), while a caller's session
        id is an arbitrary string (og118 hands it a conversation id, insult a
        channel id). uuid5 derives one DETERMINISTICALLY from the other: readable
        names outside, UUIDs inside, and no mapping table to keep in sync — the
        same id always resolves to the same session, including after a restart,
        which is the whole point.
        """
        return str(uuid.uuid5(cls.SESSION_NAMESPACE, session_id))

    def session_key(self, session_id: str) -> dict[str, str]:
        """The store's key for a session (`SessionKey`: project + session)."""
        return {
            "project_key": self.session_project_key,
            "session_id": self.sdk_session_uuid(session_id),
        }

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
                # env_passthrough=True forwards the full os.environ (legacy
                # default); =False sends the safe whitelist (no secrets).
                # Always set ``env`` explicitly so the SDK doesn't default to
                # passthrough on its own when we omit the key.
                if spec.env_passthrough:
                    entry["env"] = dict(os.environ)
                else:
                    from ..backend import safe_subprocess_env
                    entry["env"] = safe_subprocess_env()
                out[spec.name] = entry
        return out

    def build_options(
        self,
        *,
        system_prompt: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
        session_id: str | None = None,
        resuming: bool = False,
    ) -> Any:
        """Build ``ClaudeAgentOptions``. The seam a pooled consumer (e.g. insult)
        can call to construct options for its own long-lived client.

        When a ``session_store`` is wired, the turn also carries the session key —
        and WHICH key is the trap the SDK sets for you (`types.py:1649`):

            session_id=<uuid>  → PIN the id of a session being BORN.
            resume=<uuid>      → RECOVER an existing session from the store.

        They are mutually exclusive. Passing ``session_id=`` on a continuation does
        NOT resume: it starts a fresh session that stomps the id, silently losing
        the transcript you were trying to reach. So the caller says which one this
        is (``resuming``), decided by ASKING THE STORE whether the session exists —
        never by guessing from the pool, which is only a cache.
        """
        from claude_agent_sdk import ClaudeAgentOptions

        kwargs: dict[str, Any] = {
            "system_prompt": system_prompt,
            "mcp_servers": self._mcp_dict(mcp_servers),
            "allowed_tools": self._allowlist(mcp_servers, tool_policy),
            "disallowed_tools": list(tool_policy.builtin_disallowed),
            "permission_mode": tool_policy.permission_mode.value,
            # A Runner serves requests; it must never inherit the MCP servers of
            # whatever machine it happens to run on. Without this the CLI merges
            # the host's `.mcp.json` / user config, so a local og118 turn booted
            # the developer's chrome-devtools + cloudflare servers and opened
            # OAuth consent tabs in their browser. Only the servers this Runner
            # declares in `capabilities` are mounted.
            "strict_mcp_config": True,
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
        if self.session_store is not None and session_id is not None:
            kwargs["session_store"] = self.session_store
            kwargs["session_store_flush"] = self.session_store_flush
            sdk_uuid = self.sdk_session_uuid(session_id)
            if resuming:
                kwargs["resume"] = sdk_uuid
            else:
                kwargs["session_id"] = sdk_uuid
        return ClaudeAgentOptions(**kwargs)

    @staticmethod
    def build_query_input(
        user_message: str, images: list[TurnImage] | None
    ) -> str | list[dict[str, Any]]:
        """The ``client.query()`` input for this turn — SDK-free and unit-testable.

        Text-only turns stay a plain string (byte-identical to before). A turn
        with images needs the SDK's STREAMING INPUT mode: a user message whose
        ``content`` is a block list — base64 image blocks first (Anthropic's
        recommended image-before-text ordering), then the text block (skipped
        when the message is empty: an image-only send is valid, the picture IS
        the message)."""
        if not images:
            return user_message
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": img.media_type, "data": img.data},
            }
            for img in images
        ]
        if user_message and user_message.strip():
            content.append({"type": "text", "text": user_message})
        return content

    @staticmethod
    async def _query(client: Any, user_message: str, images: list[TurnImage] | None) -> None:
        """Send the turn's user message. Plain string for text-only turns; for
        image turns, the SDK's streaming-input mode (an async iterable yielding
        one user message dict whose content carries the image blocks — the
        string mode does not support attachments). ``session_id`` is left to the
        SDK default so pooled stateful clients behave exactly as with a string
        query."""
        payload = ClaudeCodeBackend.build_query_input(user_message, images)
        if isinstance(payload, str):
            await client.query(payload)
            return

        async def _messages() -> AsyncIterator[dict[str, Any]]:
            yield {
                "type": "user",
                "message": {"role": "user", "content": payload},
                "parent_tool_use_id": None,
            }

        await client.query(_messages())

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
        # Wall-clock start (monotonic) for each ToolUseBlock by id — paired with
        # its ToolResultBlock to fill ``duration_ms``. monotonic survives clock
        # jumps and is what you want for "how long did THIS take".
        start_ts: dict[str, float] = {}
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
                            start_ts[tc.id] = time.monotonic()
                        tool_calls.append(tc)
            elif kind == "UserMessage" and isinstance(content, list):
                for block in content:  # tool RESULTS feed back as ToolResultBlocks
                    if type(block).__name__ != "ToolResultBlock":
                        continue
                    use_id = getattr(block, "tool_use_id", None)
                    idx = by_id.get(use_id)
                    if idx is not None:
                        # Respect the contract: None = unknown. A missing is_error
                        # stays None (don't claim success); only a present value coerces.
                        raw_err = getattr(block, "is_error", None)
                        t0 = start_ts.get(use_id)
                        dur = int((time.monotonic() - t0) * 1000) if t0 is not None else None
                        tool_calls[idx] = replace(
                            tool_calls[idx],
                            is_error=None if raw_err is None else bool(raw_err),
                            duration_ms=dur,
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

    async def _session_exists(self, session_id: str) -> bool:
        """Does the store already hold this session? `load()` returns None when it
        does not (SDK Protocol, types.py:1370). This is what decides born-vs-resume
        — the pool cannot answer it: an empty pool after a restart says nothing
        about whether the transcript survived, and that confusion is precisely the
        bug (a `session_id=` on a continuation stomps the session)."""
        if self.session_store is None:
            return False
        entries = await self.session_store.load(self.session_key(session_id))
        return bool(entries)

    async def _client_for(self, session_id: str, options_for: Any) -> Any:
        """The pooled client for a session — rebuilt from the STORE on a miss.

        Hit: the live client (fast path, unchanged — no re-spawn of the CLI).
        Miss: the process restarted (or this replica never saw the session). With a
        store wired, that is now recoverable: rebuild the client with `resume=`, and
        the SDK materializes the transcript — tool_use and tool_result blocks
        included — from the store. Without a store this stays exactly as before: a
        miss means a fresh, amnesiac session.
        """
        from claude_agent_sdk import ClaudeSDKClient

        async with self._pool_lock:
            client = self._pool.get(session_id)
            if client is None:
                resuming = await self._session_exists(session_id)
                client = ClaudeSDKClient(options=options_for(resuming))
                await client.__aenter__()
                self._pool[session_id] = client
            lock = self._session_locks.setdefault(session_id, asyncio.Lock())
        return client, lock

    async def run_turn(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
        session_id: str | None = None,
        images: list[TurnImage] | None = None,
    ) -> TurnResult:
        try:
            from claude_agent_sdk import ClaudeSDKClient
        except ImportError as exc:  # pragma: no cover - exercised only without extra
            raise ImportError(
                "ClaudeCodeBackend requires the Claude Agent SDK. "
                "Install via: pip install 'fi-runner[claude]'"
            ) from exc

        def options_for(resuming: bool) -> Any:
            return self.build_options(
                system_prompt=system_prompt,
                mcp_servers=mcp_servers,
                tool_policy=tool_policy,
                model=model,
                session_id=session_id,
                resuming=resuming,
            )

        # One-shot: fresh client, no continuity (and nothing to resume).
        if session_id is None:
            async with ClaudeSDKClient(options=options_for(False)) as client:
                await self._query(client, user_message, images)
                text, usage, sess, tools = await self._collect(client)
                return TurnResult(text=text, usage=usage, session_id=sess, tool_calls=tools)

        # Stateful: the pooled client (hot cache) — or rebuilt from the store.
        client, lock = await self._client_for(session_id, options_for)
        async with lock:  # serialize turns on the same client (not concurrency-safe)
            await self._query(client, user_message, images)
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
        start_ts: dict[str, float] = {}  # tool_use_id -> monotonic start (for duration_ms)
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
                            start_ts[tc.id] = time.monotonic()
                        tool_calls.append(tc)
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
                        tool_calls[idx] = replace(
                            tool_calls[idx],
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
        images: list[TurnImage] | None = None,
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
        def options_for(resuming: bool) -> Any:
            return self.build_options(
                system_prompt=system_prompt,
                mcp_servers=mcp_servers,
                tool_policy=tool_policy,
                model=model,
                session_id=session_id,
                resuming=resuming,
            )

        if session_id is None:
            async with ClaudeSDKClient(options=options_for(False)) as client:
                await self._query(client, user_message, images)
                async for event in self._iter_events(client):
                    yield event
            return
        # Stateful: pooled client (hot cache) — or rebuilt from the store on a miss,
        # exactly as run_turn does. Same pool, same lock, same recovery.
        client, lock = await self._client_for(session_id, options_for)
        async with lock:
            await self._query(client, user_message, images)
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
