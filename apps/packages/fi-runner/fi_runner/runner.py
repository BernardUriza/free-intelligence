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
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field, replace
from typing import Any

from . import capabilities as _capabilities
from .backend import AgentBackend, BackendError, MCPServerSpec, ToolPolicy, TurnResult
from .conversation import ConversationStore, Message, render_transcript
from .flow import Event, events_to_mermaid
from .guards import Guard, GuardOutcome
from .narrate import narrate_flow
from .pipeline import EventSink, MutationStage, run_pipeline
from .router import ModelRouter

_log = logging.getLogger("fi_runner.runner")


def _guard_level(metadata: dict[str, Any]) -> str:
    """A single representative level for a guard outcome, for telemetry."""
    if metadata.get("guard_failed"):
        return "error"
    return metadata.get("level") or metadata.get("severity") or "ok"


@dataclass(frozen=True)
class RetryPolicy:
    """How the runner retries a turn when a guard requests it.

    The guard decides WHETHER a turn is retry-worthy (``GuardOutcome.retry``);
    this policy decides HOW MANY times and on WHICH model. ``max_attempts=1``
    (the default) disables retry entirely — backward-compatible.
    """

    # Total turn attempts (1 = no retry). The final attempt runs guards with
    # ``final=True`` so transformational guards clean up instead of retrying.
    max_attempts: int = 1
    # Model to switch to on retry (e.g. a stronger tier). None = keep the model.
    fallback_model: str | None = None


