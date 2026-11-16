"""Runner — composes a backend + persona + fi-core capabilities + guards.

The runner is backend-agnostic: it resolves its declared capabilities to MCP
server specs and hands them, the persona (system prompt) and the tool policy to
whatever :class:`~fi_runner.backend.AgentBackend` it was given.

It is also the TURN PIPELINE: each turn runs the backend, then the in-process
``guards``. When a guard requests a retry and the :class:`RetryPolicy` allows
it, the runner re-runs the turn with the guard's reinforcement appended to the
system prompt, optionally on a fallback model. On the final allowed attempt
guards are told ``final=True`` so a transformational guard sanitizes instead of
asking to retry again.

This file is the orchestrator; the work lives in sibling modules:

  - :mod:`._turn_attempt`    — one backend attempt: stream, plan events, plan veto
  - :mod:`._plan_events`     — plan-first stream events from task_tracker calls
  - :mod:`._runner_config`   — :class:`RetryPolicy`, :class:`FlowNarrator`
  - :mod:`._flow_delivery`   — Mermaid diagram render + background narration
  - :mod:`._guards_executor` — guard list execution + CRITICAL escalation
  - :mod:`.conversation`     — continuity: history fold and transcript stores
  - :mod:`.context_binding`  — per-turn prompt addendum and pinned tool arguments
"""

from __future__ import annotations

import asyncio
import logging
import signal as _signal
import time
import uuid
from collections.abc import AsyncIterator, Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from . import capabilities as _capabilities
from ._flow_delivery import deliver_turn_flow, drain_narrations, schedule_narration
from ._guards_executor import guard_level as _guard_level
from ._guards_executor import run_guards
from ._runner_config import FlowNarrator, RetryPolicy
from ._turn_attempt import AttemptOutcome, stream_attempt
from .backend import AgentBackend, BackendError, MCPServerSpec, ToolPolicy, TurnDocument, TurnImage, TurnResult
from .context_binding import render_context_prompt, stamp_pinned_args
from .conversation import ConversationStore, Message, fold_history
from .flow import Event
from .guards import Guard
from .pipeline import EventSink, MutationStage, run_pipeline
from .plan_guard import PlanGuard
from .router import ModelRouter

_log = logging.getLogger("fi_runner.runner")


@dataclass
class _TurnSetup:
    """Everything both turn entrypoints derive before touching the backend."""

    request_id: str
    t0: float
    mcp_servers: list[MCPServerSpec]
    model: str | None
    backend_message: str
    backend_session_id: str | None
    context_addendum: str
    images: list[TurnImage] | None
    documents: list[TurnDocument] | None
    events: list[Event]
    emit: Callable[[str, dict[str, Any]], None]


__all__ = ["Runner", "RetryPolicy", "FlowNarrator"]


