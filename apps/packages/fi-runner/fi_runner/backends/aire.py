"""AIREBackend — the persistent-server backend, an HTTP client of AIRE.

The third :class:`~fi_runner.backend.AgentBackend`, peer to ``ClaudeCodeBackend``
and ``CodexBackend``. The other two spawn a third-party CLI per turn and own
continuity locally (a pooled client, a text history-replay); this one calls
**AIRE** — Bernard's own always-up server that wraps the Claude Agent SDK and
owns the RAW transcript layer in the owner's Postgres.

That difference is the whole point (the two-layer storage doctrine): AIRE
remembers, so this backend is thin BY DESIGN. Session, transcript and resume all
live server-side (AIRE's ``session_store``); none of the tricks the CLI backends
need to fake continuity exist here, because the memory is not local.

The door speaks AIRE's OWN protocol over HTTPS — not the Anthropic API::

    POST /projects/{project}/init                  → set the casita's fixed prompt
    POST /projects/{project}/sessions/{s}/messages → run one turn (SSE events)

Auth is a long Bearer secret (AIRE's "LLM door"). Configure it on the
constructor or via the env — ``AIRE_GATE_URL`` and ``AIRE_AUTH_TOKEN`` (a
canary token works too: same header).

SECOND CUT (2026-08-20). The door grew (aire-server #29, commits a40f389 +
6d8bd9a): the message endpoint now accepts ``{message, mode, tools, model,
images, background}`` per turn, so the first cut's reject clauses became
forward clauses:

- ``system_prompt`` → forwarded via ``/init`` as the casita's fixed prompt,
  re-sent only when it changes. It is per-CASITA, not per-turn — that is the
  door's shape, not a limitation of this backend.
- ``model`` → forwarded in the body (a short name like ``"haiku"`` or a full
  id); AIRE pins it on the session's pooled client. The result's ``model``
  carries REAL provenance — AIRE reads it off the AssistantMessages, so it is
  the model that answered, never an echo of the request.
- ``images`` → forwarded as ``{media_type, data}`` blocks (base64, no ``data:``
  prefix). The door enforces its own limits (max 4 × 5MB b64, MIME in
  jpeg/png/webp/gif) and an image-only message is a valid turn.
- ``mcp_servers`` → translated to registry NAMES: only ``spec.name`` crosses
  the wire (as the door's ``tools`` field, forcing ``mode=agent``); the local
  ``command``/``args`` cannot and do not. AIRE mounts its own vetted in-process
  server of that name (today: ``"memory"``). A name outside the registry is
  still rejected HARD — by the door's 422, surfaced as ``BackendError``.
  Forward does not mean silent: arbitrary MCP specs remain RCE by design.
- ``tool_policy`` → still NOT forwarded (the one remaining gap): AIRE owns the
  tool config server-side, so a caller's permission_mode/allowlist is warned
  about, never silently honoured.

Requires the ``aire`` extra::

    pip install 'fi-runner[aire]'
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import AsyncIterator
from typing import Any

from ..backend import (
    BackendError,
    MCPServerSpec,
    PermissionMode,
    ToolCall,
    ToolPolicy,
    TurnImage,
    TurnResult,
)

_logger = logging.getLogger(__name__)


class AIREBackend:
    """Agent backend backed by AIRE (a persistent HTTP server, not a CLI)."""

    def __init__(
        self,
        project: str,
        *,
        gate_url: str | None = None,
        auth_token: str | None = None,
        default_model: str | None = None,
        default_mode: str = "complete",
        registry_tools: tuple[str, ...] = (),
        timeout: float = 300.0,
    ) -> None:
        # The AIRE casita this backend addresses. AIRE validates it
        # (``[a-zA-Z0-9_-]{1,128}``, "aire" reserved); we pass it through.
        self.project = project
        self.gate_url = (gate_url or os.environ.get("AIRE_GATE_URL", "")).rstrip("/")
        self.auth_token = (
            auth_token
            or os.environ.get("AIRE_AUTH_TOKEN", "")
            or os.environ.get("AIRE_CANARY_TOKEN", "")
        )
        # Forwarded per turn when the caller names no model of its own; AIRE
        # pins it on the session's pooled client (None = AIRE's server default).
        self.default_model = default_model
        # "complete" = no tools, the substitute for the raw API. When registry_tools
        # is set the turn runs in "agent" mode instead (the door requires it).
        self.default_mode = default_mode
        # Vetted AIRE-registry tool NAMES this backend requests on EVERY turn
        # (e.g. ("memory",)), unioned with the names of any per-turn mcp_servers
        # and sent as the door's `tools` field (aire-server #29). The door
        # mounts the matching in-process server server-side and 422s any name
        # outside its registry.
        self.registry_tools = tuple(registry_tools)
        self.timeout = timeout
        # /init state: the casita's fixed prompt last written, so we re-init only
        # when the system_prompt actually changes (idempotent, but a round trip).
        self._inited_prompt: str | None = None
        self._client: Any = None  # lazy httpx.AsyncClient

    # --- door plumbing -------------------------------------------------------

    def _http(self) -> Any:
        if self._client is None:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - exercised only without extra
                raise ImportError(
                    "AIREBackend requires httpx. Install via: pip install 'fi-runner[aire]'"
                ) from exc
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}

    def _require_door(self) -> None:
        if not self.gate_url or not self.auth_token:
            raise BackendError(
                "AIRE door not configured — set AIRE_GATE_URL and AIRE_AUTH_TOKEN "
                "(or pass gate_url/auth_token to AIREBackend)."
            )

    def _turn_tools(self, mcp_servers: list[MCPServerSpec]) -> list[str]:
        """The registry NAMES this turn requests: the backend's standing
        ``registry_tools`` plus each per-turn spec's name, deduped in order.
        Only the name crosses the wire — the specs' local ``command``/``args``
        cannot run on AIRE; the door mounts its OWN server of that name, and
        422s (→ ``BackendError``) any name its registry does not ship."""
        names = list(self.registry_tools) + [s.name for s in mcp_servers]
        return list(dict.fromkeys(n for n in names if n))

    async def _ensure_prompt(self, system_prompt: str) -> None:
        """Write the casita's fixed prompt via ``/init`` when it changes. The
        message endpoint auto-creates the casita, so a turn with no persona needs
        no init at all — this fires only to install/refresh a non-empty prompt."""
        prompt = (system_prompt or "").strip()
        if not prompt or prompt == self._inited_prompt:
            return
        res = await self._http().post(
            f"{self.gate_url}/projects/{self.project}/init",
            headers=self._headers,
            json={"claude_md": prompt},
        )
        if res.status_code >= 400:
            raise BackendError(f"AIRE init {res.status_code}: {res.text}")
        self._inited_prompt = prompt

    # --- SSE parsing (AIRE events -> fi-runner events) -----------------------

    @staticmethod
    def _to_toolcall(d: dict[str, Any]) -> ToolCall:
        return ToolCall.make(
            d.get("name", "") or "",
            input=d.get("input"),
            id=d.get("id"),
            is_error=d.get("is_error"),
            duration_ms=d.get("duration_ms"),
        )

    def _to_result(self, d: dict[str, Any], session: str) -> TurnResult:
        tools = [self._to_toolcall(t) for t in (d.get("tool_calls") or [])]
        return TurnResult(
            text=d.get("text", "") or "",
            usage=d.get("usage"),
            session_id=d.get("session_id") or session,
            tool_calls=tools,
            # Real provenance: AIRE reads this off the AssistantMessages, so it
            # is the model that ANSWERED, not an echo of the request.
            model=d.get("model") or None,
        )

    async def _stream_events(
        self, session: str, body: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        """POST the turn and yield AIRE's SSE events as dicts. Each ``data:`` line
        is a full event object carrying its own ``type`` (AIRE's ``_plain(ev)``)."""
        async with self._http().stream(
            "POST",
            f"{self.gate_url}/projects/{self.project}/sessions/{session}/messages",
            headers=self._headers,
            json=body,
        ) as res:
            if res.status_code >= 400:
                detail = (await res.aread()).decode("utf-8", "replace")
                raise BackendError(f"AIRE door {res.status_code}: {detail}")
            async for line in res.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                if not payload:
                    continue
                try:
                    yield json.loads(payload)
                except json.JSONDecodeError:  # a keep-alive or partial line — skip
                    continue

    def _warn_unenforceable(self, tool_policy: ToolPolicy) -> None:
        """The one remaining unforwardable input: AIRE configures the tool
        policy server-side. Warn when a caller set one, so a silent divergence
        never masquerades as an honoured request."""
        if tool_policy.builtin_allowed or tool_policy.permission_mode is not PermissionMode.DEFAULT:
            _logger.warning(
                "AIREBackend: tool_policy is not forwarded — AIRE configures tools "
                "server-side (mode=%r). The caller's permission_mode/allowlist has "
                "no effect until the door grows per-turn tools.",
                self.default_mode,
            )

    # --- the AgentBackend port ----------------------------------------------

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
        """Live-streaming turn through the AIRE door. Re-emits AIRE's SSE events
        in fi-runner's stream vocabulary (``text`` / ``tool_call`` / ``result``),
        so the Runner's glass-box stream is unchanged."""
        self._require_door()
        self._warn_unenforceable(tool_policy)
        await self._ensure_prompt(system_prompt)
        # AIRE keys memory by (project, session); a one-shot needs a throwaway name.
        session = session_id or uuid.uuid4().hex
        tools = self._turn_tools(mcp_servers)
        # The door requires mode=agent whenever tools are requested (complete has
        # no agentic loop); a tool-free backend keeps its configured default_mode.
        body: dict[str, Any] = {
            "mode": "agent" if tools else self.default_mode,
            "message": user_message,
        }
        if tools:
            body["tools"] = tools
        chosen_model = model or self.default_model
        if chosen_model:
            body["model"] = chosen_model
        if images:
            body["images"] = [{"media_type": i.media_type, "data": i.data} for i in images]
        async for ev in self._stream_events(session, body):
            kind = ev.get("type")
            if kind == "text":
                text = ev.get("text") or ""
                if text:
                    yield {"type": "text", "text": text}
            elif kind == "tool_call":
                yield {"type": "tool_call", "tool": self._to_toolcall(ev.get("tool") or {})}
            elif kind == "result":
                yield {"type": "result", "result": self._to_result(ev.get("result") or {}, session)}
            elif kind == "error":
                raise BackendError(f"AIRE turn error [{ev.get('error')}]: {ev.get('detail', '')}")
            # "done" is the stream terminator — nothing to forward.

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
        """One turn through the AIRE door. Drains the stream and returns the final
        ``result`` event. If AIRE never emits one (a torn stream), that is a real
        failure — surface it, do not invent an empty success (Art. 2)."""
        result: TurnResult | None = None
        async for event in self.run_turn_stream(
            system_prompt=system_prompt,
            user_message=user_message,
            mcp_servers=mcp_servers,
            tool_policy=tool_policy,
            model=model,
            session_id=session_id,
            images=images,
        ):
            if event.get("type") == "result":
                result = event["result"]
        if result is None:
            raise BackendError("AIRE door closed the stream with no result event.")
        return result

    async def aclose(self) -> None:
        """Close the pooled HTTP client (call on shutdown / idle reap)."""
        if self._client is not None:
            try:
                await self._client.aclose()
            finally:
                self._client = None