@dataclass(frozen=True)
class FlowNarrator:
    """How the runner narrates each turn's flow diagram (the INSIDE view).

    After a turn settles, the runner hands the mechanical diagram + the turn's
    request/response back to its OWN backend and asks it to refine the Mermaid
    into a dev-facing narrative: what its cognitive process reasoned about, with
    new notes/edges/blocks and colors. This is a SECOND backend call, so it runs
    in the BACKGROUND (never delays the turn) and supersedes the mechanical
    diagram when it lands. A refinement is rejected (mechanical kept) if it isn't
    a Mermaid flowchart or drops the ``request_id`` anchor.

    Observability is core to Free Intelligence, so a Runner narrates by DEFAULT.
    Pass ``flow_narrator=None`` to disable it (e.g. a metered backend where a
    second call per turn isn't wanted). Pending narrations are drained by
    :meth:`Runner.aclose` — or use the runner as an async context manager.
    """

    # Override the turn's model for the narration call (e.g. a cheaper tier).
    model: str | None = None
    # Extra guidance appended to the narration system prompt.
    instructions: str | None = None


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

    async def run(
        self,
        user_message: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> TurnResult:
        """Run the turn pipeline: backend → guards → retry → post-processors.

        Pass ``session_id`` (e.g. a Discord channel id) for conversation
        continuity on backends that support stateful sessions. Retries re-run the
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

        # Container-safe continuity by history replay: fold the stored transcript
        # into the prompt sent to the backend, and keep the backend stateless
        # (session_id addresses the STORE, not a backend-native session). Guards
        # still see the ORIGINAL user_message, not the folded transcript.
        backend_message = user_message
        backend_session_id = session_id
        if self.conversation_store is not None and session_id is not None:
            history = await self.conversation_store.load(session_id)
            backend_message = render_transcript(history, user_message)
            backend_session_id = None  # replay IS the continuity; don't also resume
            if history:
                emit(
                    "history_replayed",
                    {"request_id": request_id, "session_id": session_id, "messages": len(history)},
                )

        try:
            for attempt in range(attempts):
                is_last = attempt == attempts - 1
                system_prompt = f"{self.persona}\n\n{reinforcement}".strip() if reinforcement else self.persona
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

                text, outcomes, wants_retry, added = self._run_guards(
                    result.text, user_message, final=is_last, request_id=request_id, emit=emit
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
            if self.conversation_store is not None and session_id is not None:
                await self.conversation_store.append(
                    session_id,
                    [Message(role="user", content=user_message), Message(role="assistant", content=result.text)],
                )
            # Success → narrate this turn in the BACKGROUND (the INSIDE view).
            # Snapshot the path events so the task is independent of this frame.
            if self.flow_narrator is not None:
                self._schedule_narration(request_id, list(turn_events), user_message, result.text, model)
            return result
        finally:
            # Render the turn's flow even if it crashed — a failed turn's diagram
            # (error node, no completion) is as useful as a clean one. Guarded so a
            # raising renderer/callback can never mask the turn's own outcome.
            self._deliver_turn_flow(request_id, turn_events)

    async def run_stream(
        self,
        user_message: str,
        *,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
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

        # Container-safe continuity (same as run): fold the transcript into the
        # backend message; guards still see the ORIGINAL user_message.
        backend_message = user_message
        backend_session_id = session_id
        if self.conversation_store is not None and session_id is not None:
            history = await self.conversation_store.load(session_id)
            backend_message = render_transcript(history, user_message)
            backend_session_id = None
            if history:
                self._emit("history_replayed", {"request_id": request_id, "session_id": session_id, "messages": len(history)})

        result: TurnResult | None = None
        try:
            if hasattr(self.backend, "run_turn_stream"):
                async for event in self.backend.run_turn_stream(
                    system_prompt=self.persona, user_message=backend_message, mcp_servers=mcp_servers,
                    tool_policy=self.tool_policy, model=model, session_id=backend_session_id,
                ):
                    if event.get("type") == "result":
                        result = event["result"]
                    else:
                        yield event  # tool_call / text — live, before the turn ends
            else:
                # Backend can't stream → one-shot, surfaced as a single result event.
                result = await self.backend.run_turn(
                    system_prompt=self.persona, user_message=backend_message, mcp_servers=mcp_servers,
                    tool_policy=self.tool_policy, model=model, session_id=backend_session_id,
                )
        except BackendError:
            raise
        except Exception as exc:  # noqa: BLE001 - boundary: any backend failure
            self._emit("backend_error", {"backend": type(self.backend).__name__, "model": model, "attempt": 1, "error": str(exc)})
            raise BackendError(f"{type(self.backend).__name__} failed (stream): {exc}") from exc

        assert result is not None  # the backend always emits a result
        if self.guards:
            text, outcomes, _retry, _added = self._run_guards(
                result.text, user_message, final=True, request_id=request_id, emit=self._emit
            )
            result = replace(result, text=text, guard_outcomes=outcomes)
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
        if self.conversation_store is not None and session_id is not None:
            await self.conversation_store.append(
                session_id,
                [Message(role="user", content=user_message), Message(role="assistant", content=result.text)],
            )
        yield {"type": "result", "result": result}

    def _deliver_turn_flow(self, request_id: str, events: list[Event]) -> None:
        """Publish this turn's MECHANICAL flow diagram: always as a ``turn_flow``
        telemetry event (observability is never opt-in) and — when set — to
        ``on_turn_flow``. Defensive: a render/callback error is reported as
        ``turn_flow_error`` and swallowed — a diagram is never a turn's SPOF."""
        try:
            mermaid = events_to_mermaid(events, title=f"fi_runner turn · {request_id}")
        except Exception as exc:  # noqa: BLE001 - a diagram is never a turn's SPOF
            self._emit("turn_flow_error", {"request_id": request_id, "error": str(exc)})
            return
        self._emit("turn_flow", {"request_id": request_id, "narrated": False, "mermaid": mermaid})
        self._call_turn_flow(request_id, mermaid)

    def _call_turn_flow(self, request_id: str, mermaid: str) -> None:
        """Hand a diagram to the optional ``on_turn_flow`` callback, guarded so a
        raising consumer can never break (or mask) the turn."""
        if self.on_turn_flow is None:
            return
        try:
            self.on_turn_flow(request_id, mermaid)
        except Exception as exc:  # noqa: BLE001 - a diagram is never a turn's SPOF
            self._emit("turn_flow_error", {"request_id": request_id, "error": str(exc)})

    def _schedule_narration(
        self, request_id: str, events: list[Event], user_message: str, response_text: str, model: str | None
    ) -> None:
        """Fire the turn's narration in the background and track the task so
        ``aclose()`` can drain it — a narration is never silently lost."""
        task = asyncio.create_task(self._narrate(request_id, events, user_message, response_text, model))
        self._narration_tasks.add(task)
        task.add_done_callback(self._narration_tasks.discard)

    async def _narrate(
        self, request_id: str, events: list[Event], user_message: str, response_text: str, model: str | None
    ) -> None:
        """Ask the backend to refine this turn's flow into a dev-facing narrative,
        then publish it (a ``turn_flow`` event with ``narrated=True`` + the
        ``on_turn_flow`` callback), superseding the mechanical diagram. Best
        effort: any failure emits ``flow_narration_error`` and keeps the already
        published mechanical diagram."""
        narrator = self.flow_narrator
        if narrator is None:
            return
        mechanical = events_to_mermaid(events, title=f"fi_runner turn · {request_id}")
        try:
            refined = await narrate_flow(
                self.backend,
                mechanical,
                user_message=user_message,
                response_text=response_text,
                model=narrator.model or model,
                instructions=narrator.instructions,
                request_id=request_id,
            )
        except Exception as exc:  # noqa: BLE001 - narration is best-effort observability
            self._emit("flow_narration_error", {"request_id": request_id, "error": str(exc)})
            return
        self._emit("turn_flow", {"request_id": request_id, "narrated": True, "mermaid": refined})
        self._call_turn_flow(request_id, refined)

    def _run_guards(
        self,
        text: str,
        user_message: str,
        *,
        final: bool,
        request_id: str | None = None,
        emit: EventSink,
    ) -> tuple[str, dict[str, GuardOutcome], bool, str]:
        """Run each guard over the turn text once. Returns the (possibly
        sanitized) text, the per-guard outcomes, whether any guard wants a retry,
        and the combined reinforcement to append. ``text_override`` is applied
        sequentially so a later guard sees the cleaned text. Emits
        ``guard_critical`` when a guard flags a CRITICAL outcome via ``emit``
        (the per-turn sink, so guard events also reach the turn-flow buffer)."""
        outcomes: dict[str, GuardOutcome] = {}
        reinforcement_parts: list[str] = []
        wants_retry = False
        for guard in self.guards:
            # `or repr(guard)` is lazy — repr (expensive for guards holding
            # compiled-pattern lists) only runs if a guard has no `.name`.
            name = getattr(guard, "name", None) or repr(guard)
            try:
                outcome = guard.inspect(response_text=text, context=(user_message,), final=final)
            except Exception as exc:  # noqa: BLE001 - a guard is a safety NET, not a
                # single point of failure: if it raises (e.g. a malformed regex),
                # log + skip it and keep the backend's valid text rather than
                # crashing the whole turn.
                emit("guard_error", {"guard": name, "error": str(exc)})
                outcomes[name] = GuardOutcome(metadata={"guard_failed": True, "error": str(exc)})
                continue
            outcomes[name] = outcome
            if outcome.metadata.get("critical") is True or outcome.metadata.get("level") == "CRITICAL":
                # A guaranteed safety signal (e.g. triage escalating a suicide
                # plan) must SURFACE as telemetry so a consumer can alert/escalate,
                # even for an observational guard that never edits the text.
                emit(
                    "guard_critical",
                    {
                        "guard": name,
                        "request_id": request_id,
                        "level": outcome.metadata.get("level"),
                        "gravity": outcome.metadata.get("gravity"),
                        "reasons": outcome.metadata.get("reasons"),
                    },
                )
            if outcome.text_override is not None:
                text = outcome.text_override
            if outcome.retry:
                wants_retry = True
                if outcome.reinforcement:
                    reinforcement_parts.append(outcome.reinforcement)
        return text, outcomes, wants_retry, "\n\n".join(reinforcement_parts)

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

    async def aclose(self) -> None:
        """Drain pending background narrations (so none is lost) and release
        backend resources (pooled sessions, etc.), if any. Idempotent."""
        if self._narration_tasks:
            await asyncio.gather(*tuple(self._narration_tasks), return_exceptions=True)
        close = getattr(self.backend, "aclose", None)
        if close is not None:
            await close()

    async def __aenter__(self) -> Runner:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