@dataclass
class Runner:
    """A configured runner: a backend + a persona + fi-core capabilities + guards.

    Attributes:
        backend: Where the turn runs. Swappable without touching the runner.
        persona: The system prompt. Must be non-empty.
        capabilities: fi-core capability names, resolved to MCP server specs.
        extra_mcp_servers: Runner-specific MCP servers that are not fi-core.
        tool_policy: Which tools the backend may call.
        model: Default model; ``None`` lets the backend choose.
        guards: Deterministic in-process checks run AFTER every attempt. Unlike
            capabilities (optional MCP tools) they are guaranteed to run.
        plan_guard: Reviews a declared task_tracker plan before other tools run.
            A veto emits ``plan_rejected`` and forces a retry when budget allows.
        retry_policy: Attempts and fallback model when a guard asks to retry.
        post_processors: Text mutations run once after guards settle, each with
            its own invariants (see :mod:`fi_runner.pipeline`).
        on_event: Telemetry sink. Default: stdlib logging.
        on_turn_flow: Extra channel ``(request_id, mermaid)`` for the turn's flow
            diagram. May fire twice per turn (mechanical, then narrated). Both
            entrypoints publish the mechanical diagram.
        flow_narrator: Refines the diagram with a SECOND backend call, in the
            background. ``run()``-only on purpose: enabling it for streaming
            would double every streaming consumer's per-turn spend.
        model_router: Optional per-turn model selection; overrides ``model``.
        conversation_store: Continuity by history replay. With a ``session_id``
            the transcript is folded into the prompt and the backend stays
            stateless, so the conversation survives a recycled container.
        pre_emit_append: Persist the exchange BEFORE post-processors run. Stores
            the pre-mutation text in exchange for surviving a post-yield crash.
        client_history_max_messages: Cap on client-supplied ``history`` items.
        client_history_max_chars: Cap on client-supplied ``history`` size.
            History is untrusted context, never authorization.
        context_prompt: ``context -> addendum`` folded into the system prompt.
            Tells the agent what it SHOULD do; it is open to persuasion.
        pin_tool_args: ``context -> {server: {arg: value}}`` stamped on the MCP
            specs. Decides what the agent CAN do; needs a backend that declares
            ``enforces_pinned_args``, else the turn fails loud.
    """

    backend: AgentBackend
    persona: str
    capabilities: list[str] = field(default_factory=list)
    extra_mcp_servers: list[MCPServerSpec] = field(default_factory=list)
    tool_policy: ToolPolicy = field(default_factory=ToolPolicy)
    model: str | None = None
    guards: list[Guard] = field(default_factory=list)
    plan_guard: PlanGuard | None = None
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    post_processors: list[MutationStage] = field(default_factory=list)
    on_event: EventSink | None = None
    on_turn_flow: Callable[[str, str], None] | None = None
    flow_narrator: FlowNarrator | None = field(default_factory=FlowNarrator)
    _narration_tasks: set[asyncio.Task[None]] = field(default_factory=set, init=False, repr=False)
    model_router: ModelRouter | None = None
    conversation_store: ConversationStore | None = None
    pre_emit_append: bool = False
    client_history_max_messages: int = 20
    client_history_max_chars: int = 16_000
    context_prompt: Callable[[Mapping[str, Any]], str | None] | None = None
    pin_tool_args: Callable[[Mapping[str, Any]], Mapping[str, Mapping[str, Any]]] | None = None

    def __post_init__(self) -> None:
        if not self.persona or not self.persona.strip():
            raise ValueError("Runner.persona must be a non-empty system prompt")

    def _emit(self, event: str, fields: dict[str, Any]) -> None:
        """Emit a telemetry event through the configured sink (or stdlib log)."""
        if self.on_event is not None:
            self.on_event(event, fields)
        else:
            _log.info("%s %s", event, fields)

    def _mcp_servers(self) -> list[MCPServerSpec]:
        return _capabilities.resolve(self.capabilities) + list(self.extra_mcp_servers)

    def _compose_system_prompt(self, context_addendum: str, reinforcement: str) -> str:
        """persona [+ context addendum] [+ guard reinforcement], joined by blank lines."""
        parts = [self.persona]
        if context_addendum:
            parts.append(context_addendum)
        if reinforcement:
            parts.append(reinforcement)
        return "\n\n".join(parts).strip()

    async def _prepare_turn(
        self,
        user_message: str,
        session_id: str | None,
        context: dict[str, Any] | None,
        request_id: str | None,
        history: Iterable[Any] | None,
        images: Iterable[Any] | None,
        documents: Iterable[Any] | None,
    ) -> _TurnSetup:
        """The preamble both entrypoints share: validate, mint the request id,
        resolve and pin MCP servers, route the model, fold continuity and render
        the context binding.

        Raises:
            ValueError: empty ``user_message`` on a turn with no images or documents.
        """
        # Local buffer: safe under concurrent turns, and it feeds the flow diagram.
        events: list[Event] = []

        def emit(event: str, fields: dict[str, Any]) -> None:
            events.append((event, fields))
            self._emit(event, fields)

        turn_images = [TurnImage.from_any(i) for i in images] if images else None
        turn_documents = [TurnDocument.from_any(d) for d in documents] if documents else None
        if (not user_message or not user_message.strip()) and not turn_images and not turn_documents:
            raise ValueError("user_message must be non-empty")
        request_id = request_id or uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        if turn_images:
            # Count and media types only, never the bytes.
            emit(
                "images_attached",
                {"request_id": request_id, "count": len(turn_images), "media_types": [i.media_type for i in turn_images]},
            )
        mcp_servers = stamp_pinned_args(
            self.pin_tool_args, self.backend, self._mcp_servers(), context, emit=emit, request_id=request_id
        )
        model = self.model
        if self.model_router is not None:
            chosen = await self.model_router.choose(
                user_message=user_message, default=self.model, context=context or {}
            )
            if chosen:
                model = chosen
        # Only the BACKEND gets the fold; guards still see the original message.
        backend_message, backend_session_id = await fold_history(
            backend=self.backend,
            store=self.conversation_store,
            user_message=user_message,
            session_id=session_id,
            history=history,
            max_messages=self.client_history_max_messages,
            max_chars=self.client_history_max_chars,
            emit=emit,
            request_id=request_id,
        )
        return _TurnSetup(
            request_id=request_id,
            t0=t0,
            mcp_servers=mcp_servers,
            model=model,
            backend_message=backend_message,
            backend_session_id=backend_session_id,
            context_addendum=render_context_prompt(self.context_prompt, context, emit=emit, request_id=request_id),
            images=turn_images,
            documents=turn_documents,
            events=events,
            emit=emit,
        )

    async def _settle_turn(
        self,
        result: TurnResult,
        setup: _TurnSetup,
        *,
        model: str | None,
        attempts: int,
        streamed: bool,
        phase: str,
        session_id: str | None,
        user_message: str,
        context: dict[str, Any] | None,
    ) -> TurnResult:
        """Settle a turn: tool-call telemetry, optional write-ahead append,
        post-processors, ``turn_completed``, then the success append.

        ``model`` is what actually ran (the retry loop may have escalated), and
        it is stamped onto the result so the answer carries its own provenance.
        """
        emit = setup.emit
        result = replace(result, model=model)
        for i, call in enumerate(result.tool_calls):
            # Name, server and status only: never the tool input.
            emit(
                "tool_called",
                {
                    "request_id": setup.request_id,
                    "index": i,
                    "name": call.name,
                    "server": call.server,
                    "is_error": call.is_error,
                },
            )
        if self.pre_emit_append:
            await self._append_to_store(
                session_id, user_message, result.text,
                request_id=setup.request_id, phase=f"{phase}_pre_emit", emit=emit,
            )
        result = await self._apply_post_processors(
            result, context, request_id=setup.request_id, emit=emit
        )
        completed: dict[str, Any] = {
            "request_id": setup.request_id,
            "model": model,
            "latency_ms": round((time.perf_counter() - setup.t0) * 1000, 2),
            "tokens": result.usage,
            "mcp_count": len(setup.mcp_servers),
            "tool_count": len(result.tool_calls),
            "attempts": attempts,
            "guard_levels": {n: _guard_level(o.metadata) for n, o in result.guard_outcomes.items()},
        }
        if streamed:
            completed["streamed"] = True
        emit("turn_completed", completed)
        if not self.pre_emit_append:
            await self._append_to_store(
                session_id, user_message, result.text,
                request_id=setup.request_id, phase=phase, emit=emit,
            )
        return result

    @property
    def _enforces_before_delivery(self) -> bool:
        """Whether anything on this runner must decide BEFORE the user sees the answer.

        A guard cannot enforce what was already delivered, so the streaming path
        withholds TEXT deltas when this is true and flushes the settled text once
        guards have run. Tool-call and plan events are never withheld.
        """
        return bool(self.guards) or self.plan_guard is not None or self.retry_policy.max_attempts > 1

    async def _attempt_stream(
        self,
        setup: _TurnSetup,
        *,
        user_message: str,
        session_id: str | None,
        live_text: bool,
    ) -> AsyncIterator[dict[str, Any]]:
        """THE turn attempt loop, shared by :meth:`run` and :meth:`run_stream`.

        Yields each attempt's events and, last, the private sentinel
        ``{"type": "_settled", "result", "model", "attempts"}``. Sharing it is
        what gives both entrypoints the same retry budget, guard verdict and
        plan-guard veto.

        With ``live_text=False`` text deltas are withheld and the settled text
        is emitted as ONE text event just before the sentinel.

        Raises:
            BackendError: the backend failed, or ended without a result event.
        """
        attempts = max(1, self.retry_policy.max_attempts)
        backend_name = type(self.backend).__name__
        reinforcement = ""
        model = setup.model
        result: TurnResult | None = None
        attempt = 0
        # Attachments ride only when present, so a text turn stays byte-identical
        # and a vision-less backend fails loud instead of ignoring the picture.
        attachments: dict[str, Any] = {}
        if setup.images:
            attachments["images"] = setup.images
        if setup.documents:
            attachments["documents"] = setup.documents

        for attempt in range(attempts):
            is_last = attempt == attempts - 1
            outcome = AttemptOutcome()
            turn = {
                "system_prompt": self._compose_system_prompt(setup.context_addendum, reinforcement),
                "user_message": setup.backend_message,
                "mcp_servers": setup.mcp_servers,
                "tool_policy": self.tool_policy,
                "model": model,
                "session_id": setup.backend_session_id,
                **attachments,
            }
            try:
                async for event in stream_attempt(
                    self.backend, turn, outcome,
                    live_text=live_text, plan_guard=self.plan_guard,
                    session_id=session_id, request_id=setup.request_id,
                ):
                    yield event
            except BackendError:
                raise
            except Exception as exc:  # noqa: BLE001 - boundary: any backend failure
                setup.emit(
                    "backend_error",
                    {"backend": backend_name, "model": model, "attempt": attempt + 1, "error": str(exc)},
                )
                raise BackendError(f"{backend_name} failed on attempt {attempt + 1}/{attempts}: {exc}") from exc

            if outcome.result is None:
                raise BackendError(
                    f"{backend_name} ended the turn without a result event (attempt {attempt + 1}/{attempts})"
                )
            result = outcome.result
            if not self.guards and not outcome.plan_reinforcement:
                break

            text, outcomes, wants_retry, added = run_guards(
                self.guards, result.text, user_message,
                final=is_last, request_id=setup.request_id, emit=setup.emit,
            )
            result = replace(result, text=text, guard_outcomes=outcomes)
            if is_last or not (wants_retry or outcome.plan_reinforcement):
                break
            reinforcement = "\n\n".join(
                p for p in (reinforcement, added, outcome.plan_reinforcement) if p
            ).strip()
            model = self.retry_policy.fallback_model or model

        if result is None:
            raise BackendError(f"{backend_name} produced no result")
        if not live_text:
            # The settled text, not the raw deltas: a guard may have rewritten it.
            yield {"type": "text", "text": result.text}
        yield {"type": "_settled", "result": result, "model": model, "attempts": attempt + 1}

    async def run(
        self,
        user_message: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
        history: Iterable[Any] | None = None,
        images: Iterable[Any] | None = None,
        documents: Iterable[Any] | None = None,
    ) -> TurnResult:
        """Run the turn pipeline: backend → guards → retry → post-processors.

        Args:
            session_id: Conversation continuity key (store replay or native session).
            context: Per-turn side data for bindings, routing and post-processors.
            request_id: Correlates every event of the turn; minted when omitted.
            history: Client-supplied transcript. Sanitized as untrusted context;
                wins over ``conversation_store`` when both are present.
            images: ``TurnImage``s or ``{media_type, data}`` mappings (base64) for
                THIS turn only. An image-only turn is valid.
            documents: ``TurnDocument``s or mappings, current turn only.

        Raises:
            ValueError: empty ``user_message`` with no images or documents.
            BackendError: the backend failed (original exception chained).
        """
        setup = await self._prepare_turn(user_message, session_id, context, request_id, history, images, documents)
        try:
            settled: dict[str, Any] = {}
            async for event in self._attempt_stream(
                setup, user_message=user_message, session_id=session_id, live_text=False
            ):
                if event.get("type") == "_settled":
                    settled = event
            result = await self._settle_turn(
                settled["result"], setup,
                model=settled["model"], attempts=settled["attempts"], streamed=False, phase="run",
                session_id=session_id, user_message=user_message, context=context,
            )
            if self.flow_narrator is not None:
                schedule_narration(
                    setup.request_id, list(setup.events), user_message, result.text, settled["model"],
                    narrator=self.flow_narrator, backend=self.backend,
                    emit=self._emit, on_turn_flow=self.on_turn_flow,
                    task_pool=self._narration_tasks,
                )
            return result
        finally:
            # A crashed turn's diagram is as useful as a clean one.
            deliver_turn_flow(setup.request_id, setup.events, emit=self._emit, on_turn_flow=self.on_turn_flow)

    async def run_stream(
        self,
        user_message: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
        history: Iterable[Any] | None = None,
        images: Iterable[Any] | None = None,
        documents: Iterable[Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Live-streaming turn; same arguments and guarantees as :meth:`run`.

        Yields:
            ``{"type": "tool_call", "tool": ToolCall}`` per tool call, the derived
            plan/step events, ``{"type": "text", "text": delta}``, and last
            ``{"type": "result", "result": TurnResult}``.

            Text streams token by token only when nothing can still change the
            answer (:attr:`_enforces_before_delivery` is false). Otherwise it
            arrives as ONE text event after guards run.

        Raises:
            ValueError: empty ``user_message`` with no images or documents.
            BackendError: the backend failed (original exception chained).
        """
        setup = await self._prepare_turn(user_message, session_id, context, request_id, history, images, documents)
        try:
            settled: dict[str, Any] = {}
            async for event in self._attempt_stream(
                setup, user_message=user_message, session_id=session_id,
                live_text=not self._enforces_before_delivery,
            ):
                if event.get("type") == "_settled":
                    settled = event
                    continue
                yield event

            result: TurnResult = settled["result"]
            # R10: a failure settling must never cost the consumer its result event.
            try:
                result = await self._settle_turn(
                    result, setup,
                    model=settled["model"], attempts=settled["attempts"], streamed=True, phase="run_stream",
                    session_id=session_id, user_message=user_message, context=context,
                )
            except Exception as exc:  # noqa: BLE001 - R10: never lose the result event
                setup.emit("stream_postprocess_error", {
                    "request_id": setup.request_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })
            yield {"type": "result", "result": result}
        finally:
            deliver_turn_flow(setup.request_id, setup.events, emit=self._emit, on_turn_flow=self.on_turn_flow)

    async def _append_to_store(
        self,
        session_id: str | None,
        user_message: str,
        assistant_text: str,
        *,
        request_id: str,
        phase: str,
        emit: EventSink,
    ) -> None:
        """Persist one user/assistant exchange to ``conversation_store``.

        No-op without a store or a ``session_id``. A failure is surfaced as
        ``conversation_store_error`` (``phase`` names the call site) and never
        raised: the user already saw a valid answer. Monitor that event, the
        next turn replays without this exchange.
        """
        if self.conversation_store is None or session_id is None:
            return
        try:
            await self.conversation_store.append(
                session_id,
                [Message(role="user", content=user_message), Message(role="assistant", content=assistant_text)],
            )
        except Exception as exc:  # noqa: BLE001 - boundary: any store failure
            emit("conversation_store_error", {
                "request_id": request_id, "session_id": session_id,
                "phase": phase, "error_type": type(exc).__name__, "error": str(exc),
            })

    async def _apply_post_processors(
        self,
        result: TurnResult,
        context: dict[str, Any] | None,
        *,
        request_id: str | None = None,
        emit: EventSink,
    ) -> TurnResult:
        """Run post-processors once on the settled text; no-op when none are declared."""
        if not self.post_processors:
            return result
        mutated = await run_pipeline(
            self.post_processors, result.text, context or {}, request_id=request_id, on_event=emit
        )
        return replace(result, text=mutated)

    async def forget_session(self, session_id: str) -> bool:
        """Erase a session's native memory, the cascade a consumer's delete owes.

        Returns:
            ``True`` when the backend erased it. ``False`` when the backend has
            no ``forget_session``; that case emits ``forget_session_unsupported``
            because the native transcript then survives the user's delete.
        """
        forget = getattr(self.backend, "forget_session", None)
        if not callable(forget):
            self._emit("forget_session_unsupported", {
                "backend": type(self.backend).__name__,
                "session_id": session_id,
                "consequence": "native transcript survives the user's delete",
            })
            return False
        return bool(await forget(session_id))

    async def preflight(self, *, timeout: float = 10.0) -> dict[str, Any]:
        """Probe every MCP server this runner will use, before the first turn.

        Returns:
            ``{server_name: PreflightResult}``, so the caller can fail boot when
            an expected MCP is dead instead of finding out mid-turn.
        """
        from .preflight import probe_all  # local import keeps preflight optional

        return await probe_all(self._mcp_servers(), timeout=timeout)

    def install_signal_handlers(
        self,
        *,
        signals: tuple[_signal.Signals, ...] = (),
    ) -> None:
        """Register handlers (default SIGTERM, SIGINT) that run :meth:`aclose` on shutdown.

        Must be called inside a running event loop. Idempotent. A signal the
        platform cannot register (Windows) is skipped and reported as
        ``runner_signal_install_skipped``.
        """
        if not signals:
            signals = (_signal.SIGTERM, _signal.SIGINT)
        loop = asyncio.get_running_loop()
        for sig in signals:
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._on_signal(s)),
                )
            except NotImplementedError:
                self._emit("runner_signal_install_skipped", {
                    "signal": int(sig),
                    "reason": "platform_unsupported",
                })

    async def _on_signal(self, sig: _signal.Signals) -> None:
        """Announce the signal, then drain and close."""
        self._emit("runner_signal_received", {"signal": int(sig)})
        try:
            await self.aclose()
        except Exception as exc:  # noqa: BLE001 - shutdown is best-effort
            self._emit("runner_shutdown_error", {
                "signal": int(sig),
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

    async def aclose(self) -> None:
        """Drain pending background narrations and release backend resources. Idempotent."""
        await drain_narrations(self._narration_tasks, emit=self._emit)
        close = getattr(self.backend, "aclose", None)
        if close is not None:
            await close()

    async def __aenter__(self) -> Runner:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
