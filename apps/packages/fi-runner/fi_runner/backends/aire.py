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
  the wire (as the door's ``tools`` field, riding the configured mode — since
  aire-server 5ae8e33 the door runs registry tools in ``complete`` too); the
  local ``command``/``args`` cannot and do not. AIRE mounts its own vetted in-process
  server of that name (today: ``"memory"``). A name outside the registry is
  still rejected HARD — by the door's 422, surfaced as ``BackendError``.
  Forward does not mean silent: arbitrary MCP specs remain RCE by design.
- ``tool_policy`` → still NOT forwarded (the one remaining gap): AIRE owns the
  tool config server-side, so a caller's permission_mode/allowlist is warned
  about, never silently honoured.

THIRD CUT (2026-08-21, OG118-LIVING-CLAUDE). The casita may now vary PER TURN:
``project_for_turn`` is an optional zero-arg resolver consulted at the top of
every turn (og118 wires it to a request-scoped contextvar carrying
``og118-{conversation_id}``). A truthy return routes the turn — its ``/init``
and its message — to that casita; ``None``/empty falls back to the fixed
``project``. Init state is tracked per casita, so the first turn that lands in
a new casita installs its prompt there (AIRE's ``/init`` preserves the
casita's living part by contract, so repeats are safe).

THIN BIRTH (2026-08-21, aire-server ef21e68): a per-turn casita is NOT born
with a copy of the persona. The full ``system_prompt`` is installed ONCE in the
shared base casita (the fixed ``project``), and each chat casita is inited with
the one-line stub ``@base {project}`` — AIRE dereferences it at every spawn, so
the persona has a single live source instead of N frozen copies. A chat casita
born fat before this cut is rebased to the stub on the next process restart
(the per-process init cache is empty then), and AIRE's rebase preserves its
living part — the soul survives, the frozen base copy dies.

FOURTH CUT (2026-08-24, the end of the double memory). The backend now declares
``has_durable_memory`` and answers ``has_session`` off the door's
``GET /projects/{p}/sessions/{s}``, so the Runner RESUMES AIRE's transcript
instead of replaying the caller's. Until this cut the Runner probed
``backend.session_store`` — an attribute only the local SDK host owns — so this
backend, whose entire premise is that the memory is server-side, always answered
"no durable memory". Measured on the live gate: two turns of one og118 chat
landed in TWO different AIRE sessions of the same casita, the second carrying the
first as ``"Conversation so far: …"`` prompt text. Every turn re-paid the
conversation in tokens, re-paid the persona's cache creation on a cold spawn, and
orphaned a transcript nobody would ever resume — while the ``tool_use`` /
``tool_result`` blocks a text replay cannot carry were dropped each time.

Requires the ``aire`` extra::

    pip install 'fi-runner[aire]'
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import AsyncIterator, Callable
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


# The door speaks ``{"error": "<code>", "detail": "..."}``; the code is the only
# part that carries a decision (terminal vs backpressure vs unknown), and a
# formatted message string is the one place it cannot be read reliably — a
# wording change on AIRE's side would silently reroute a terminal cut into a
# retry storm for any consumer classifying by substring. Subclassing
# BackendError keeps every existing ``except BackendError`` working.
class AIREDoorError(BackendError):
    """A door failure that kept AIRE's own error code as data.

    ``code`` is AIRE's structured error name (``budget_exhausted``,
    ``slot_busy``, …) when the failure came from an SSE error event; ``None``
    when the door failed before speaking its protocol. ``http_status`` is the
    door's response status when the failure was an HTTP one.
    """

    def __init__(
        self, message: str, *, code: str | None = None, http_status: int | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


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
        project_for_turn: Callable[[], str | None] | None = None,
        timeout: float = 300.0,
    ) -> None:
        # The AIRE casita this backend addresses. AIRE validates it
        # (``[a-zA-Z0-9_-]{1,128}``, "aire" reserved); we pass it through.
        self.project = project
        # Optional per-turn casita resolver (casita-per-chat): consulted at the
        # top of every turn; a truthy return overrides ``project`` for that turn
        # only. The consumer owns the scoping policy (e.g. a request-scoped
        # contextvar carrying the chat's id); the backend stays stateless about
        # WHICH chat is talking.
        self.project_for_turn = project_for_turn
        self.gate_url = (gate_url or os.environ.get("AIRE_GATE_URL", "")).rstrip("/")
        self.auth_token = (
            auth_token
            or os.environ.get("AIRE_AUTH_TOKEN", "")
            or os.environ.get("AIRE_CANARY_TOKEN", "")
        )
        # Forwarded per turn when the caller names no model of its own; AIRE
        # pins it on the session's pooled client (None = AIRE's server default).
        self.default_model = default_model
        # The door mode EVERY turn rides, tools or not. Since aire-server 5ae8e33
        # the door accepts registry tools in mode=complete, so requesting tools no
        # longer forces "agent" (whose preset carries builtins nobody asked for).
        self.default_mode = default_mode
        # Vetted AIRE-registry tool NAMES this backend requests on EVERY turn
        # (e.g. ("memory",)), unioned with the names of any per-turn mcp_servers
        # and sent as the door's `tools` field (aire-server #29). The door
        # mounts the matching in-process server server-side and 422s any name
        # outside its registry.
        self.registry_tools = tuple(registry_tools)
        self.timeout = timeout
        # /init state PER CASITA, per process: the prompt last written to each
        # project, so we re-init only on change. The base casita holds the full
        # persona; each chat casita holds only the `@base` stub (thin birth) —
        # a fresh process re-inits both, which rebases fat-born chats to the stub.
        self._inited_prompts: dict[str, str] = {}
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
        422s (→ ``BackendError``) any name its registry does not ship.
        HTTP specs are NOT registry names — they ride ``remote_tools``."""
        names = list(self.registry_tools) + [s.name for s in mcp_servers if not s.is_http]
        return list(dict.fromkeys(n for n in names if n))

    def _remote_tools(self, mcp_servers: list[MCPServerSpec]) -> list[dict[str, Any]]:
        """The HTTP specs, as the door's ``remote_tools`` field (aire-server
        #48): servers the RUNNER hosts and AIRE only wires. The url's origin
        must be in the door's ``AIRE_REMOTE_TOOL_ORIGINS`` allowlist — an
        unlisted origin is a 422 (→ ``AIREDoorError``). The headers carry the
        runner's own bearer to its own server: data, never logged."""
        out: list[dict[str, Any]] = []
        for spec in mcp_servers:
            if not spec.is_http:
                continue
            entry: dict[str, Any] = {"name": spec.name, "url": spec.url}
            if spec.headers:
                entry["headers"] = dict(spec.headers)
            out.append(entry)
        return out

    def _resolve_project(self) -> str:
        """The casita THIS turn addresses: the per-turn resolver's answer when
        wired and truthy (casita-per-chat), else the fixed ``project``."""
        if self.project_for_turn is not None:
            override = self.project_for_turn()
            if override:
                return override
        return self.project

    async def _ensure_prompt(self, project: str, system_prompt: str) -> None:
        """Install the turn's prompt surface, thin-birth style (see module doc).

        The FULL persona lives only in the shared base casita (``self.project``);
        a per-turn chat casita gets the one-line ``@base`` stub AIRE dereferences
        at spawn (aire-server ef21e68). Base first, so a chat's very first spawn
        already finds a persona to dereference. The message endpoint auto-creates
        casitas, so a turn with no persona needs no init at all."""
        prompt = (system_prompt or "").strip()
        if not prompt:
            return
        await self._init_casita(self.project, prompt)
        if project != self.project:
            await self._init_casita(project, f"@base {self.project}")

    async def _init_casita(self, project: str, prompt: str) -> None:
        """POST ``/init`` unless this process already wrote that exact prompt to
        that casita. AIRE's ``/init`` preserves the casita's LIVING part (below
        its marker) by contract, so re-running it only rebases the base — which
        is how a fat-born chat casita converges to the stub after a restart."""
        if prompt == self._inited_prompts.get(project):
            return
        res = await self._http().post(
            f"{self.gate_url}/projects/{project}/init",
            headers=self._headers,
            json={"claude_md": prompt},
        )
        if res.status_code >= 400:
            raise BackendError(f"AIRE init {res.status_code}: {res.text}")
        self._inited_prompts[project] = prompt

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
        self, project: str, session: str, body: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        """POST the turn and yield AIRE's SSE events as dicts. Each ``data:`` line
        is a full event object carrying its own ``type`` (AIRE's ``_plain(ev)``)."""
        async with self._http().stream(
            "POST",
            f"{self.gate_url}/projects/{project}/sessions/{session}/messages",
            headers=self._headers,
            json=body,
        ) as res:
            if res.status_code >= 400:
                detail = (await res.aread()).decode("utf-8", "replace")
                raise AIREDoorError(
                    f"AIRE door {res.status_code}: {detail}", http_status=res.status_code
                )
            async for line in res.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                if not payload:
                    continue
                try:
                    ev = json.loads(payload)
                except json.JSONDecodeError:  # a keep-alive or partial line — skip
                    continue
                # AIRE's edge yields budget_exceeded / slot_busy payloads WITHOUT
                # a "type" key (messages.py emits them from except-clauses).
                # Dropping them kills the turn later as a bare "no result event";
                # normalizing keeps the error CODE the consumer classifies on.
                if "type" not in ev and "error" in ev:
                    ev = {"type": "error", **ev}
                yield ev

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

    # --- native memory -------------------------------------------------------

    @property
    def has_durable_memory(self) -> bool:
        """Always. AIRE's ``session_store`` in the owner's Postgres IS this
        backend's memory — it is the reason the backend exists, and unlike the
        CLI hosts it cannot be absent: there is no configuration in which this
        door remembers less than durably.

        Declaring it is what lets the Runner RESUME instead of replaying. Until
        this existed the Runner probed ``backend.session_store`` — an attribute
        only the local SDK host has — so this backend always answered no, and
        every turn re-sent the whole conversation as prompt text AND was handed
        ``session_id=None``, minting a throwaway session per turn. The casita
        filled with transcripts nobody ever resumed, and the ``tool_use`` /
        ``tool_result`` blocks a text replay cannot carry were lost each time."""
        return True

    async def has_session(self, session_id: str) -> bool:
        """Does AIRE already hold this session's transcript, in the casita THIS
        turn addresses? Answered by the door (``GET /projects/{p}/sessions/{s}``),
        which exposes the engine's own resume check.

        The casita is resolved the same way a turn resolves it, so a per-chat
        consumer asks about the chat it is actually about to send. A door that
        cannot answer (unreachable, or an older AIRE without the route) returns
        False: the Runner then replays, which is what it did before this method
        existed — degrade to the old cost, never to a wrong resume."""
        self._require_door()
        project = self._resolve_project()
        try:
            res = await self._http().get(
                f"{self.gate_url}/projects/{project}/sessions/{session_id}",
                headers=self._headers,
            )
        except Exception:  # noqa: BLE001 - any transport failure degrades to replay
            _logger.warning("AIREBackend: session probe failed for %s/%s", project, session_id)
            return False
        if res.status_code >= 400:
            return False
        return bool(res.json().get("exists"))

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
        project = self._resolve_project()
        await self._ensure_prompt(project, system_prompt)
        # AIRE keys memory by (project, session); a one-shot needs a throwaway name.
        session = session_id or uuid.uuid4().hex
        tools = self._turn_tools(mcp_servers)
        # Tools ride the configured mode as-is. The old guard that 422ed tools in
        # mode=complete fell (aire-server 5ae8e33, measured live: a complete turn
        # with tools:["persona"] executed the tool fine) — forcing mode=agent here
        # would drag in the agent preset's builtins the consumer never asked for.
        body: dict[str, Any] = {
            "mode": self.default_mode,
            "message": user_message,
        }
        if tools:
            body["tools"] = tools
        if remote := self._remote_tools(mcp_servers):
            body["remote_tools"] = remote
        chosen_model = model or self.default_model
        if chosen_model:
            body["model"] = chosen_model
        if images:
            body["images"] = [{"media_type": i.media_type, "data": i.data} for i in images]
        async for ev in self._stream_events(project, session, body):
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
                code = ev.get("error")
                raise AIREDoorError(
                    f"AIRE turn error [{code}]: {ev.get('detail', '')}", code=code or None
                )
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
        failure — surface it, do not invent an empty success (Art. 2).

        The ONE error that does not void a result already in hand is AIRE's
        ``budget_exhausted`` (aire #23): the engine emits it AFTER the result
        event, as a footnote saying the client hit its own ceiling and was
        retired. Raising over it throws away a full answer. The answer is kept
        (it may be cut short, which still beats silence); an EMPTY one stays an
        error so the caller's resend — AIRE's own prescription — can continue
        the work."""
        result: TurnResult | None = None
        try:
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
        except AIREDoorError as exc:
            if exc.code != "budget_exhausted" or result is None or not result.text:
                raise
            _logger.warning(
                "AIRE cut the client at its budget ceiling after the result "
                "(session=%s, text_len=%d); the answer is delivered and the "
                "retired client rebuilds next turn.",
                session_id,
                len(result.text),
            )
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
