"""Runner — composes a backend + persona + fi-core capabilities + guards.

The runner is backend-agnostic: it resolves its declared capabilities to MCP
server specs and hands them, the persona (system prompt) and the tool policy to
whatever :class:`~fi_runner.backend.AgentBackend` it was given. Swap the backend
(Claude Code ↔ Codex ↔ raw API) without touching the runner.

It is also the TURN PIPELINE: each turn runs the backend, then the in-process
``guards`` (deterministic safety nets). When a guard requests a retry (e.g. a
persona break) and the :class:`RetryPolicy` allows it, the runner re-runs the
turn with the guard's reinforcement appended to the system prompt — optionally
on a fallback model. On the final allowed attempt guards are told ``final=True``
so a transformational guard sanitizes instead of asking to retry again. This is
how the retry/anti-drift loop that used to live in a consumer (insult's client)
moves UP into the runner: the runner orchestrates, the runner stays dumb about
WHAT each guard does.

Internals are split into sibling modules; this file is the orchestrator:

  - :mod:`._plan_events`    — plan-first stream events from task_tracker calls
  - :mod:`._runner_config`  — :class:`RetryPolicy`, :class:`FlowNarrator`
  - :mod:`._flow_delivery`  — Mermaid diagram render + background narration
  - :mod:`._guards_executor` — guard list execution + CRITICAL escalation
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
from .backend import AgentBackend, BackendError, MCPServerSpec, ToolPolicy, TurnResult
from .conversation import ConversationStore, Message, render_transcript, sanitize_history
from .flow import Event
from .guards import Guard
from .pipeline import EventSink, MutationStage, run_pipeline
from .plan_guard import PlanGuard
from .router import ModelRouter

# Extracted internals — kept private (leading underscore) to signal they
# are implementation detail; consumers should import from ``fi_runner``
# directly, not these submodules.
from ._flow_delivery import deliver_turn_flow, schedule_narration
from ._guards_executor import guard_level as _guard_level, run_guards
from ._plan_events import _derive_plan_events, _PlanStreamObserver
from ._runner_config import FlowNarrator, RetryPolicy

_log = logging.getLogger("fi_runner.runner")


__all__ = [
    "Runner",
    "RetryPolicy",
    "FlowNarrator",
    # Re-exports kept for backward compatibility — tests and the package
    # __init__.py import these from ``fi_runner.runner`` directly.
    "_derive_plan_events",
    "_PlanStreamObserver",
]


@dataclass
class Runner:
    """A configured runner: a backend + a persona + fi-core capabilities + guards."""

    backend: AgentBackend
    persona: str  # the system prompt
    capabilities: list[str] = field(default_factory=list)  # fi-core, e.g. ["cognitive", "persona"]
    # Runner-specific MCP servers not in fi-core (e.g. insult's insult_db, playwright).
    extra_mcp_servers: list[MCPServerSpec] = field(default_factory=list)
    tool_policy: ToolPolicy = field(default_factory=ToolPolicy)
    model: str | None = None
    # Deterministic safety nets run in-process AFTER the turn — guaranteed, unlike
    # capabilities (optional MCP tools). This is how a runner gets fi-core grounding
    # (triage, anti-drift) without importing fi-core itself. See fi_runner.guards.
    guards: list[Guard] = field(default_factory=list)
    # Plan-first anti-drift: inspects the declared task_tracker plan BEFORE any
    # other tool runs. Soft-rejects (emits ``plan_rejected`` event); the consumer
    # decides whether to abort the turn or retry with the guard's reinforcement.
    # See :mod:`fi_runner.plan_guard`. None = no pre-execution plan review.
    plan_guard: PlanGuard | None = None
    # Retry behavior when a guard requests it (default: no retry).
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    # Cosmetic/normalizing text mutations run AFTER guards+retry settle, once, each
    # with invariants (max_shrink_pct, must_preserve). See fi_runner.pipeline.
    post_processors: list[MutationStage] = field(default_factory=list)
    # Telemetry sink for the post-processor pipeline (default: stdlib logging).
    on_event: EventSink | None = None
    # EVERY turn self-documents: the runner always collects the turn's telemetry
    # and, once it settles (or crashes), renders a Mermaid flowchart of the path
    # it took — MCP wiring, guards + levels (CRITICAL highlighted), retries,
    # post-processors, latency/cost — emitted as a ``turn_flow`` event (always, so
    # observability is never opt-in). This OPTIONAL callback is an EXTRA channel
    # for the raw diagram string ``(request_id, mermaid)`` when you also want to
    # write a file / push to a dashboard. The runner stays dumb about WHERE it
    # goes. A raising callback never breaks the turn. It may be called twice per
    # turn — first the mechanical diagram, then the narrated one (latest wins).
    on_turn_flow: Callable[[str, str], None] | None = None
    # The INSIDE view: after each turn, the runner's own backend refines the flow
    # diagram into a dev-facing narrative (see :class:`FlowNarrator`). On by
    # DEFAULT (observability is core to Free Intelligence); set ``None`` to skip
    # the second backend call. Runs in the background; drained by ``aclose()``.
    flow_narrator: FlowNarrator | None = field(default_factory=FlowNarrator)
    # Internal: in-flight background narration tasks, awaited by ``aclose()`` /
    # the async context manager so a narration is never silently lost.
    _narration_tasks: set[asyncio.Task[None]] = field(default_factory=set, init=False, repr=False)
    # Optional per-turn model selection (e.g. tier routing). None = use `model`.
    # A sticky router caches per session internally; the runner stays dumb.
    model_router: ModelRouter | None = None
    # Container-safe conversation continuity by HISTORY REPLAY: when set AND a
    # session_id is given, the runner loads the transcript from this store, folds
    # it into the turn's prompt, and appends the new exchange after. The backend
    # stays stateless (the runner does NOT pass session_id to it — replay is the
    # continuity), so the conversation survives a recycled container as long as the
    # store is durable. Mutually exclusive with a backend's native session. See
    # fi_runner.conversation. None = no replay.
    conversation_store: ConversationStore | None = None
    # Write-ahead variant of the conversation_store append. When ``True`` AND
    # ``conversation_store`` is set, the runner persists the exchange BEFORE
    # the post-processor pipeline runs (and before any ``turn_completed`` event
    # is emitted). The stored ``assistant`` text is therefore the post-guards
    # but pre-cosmetic-mutation version — losing post-processor normalization
    # in exchange for a durable record that survives a post-yield crash. Off
    # by default; turn on only when transactional durability matters more than
    # storing the fully-mutated text. See R14 in the fi-runner robustness
    # roadmap memory.
    pre_emit_append: bool = False
    # Client-supplied conversation history (the og118 canary). A turn may carry its
    # OWN transcript via ``run(history=...)`` instead of relying on a server-side
    # store — the client owns its history (e.g. IndexedDB) and replays it, so
    # continuity survives a recycled container with NO durable store. The history is
    # UNTRUSTED input: it is folded as conversational CONTEXT, never authorization
    # (it never grants permissions, selects a corpus, runs a tool, or proves
    # identity). These two caps bound what a (possibly tampered) client can replay
    # per turn — message count and total chars — keeping per-turn token cost finite.
    # Sanitization (role allowlist, drop tool payloads, truncate oldest) is in
    # fi_runner.conversation.sanitize_history.
    client_history_max_messages: int = 20
    client_history_max_chars: int = 16_000
    # Opt-in per-turn CONTEXT BINDING (proj-corpusbind canary). Given the turn's
    # ``context`` dict, returns an optional system-prompt addendum folded in
    # alongside the persona. This is how a consumer binds structured per-turn
    # state — the active corpus_id, a tenant — into the agent's instructions
    # WITHOUT stuffing it into the user message (which would pollute the replayed
    # transcript and be untyped). Default None → no addendum, byte-identical to
    # before. See fi_runner.context_binding.active_corpus_binding.
    context_prompt: Callable[[Mapping[str, Any]], str | None] | None = None

    def __post_init__(self) -> None:
        # Fail fast on a misconfigured runner instead of shipping an empty system
        # prompt to the model (which silently degrades the output).
        if not self.persona or not self.persona.strip():
            raise ValueError("Runner.persona must be a non-empty system prompt")

    def _emit(self, event: str, fields: dict[str, Any]) -> None:
        """Emit a telemetry event through the configured sink (or stdlib log)."""
        if self.on_event is not None:
            self.on_event(event, fields)
        else:
            _log.info("%s %s", event, fields)

    async def _fold_history(
        self,
        user_message: str,
        session_id: str | None,
        history: Iterable[Any] | None,
        emit: Callable[[str, dict[str, Any]], None],
        request_id: str,
    ) -> tuple[str, str | None]:
        """Resolve the message + session the backend should receive, folding prior
        turns in for continuity. Two sources, client wins (divergence rule):

        - ``history`` given (client-supplied) → sanitize it (untrusted) and fold;
        - else a ``conversation_store`` + ``session_id`` → load and fold;
        - else → the raw message, with the backend-native ``session_id`` preserved.

        When history folds, the backend stays stateless (``session_id`` → None):
        replay IS the continuity, so we never also resume a native session. Guards
        still see the ORIGINAL ``user_message`` — only the BACKEND gets the fold."""
        folded: list[Message] | None = None
        source: str | None = None
        if history is not None:
            folded = sanitize_history(
                history,
                max_messages=self.client_history_max_messages,
                max_chars=self.client_history_max_chars,
            )
            # The frontend's optimistic append may include the CURRENT message as the
            # last history item — drop it so render_transcript doesn't echo it twice.
            if folded and folded[-1].role == "user" and folded[-1].content.strip() == user_message.strip():
                folded = folded[:-1]
            source = "client"
        elif self.conversation_store is not None and session_id is not None:
            folded = await self.conversation_store.load(session_id)
            source = "store"
        if folded is None:
            return user_message, session_id  # no continuity → backend-native session
        if folded:
            emit(
                "history_replayed",
                {"request_id": request_id, "session_id": session_id, "messages": len(folded), "source": source},
            )
        return render_transcript(folded, user_message), None

    def _render_context_prompt(
        self,
        context: dict[str, Any] | None,
        emit: Callable[[str, dict[str, Any]], None],
        request_id: str,
    ) -> str:
        """Render the per-turn context binding into a system-prompt addendum.

        Returns "" when no binding is configured or it yields nothing. A raising
        binding never breaks the turn — it is surfaced as ``context_prompt_error``
        and treated as no addendum (the agent then sees no corpus binding, which
        the consumer's monitoring must catch)."""
        if self.context_prompt is None:
            return ""
        try:
            rendered = self.context_prompt(context or {})
        except Exception as exc:  # noqa: BLE001 - a hostile/buggy binding must not kill the turn
            emit("context_prompt_error", {"request_id": request_id, "error": str(exc)})
            return ""
        if rendered and rendered.strip():
            addendum = rendered.strip()
            emit("context_bound", {"request_id": request_id, "chars": len(addendum)})
            return addendum
        return ""

    def _compose_system_prompt(self, context_addendum: str, reinforcement: str) -> str:
        """persona [+ context addendum] [+ guard reinforcement], joined by blank lines."""
        parts = [self.persona]
        if context_addendum:
            parts.append(context_addendum)
        if reinforcement:
            parts.append(reinforcement)
        return "\n\n".join(parts).strip()

    async def run(
        self,
        user_message: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
        history: Iterable[Any] | None = None,
    ) -> TurnResult:
        """Run the turn pipeline: backend → guards → retry → post-processors.

        Pass ``session_id`` (e.g. a Discord channel id) for conversation
        continuity on backends that support stateful sessions. Pass ``history`` (a
        client-supplied transcript of prior ``user``/``assistant`` turns) to fold
        continuity in WITHOUT a server-side store — it is sanitized as untrusted
        context and wins over the ``conversation_store`` when both are present.
        Retries re-run the
        turn with accumulated reinforcement appended to the persona; the final
        attempt lets transformational guards sanitize instead of retrying.
        ``context`` is forwarded to each post-processor stage (per-turn side data).
        ``request_id`` correlates every event from this turn (a fresh short id is
        generated when omitted): a ``turn_completed`` event (latency, tokens,
        model, mcp_count, guard levels) is emitted at the end, and
        ``guard_critical`` whenever a guard flags a CRITICAL outcome.

        Raises ``ValueError`` on empty ``user_message`` and :class:`BackendError`
        if the backend fails (the original exception is chained as ``__cause__``).
        """
        if not user_message or not user_message.strip():
            raise ValueError("user_message must be non-empty")
        request_id = request_id or uuid.uuid4().hex[:12]

        # EVERY turn self-documents — observability is not opt-in. Mirror this
        # turn's events into a local buffer (local → safe under concurrent runs)
        # so we can render its path (and narrate it) once it settles.
        turn_events: list[Event] = []

        def emit(event: str, fields: dict[str, Any]) -> None:
            turn_events.append((event, fields))
            self._emit(event, fields)

        t0 = time.perf_counter()
        mcp_servers = _capabilities.resolve(self.capabilities) + list(self.extra_mcp_servers)
        attempts = max(1, self.retry_policy.max_attempts)
        reinforcement = ""
        model = self.model
        if self.model_router is not None:
            chosen = await self.model_router.choose(
                user_message=user_message, default=self.model, context=context or {}
            )
            if chosen:
                model = chosen
        result: TurnResult | None = None
        attempt = 0

        # Container-safe continuity by history replay: fold the transcript (client-
        # supplied or from the store) into the prompt sent to the backend, keeping
        # the backend stateless. Guards still see the ORIGINAL user_message.
        backend_message, backend_session_id = await self._fold_history(
            user_message, session_id, history, emit, request_id
        )

        # Per-turn context binding (e.g. the active corpus): rendered once, constant
        # across retries; the guard reinforcement is what varies per attempt.
        context_addendum = self._render_context_prompt(context, emit, request_id)

        try:
            for attempt in range(attempts):
                is_last = attempt == attempts - 1
                system_prompt = self._compose_system_prompt(context_addendum, reinforcement)
                try:
                    result = await self.backend.run_turn(
                        system_prompt=system_prompt,
                        user_message=backend_message,
                        mcp_servers=mcp_servers,
                        tool_policy=self.tool_policy,
                        model=model,
                        session_id=backend_session_id,
                    )
                except BackendError:
                    raise  # already typed — don't double-wrap
                except Exception as exc:  # noqa: BLE001 - boundary: any backend failure
                    emit(
                        "backend_error",
                        {
                            "backend": type(self.backend).__name__,
                            "model": model,
                            "attempt": attempt + 1,
                            "error": str(exc),
                        },
                    )
                    raise BackendError(
                        f"{type(self.backend).__name__} failed on attempt "
                        f"{attempt + 1}/{attempts}: {exc}"
                    ) from exc
                if not self.guards:
                    break

                text, outcomes, wants_retry, added = run_guards(
                    self.guards, result.text, user_message,
                    final=is_last, request_id=request_id, emit=emit,
                )
                result = replace(result, text=text, guard_outcomes=outcomes)
                if is_last or not wants_retry:
                    break
                # A guard asked to retry and attempts remain: reinforce + (maybe) escalate model.
                reinforcement = f"{reinforcement}\n\n{added}".strip()
                model = self.retry_policy.fallback_model or model

            assert result is not None  # the loop runs at least once
            # Tool-trace → telemetry. PHI-safe: only name/server/status reach the
            # event stream (and the diagram), never the tool input/args.
            for i, call in enumerate(result.tool_calls):
                emit(
                    "tool_called",
                    {
                        "request_id": request_id,
                        "index": i,
                        "name": call.name,
                        "server": call.server,
                        "is_error": call.is_error,
                    },
                )
            # R14: optional write-ahead append BEFORE post-processors. Stores the
            # post-guards but pre-mutation text — useful when the consumer needs
            # the durable record to predate any cosmetic transform.
            if self.pre_emit_append:
                await self._append_to_store(
                    session_id, user_message, result.text,
                    request_id=request_id, phase="run_pre_emit", emit=emit,
                )
            result = await self._apply_post_processors(result, context, request_id=request_id, emit=emit)
            emit(
                "turn_completed",
                {
                    "request_id": request_id,
                    "model": model,
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                    "tokens": result.usage,
                    "mcp_count": len(mcp_servers),
                    "tool_count": len(result.tool_calls),
                    "attempts": attempt + 1,
                    "guard_levels": {n: _guard_level(o.metadata) for n, o in result.guard_outcomes.items()},
                },
            )
            # Success → persist the exchange for replay (the ORIGINAL user_message,
            # not the folded transcript). Only on success: a crash stores no half
            # turn. Reached only when conversation_store + session_id are set.
            # Failure is SURFACED as ``conversation_store_error`` but does NOT
            # raise — the user already saw a valid response; we don't roll back
            # the turn just because persistence flaked. The next turn will lose
            # this exchange from history (silent context loss), so monitoring on
            # this event is required for production durability.
            if not self.pre_emit_append:
                await self._append_to_store(
                    session_id, user_message, result.text,
                    request_id=request_id, phase="run", emit=emit,
                )
            # Success → narrate this turn in the BACKGROUND (the INSIDE view).
            # Snapshot the path events so the task is independent of this frame.
            if self.flow_narrator is not None:
                schedule_narration(
                    request_id, list(turn_events), user_message, result.text, model,
                    narrator=self.flow_narrator, backend=self.backend,
                    emit=self._emit, on_turn_flow=self.on_turn_flow,
                    task_pool=self._narration_tasks,
                )
            return result
        finally:
            # Render the turn's flow even if it crashed — a failed turn's diagram
            # (error node, no completion) is as useful as a clean one. Guarded so a
            # raising renderer/callback can never mask the turn's own outcome.
            deliver_turn_flow(request_id, turn_events, emit=self._emit, on_turn_flow=self.on_turn_flow)

    async def run_stream(
        self,
        user_message: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
        history: Iterable[Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Live-streaming turn: yields backend events AS THEY HAPPEN —
        ``{"type":"tool_call","tool":ToolCall}`` per tool call,
        ``{"type":"text","text":delta}`` per text delta — then a final
        ``{"type":"result","result":TurnResult}`` once guards + post-processors
        settle. Additive: :meth:`run` is unchanged.

        Single attempt (the text is already streamed, so no retry); guards run with
        ``final=True`` so a transformational guard sanitizes the final result text
        (the live text may differ from the sanitized final — reconcile on result).
        Backends without ``run_turn_stream`` fall back to one result event. Telemetry
        (turn_completed, tool_called, guard_critical) still fires via on_event; the
        flow diagram + narration are run()-only (not produced for streamed turns)."""
        if not user_message or not user_message.strip():
            raise ValueError("user_message must be non-empty")
        request_id = request_id or uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        mcp_servers = _capabilities.resolve(self.capabilities) + list(self.extra_mcp_servers)
        model = self.model
        if self.model_router is not None:
            chosen = await self.model_router.choose(user_message=user_message, default=self.model, context=context or {})
            if chosen:
                model = chosen

        # Per-turn context binding — the same addendum the agent gets in run().
        context_addendum = self._render_context_prompt(context, self._emit, request_id)

        # Container-safe continuity (same as run): fold the transcript (client-
        # supplied or from the store) into the backend message; guards still see
        # the ORIGINAL user_message.
        backend_message, backend_session_id = await self._fold_history(
            user_message, session_id, history, self._emit, request_id
        )

        # Per-turn observer for the plan-first derived events. Tracks the
        # per-plan_id counters (done/failed/cancelled) needed to pick the
        # terminal event when ``finalize_plan`` lands.
        plan_observer = _PlanStreamObserver()

        result: TurnResult | None = None
        try:
            if hasattr(self.backend, "run_turn_stream"):
                async for event in self.backend.run_turn_stream(
                    system_prompt=self._compose_system_prompt(context_addendum, ""), user_message=backend_message, mcp_servers=mcp_servers,
                    tool_policy=self.tool_policy, model=model, session_id=backend_session_id,
                ):
                    if event.get("type") == "result":
                        result = event["result"]
                    else:
                        yield event  # tool_call / text — live, before the turn ends
                        # Plan-first observability: when the agent calls the task_tracker
                        # MCP, re-emit the semantic event (plan / step_started / step_done /
                        # step_noted / plan_amended / plan_completed / plan_failed / plan_cancelled)
                        # so the UI can paint a checklist without parsing tool names itself.
                        # The original tool_call event still goes through above, so the
                        # generic ThinkingPanel keeps working — these are ADDITIVE.
                        if event.get("type") == "tool_call":
                            for derived in _derive_plan_events(
                                event["tool"],
                                session_id=session_id,
                                request_id=request_id,
                                observer=plan_observer,
                            ):
                                yield derived
                                # Plan-first anti-drift: when a fresh ``plan`` event is
                                # emitted, give the optional PlanGuard a chance to veto
                                # before the agent fires any other tool. Rejection is
                                # SOFT — we emit ``plan_rejected`` but do not interrupt
                                # the stream; the consumer's turn loop (or the agent's
                                # own logic, prompted via reinforcement) decides to abort.
                                if derived.get("type") == "plan" and self.plan_guard is not None:
                                    steps = (derived.get("data") or {}).get("steps") or []
                                    outcome = self.plan_guard.inspect(steps)
                                    if not outcome.allowed:
                                        yield {"type": "plan_rejected", "data": {
                                            "request_id": request_id,
                                            "reason": outcome.reason,
                                            "matched": list(outcome.matched),
                                            "reinforcement": outcome.reinforcement,
                                            "guard": self.plan_guard.name,
                                        }}
            else:
                # Backend can't stream → one-shot, surfaced as a single result event.
                result = await self.backend.run_turn(
                    system_prompt=self._compose_system_prompt(context_addendum, ""), user_message=backend_message, mcp_servers=mcp_servers,
                    tool_policy=self.tool_policy, model=model, session_id=backend_session_id,
                )
        except BackendError:
            raise
        except Exception as exc:  # noqa: BLE001 - boundary: any backend failure
            self._emit("backend_error", {"backend": type(self.backend).__name__, "model": model, "attempt": 1, "error": str(exc)})
            raise BackendError(f"{type(self.backend).__name__} failed (stream): {exc}") from exc

        assert result is not None  # the backend always emits a result
        # R10: the post-stream pipeline (guards + tool_call telemetry + post-
        # processors + turn_completed + conversation_store append) is wrapped
        # in a single try/except so a failure here can never crash the async
        # generator before the consumer receives its ``result`` event. The
        # final ``yield`` sits OUTSIDE the guarded block — even a catastrophic
        # post-processor crash still hands back the best-available result.
        try:
            if self.guards:
                text, outcomes, _retry, _added = run_guards(
                    self.guards, result.text, user_message,
                    final=True, request_id=request_id, emit=self._emit,
                )
                result = replace(result, text=text, guard_outcomes=outcomes)
            # R14: optional write-ahead append (same semantic as run()).
            if self.pre_emit_append:
                await self._append_to_store(
                    session_id, user_message, result.text,
                    request_id=request_id, phase="run_stream_pre_emit", emit=self._emit,
                )
            for i, call in enumerate(result.tool_calls):
                self._emit("tool_called", {
                    "request_id": request_id, "index": i, "name": call.name,
                    "server": call.server, "is_error": call.is_error,
                })
            result = await self._apply_post_processors(result, context, request_id=request_id, emit=self._emit)
            self._emit("turn_completed", {
                "request_id": request_id, "model": model,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "tokens": result.usage, "mcp_count": len(mcp_servers),
                "tool_count": len(result.tool_calls), "attempts": 1, "streamed": True,
                "guard_levels": {n: _guard_level(o.metadata) for n, o in result.guard_outcomes.items()},
            })
            if not self.pre_emit_append:
                await self._append_to_store(
                    session_id, user_message, result.text,
                    request_id=request_id, phase="run_stream", emit=self._emit,
                )
        except Exception as exc:  # noqa: BLE001 - R10: never lose the result event
            self._emit("stream_postprocess_error", {
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        yield {"type": "result", "result": result}

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

        No-op when ``conversation_store`` or ``session_id`` is unset. Failures
        are SURFACED as ``conversation_store_error`` but never raised — the
        user already saw a valid response and we don't roll back the turn
        just because persistence flaked. ``phase`` discriminates which call
        site (``run`` / ``run_pre_emit`` / ``run_stream`` / ``run_stream_pre_emit``)
        produced the failure, for monitoring."""
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
        """Run post-processors ONCE on the settled text, with per-stage invariants.
        No-op when none are declared. Pipeline events go through ``emit`` (the
        per-turn sink) so ``mutation_applied`` / ``pipeline_violation`` also land
        in the turn-flow buffer, not just the raw ``on_event``."""
        if not self.post_processors:
            return result
        mutated = await run_pipeline(
            self.post_processors, result.text, context or {}, request_id=request_id, on_event=emit
        )
        return replace(result, text=mutated)

    async def preflight(self, *, timeout: float = 10.0) -> dict[str, Any]:
        """Probe every MCP server this runner will use, BEFORE the first turn.

        Resolves capabilities + ``extra_mcp_servers`` exactly as :meth:`run` does,
        then runs :func:`fi_runner.preflight.probe_mcp` for each in parallel.
        Returns ``{server_name: PreflightResult}`` so the caller can fail boot
        (or just log) when an expected MCP is dead — instead of finding out
        mid-turn as a generic ``is_error`` with no context.

        Cheap: each probe is a short JSON-RPC handshake; safe to call on every
        process start. No-op for runners with zero MCP servers."""
        from .preflight import probe_all  # local import keeps preflight optional

        mcp_servers = _capabilities.resolve(self.capabilities) + list(self.extra_mcp_servers)
        return await probe_all(mcp_servers, timeout=timeout)

    def install_signal_handlers(
        self,
        *,
        signals: tuple[_signal.Signals, ...] = (),
    ) -> None:
        """Register SIGTERM/SIGINT handlers that drain background narrations
        on shutdown — opt-in for k8s/long-running deploys (R11).

        When the registered signal fires, the runner emits
        ``runner_signal_received`` and schedules :meth:`aclose` on the current
        event loop. Must be called from inside a running event loop (handlers
        register via :meth:`asyncio.AbstractEventLoop.add_signal_handler`).

        Unix-only: ``add_signal_handler`` raises ``NotImplementedError`` on
        Windows; we catch and skip per-signal so a partial install still
        runs (e.g. SIGINT works on Win, SIGTERM does not). Idempotent —
        replaces any prior handler for the same signal."""
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
                # Windows: asyncio signal handlers are unix-only. Skip
                # silently; the consumer can wire a SetConsoleCtrlHandler
                # equivalent themselves if needed.
                self._emit("runner_signal_install_skipped", {
                    "signal": int(sig),
                    "reason": "platform_unsupported",
                })

    async def _on_signal(self, sig: _signal.Signals) -> None:
        """Drain narrations + release backend resources when a registered
        signal fires. Surfaces the event before closing so an external
        observer can correlate the shutdown with telemetry."""
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
        """Drain pending background narrations (so none is lost) and release
        backend resources (pooled sessions, etc.), if any. Idempotent.

        ``return_exceptions=True`` is required so one failed narration doesn't
        cancel the others mid-drain. We iterate the results to surface every
        failure as a ``narration_drain_error`` event — otherwise narrations
        that raised would be silently swallowed by gather (a documented
        asyncio footgun)."""
        if self._narration_tasks:
            results = await asyncio.gather(
                *tuple(self._narration_tasks), return_exceptions=True
            )
            for r in results:
                if isinstance(r, BaseException):
                    # BaseException catches CancelledError too — gather's
                    # return_exceptions does NOT auto-detect it via Exception.
                    self._emit("narration_drain_error", {
                        "error_type": type(r).__name__,
                        "error": str(r),
                    })
        close = getattr(self.backend, "aclose", None)
        if close is not None:
            await close()

    async def __aenter__(self) -> Runner:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
