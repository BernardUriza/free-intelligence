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

import logging
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any

from . import capabilities as _capabilities
from .backend import AgentBackend, BackendError, MCPServerSpec, ToolPolicy, TurnResult
from .guards import Guard, GuardOutcome
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
    # Optional per-turn model selection (e.g. tier routing). None = use `model`.
    # A sticky router caches per session internally; the runner stays dumb.
    model_router: ModelRouter | None = None

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

        for attempt in range(attempts):
            is_last = attempt == attempts - 1
            system_prompt = f"{self.persona}\n\n{reinforcement}".strip() if reinforcement else self.persona
            try:
                result = await self.backend.run_turn(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    mcp_servers=mcp_servers,
                    tool_policy=self.tool_policy,
                    model=model,
                    session_id=session_id,
                )
            except BackendError:
                raise  # already typed — don't double-wrap
            except Exception as exc:  # noqa: BLE001 - boundary: any backend failure
                self._emit(
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
                result.text, user_message, final=is_last, request_id=request_id
            )
            result = replace(result, text=text, guard_outcomes=outcomes)
            if is_last or not wants_retry:
                break
            # A guard asked to retry and attempts remain: reinforce + (maybe) escalate model.
            reinforcement = f"{reinforcement}\n\n{added}".strip()
            model = self.retry_policy.fallback_model or model

        assert result is not None  # the loop runs at least once
        result = await self._apply_post_processors(result, context, request_id=request_id)
        self._emit(
            "turn_completed",
            {
                "request_id": request_id,
                "model": model,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "tokens": result.usage,
                "mcp_count": len(mcp_servers),
                "attempts": attempt + 1,
                "guard_levels": {n: _guard_level(o.metadata) for n, o in result.guard_outcomes.items()},
            },
        )
        return result

    def _run_guards(
        self, text: str, user_message: str, *, final: bool, request_id: str | None = None
    ) -> tuple[str, dict[str, GuardOutcome], bool, str]:
        """Run each guard over the turn text once. Returns the (possibly
        sanitized) text, the per-guard outcomes, whether any guard wants a retry,
        and the combined reinforcement to append. ``text_override`` is applied
        sequentially so a later guard sees the cleaned text. Emits
        ``guard_critical`` when a guard flags a CRITICAL outcome."""
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
                self._emit("guard_error", {"guard": name, "error": str(exc)})
                outcomes[name] = GuardOutcome(metadata={"guard_failed": True, "error": str(exc)})
                continue
            outcomes[name] = outcome
            if outcome.metadata.get("critical") is True or outcome.metadata.get("level") == "CRITICAL":
                # A guaranteed safety signal (e.g. triage escalating a suicide
                # plan) must SURFACE as telemetry so a consumer can alert/escalate,
                # even for an observational guard that never edits the text.
                self._emit(
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
        self, result: TurnResult, context: dict[str, Any] | None, *, request_id: str | None = None
    ) -> TurnResult:
        """Run post-processors ONCE on the settled text, with per-stage invariants.
        No-op when none are declared."""
        if not self.post_processors:
            return result
        mutated = await run_pipeline(
            self.post_processors, result.text, context or {}, request_id=request_id, on_event=self.on_event
        )
        return replace(result, text=mutated)

    async def aclose(self) -> None:
        """Release backend resources (pooled sessions, etc.), if any."""
        close = getattr(self.backend, "aclose", None)
        if close is not None:
            await close()
