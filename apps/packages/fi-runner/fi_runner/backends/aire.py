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

FIRST-CUT SCOPE (2026-07-27). AIRE's message endpoint accepts only
``{message, mode}`` per turn, so this backend faithfully covers the **companion /
text turn** — the exact shape where og118 disabled the SDK ``session_store``
mirror (#358/#359) because AIRE owns the memory. Everything the door does NOT
accept per turn yet is a KNOWN gap, filed as aire-server backlog (grow the door:
per-turn model / mcp_servers / tool_policy / images). Until then this backend
REJECTS LOUDLY rather than silently answering wrong:

- ``system_prompt`` → forwarded via ``/init`` as the casita's fixed prompt,
  re-sent only when it changes. It is per-CASITA, not per-turn — that is the
  door's shape, not a limitation of this backend.
- ``images`` (vision) → raises: the door takes no per-turn image blocks yet.
- ``mcp_servers`` (tools) → raises when non-empty: tools run INSIDE AIRE's
  engine, configured server-side, never handed per turn. A caller expecting a
  tool to fire must learn it will not, not get a silent text answer.
- ``model`` / ``tool_policy`` → accepted for interface symmetry but NOT
  enforceable from the caller (AIRE picks the model and the tool config
  server-side). The result's ``model`` stays ``None`` — honest "engine-decided",
  never an echo of a request AIRE may not have honoured.

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
        # AIRE picks the model server-side; kept for interface symmetry and to
        # warn when a caller asks for a per-turn model we cannot enforce yet.
        self.default_model = default_model
        # "complete" = no tools, the substitute for the raw API. When registry_tools
        # is set the turn runs in "agent" mode instead (the door requires it).
        self.default_mode = default_mode
        # Vetted AIRE-registry tool NAMES this backend requests each turn (e.g.
        # ("memory",)), sent as the door's `tools` field (aire-server #29). These
        # are NOT the caller's local MCPServerSpecs — those cannot cross the wire
        # and are still rejected. A consumer that wants tools on AIRE names them
        # here; the door mounts the matching in-process server server-side.
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

    @staticmethod
    def _reject_unsupported(
        mcp_servers: list[MCPServerSpec], images: list[TurnImage] | None
    ) -> None:
        """Fail loudly on capabilities the door cannot honour per turn, so a
        caller never gets a silent text answer where it expected vision or tools."""
        if images:
            raise BackendError(
                "AIREBackend has no vision yet: AIRE's door takes no per-turn image "
                "blocks. Grow the door first (aire-server backlog)."
            )
        if mcp_servers:
            raise BackendError(
                f"AIREBackend cannot forward local MCP servers ({len(mcp_servers)} given): "
                "they run in the caller's process and cannot cross the wire. For tools on "
                "AIRE, pass registry_tools=(...) with the names of servers AIRE ships "
                "(e.g. \"memory\"); AIRE mounts them server-side."
            )

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
            model=None,  # AIRE picks the model server-side — no provenance yet (door gap)
        )

    async def _stream_events(
        self, session: str, message: str, mode: str
    ) -> AsyncIterator[dict[str, Any]]:
        """POST the turn and yield AIRE's SSE events as dicts. Each ``data:`` line
        is a full event object carrying its own ``type`` (AIRE's ``_plain(ev)``)."""
        body: dict[str, Any] = {"mode": mode, "message": message}
        if self.registry_tools:
            body["tools"] = list(self.registry_tools)
        async with self._http().stream(
            "POST",
            f"{self.gate_url}/projects/{self.project}/sessions/{session}/messages",
            headers=self._headers,
            json=body,
        ) as res:
            if res.status_code >= 400:
                body = (await res.aread()).decode("utf-8", "replace")
                raise BackendError(f"AIRE door {res.status_code}: {body}")
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

    def _warn_unenforceable(self, model: str | None, tool_policy: ToolPolicy) -> None:
        """The caller controls model + tools locally on the CLI backends; AIRE
        controls both server-side. Warn when a caller asked for either, so a
        silent divergence never masquerades as an honoured request."""
        chosen = model or self.default_model
        if chosen:
            _logger.warning(
                "AIREBackend: model %r is not enforceable — AIRE selects the model "
                "server-side (door gap). The turn runs on AIRE's configured model.",
                chosen,
            )
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
        self._reject_unsupported(mcp_servers, images)
        self._warn_unenforceable(model, tool_policy)
        await self._ensure_prompt(system_prompt)
        # AIRE keys memory by (project, session); a one-shot needs a throwaway name.
        session = session_id or uuid.uuid4().hex
        # The door requires mode=agent whenever tools are requested (complete has
        # no agentic loop); a tool-free backend keeps its configured default_mode.
        mode = "agent" if self.registry_tools else self.default_mode
        async for ev in self._stream_events(session, user_message, mode):
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
