"""Mutation pipeline — post-turn text stages with per-stage invariants.

A guard is a SAFETY NET (detect/retry/sanitize). A **post-processor** is a
cosmetic/normalizing text mutation that runs AFTER the turn settles: language
normalization, list stripping, formatting. The danger of a blind mutation chain
is that a catch-all matcher silently nukes good content — so every stage declares
its invariants (``max_shrink_pct``, ``must_preserve``) and an ``on_violation``
policy, and the runner REJECTS a mutation that breaks them (logged, not silent).

Origin: extracted from the production Discord bot
(``insult/core/character/pipeline.py``), generalized for reuse. The incident that
motivated the invariants — a dedup stage deleting 51% of a substantive reply to a
vulnerable user, logged but not blocked — is exactly what a shared core should
make impossible for every runner, not just the one that got burned.

Zero-dep: telemetry goes through an optional ``on_event`` sink (default: stdlib
logging) so fi_runner pulls in no structured-logging dependency; a consumer can
pass a sink that forwards to structlog / its own observability.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

_log = logging.getLogger("fi_runner.pipeline")

#: Telemetry sink: ``(event_name, fields) -> None``. Default logs via stdlib;
#: pass your own (e.g. structlog) to integrate with existing observability.
EventSink = Callable[[str, dict[str, Any]], None]


def _default_sink(event: str, fields: dict[str, Any]) -> None:
    _log.info("%s %s", event, fields)


# ---------------------------------------------------------------------------
# Invariant helpers — generic must_preserve callables
# ---------------------------------------------------------------------------
#
# Each returns True when the invariant HOLDS, False when violated. They take
# (before, after) only — never stage ctx — so they compose across stages.
# Runner-specific invariants (e.g. insult's [REACT:] markers) live in the runner.


def preserve_question_marks(before: str, after: str) -> bool:
    """If the original asked a question, the mutation must keep at least one."""
    if "?" in before:
        return "?" in after
    return True


def preserve_min_length(min_chars: int) -> Callable[[str, str], bool]:
    """Floor: don't let a stage take a non-empty response below ``min_chars``."""

    def _check(before: str, after: str) -> bool:
        if len(before) >= min_chars:
            return len(after) >= min_chars
        return True

    _check.__name__ = f"preserve_min_length({min_chars})"
    return _check


# ---------------------------------------------------------------------------
# MutationStage + on_violation policies
# ---------------------------------------------------------------------------

OnViolation = Literal["skip_stage", "abort_pipeline", "raise", "log_only"]
"""Per-stage failure policy.

- ``skip_stage`` (default) — reject the mutation, treat the stage as a no-op,
  fire telemetry, continue. Right for cosmetic stages (dedup, formatting).
- ``abort_pipeline`` — reject AND run no further stage (violation suggests an
  upstream break that further processing would compound).
- ``raise`` — surface a :class:`PipelineViolationError` (tests / dev only).
- ``log_only`` — accept the mutation, just log (shadow-mode rollout).
"""


@dataclass
class MutationStage:
    """One step in the post-turn mutation chain.

    ``apply`` is ``(text, ctx) -> str`` and may be sync OR async (the runner
    awaits if needed). ``ctx`` carries per-turn side data the stage needs
    (recent openers, user profile) without changing the runner.
    """

    name: str
    apply: Callable[[str, dict[str, Any]], str | Awaitable[str]]
    max_shrink_pct: float | None = 0.40
    """Reject the mutation if it shrinks the text by more than this fraction.
    ``None`` disables the length guard (e.g. a stage that legitimately removes
    a reaction-only response)."""
    must_preserve: list[Callable[[str, str], bool]] = field(default_factory=list)
    on_violation: OnViolation = "skip_stage"


class PipelineViolationError(Exception):
    """Raised by :func:`run_pipeline` when a stage's policy is ``"raise"``."""

    def __init__(self, stage: str, failed: list[str], before_len: int, after_len: int) -> None:
        super().__init__(f"stage={stage} violations={failed} {before_len}->{after_len} chars")
        self.stage = stage
        self.failed = failed
        self.before_len = before_len
        self.after_len = after_len


def _shrink_pct(before: str, after: str) -> float:
    if not before:
        return 0.0
    return max(0.0, (len(before) - len(after)) / len(before))


def _check_invariants(stage: MutationStage, before: str, after: str) -> list[str]:
    """Return the names of invariants the mutation broke. Empty = OK."""
    failed: list[str] = []
    if stage.max_shrink_pct is not None and _shrink_pct(before, after) > stage.max_shrink_pct:
        failed.append(f"max_shrink_pct({stage.max_shrink_pct:.2f})")
    for check in stage.must_preserve:
        try:
            if not check(before, after):
                failed.append(check.__name__ or repr(check))
        except Exception:  # noqa: BLE001 - a broken check is itself a violation
            failed.append(f"{getattr(check, '__name__', 'check')}:raised")
    return failed


async def run_pipeline(
    stages: list[MutationStage],
    text: str,
    ctx: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
    on_event: EventSink | None = None,
) -> str:
    """Apply ``stages`` in order, enforcing each stage's invariants.

    A mutation that breaks an invariant is rejected per the stage's
    ``on_violation`` policy. Emits ``mutation_applied`` (text changed) and
    ``pipeline_violation`` (mutation rejected) events through ``on_event``.
    """
    sink = on_event or _default_sink
    ctx = ctx or {}
    for stage in stages:
        before = text
        try:
            result = stage.apply(text, ctx)
            if inspect.isawaitable(result):
                result = await result
            after = result if isinstance(result, str) else str(result)
        except Exception:  # noqa: BLE001 - a raising stage doesn't get to mutate
            sink("pipeline_stage_raised", {"stage": stage.name, "request_id": request_id})
            continue
        if after == before:
            continue
        failed = _check_invariants(stage, before, after)
        if failed:
            sink(
                "pipeline_violation",
                {
                    "stage": stage.name,
                    "policy": stage.on_violation,
                    "failed_invariants": failed,
                    "before_len": len(before),
                    "after_len": len(after),
                    "shrink_pct": round(_shrink_pct(before, after), 4),
                    "request_id": request_id,
                },
            )
            if stage.on_violation == "raise":
                raise PipelineViolationError(stage.name, failed, len(before), len(after))
            if stage.on_violation == "abort_pipeline":
                return before
            if stage.on_violation == "skip_stage":
                text = before
                continue
            # log_only — accept anyway.
            text = after
            continue
        sink(
            "mutation_applied",
            {
                "stage": stage.name,
                "before_len": len(before),
                "after_len": len(after),
                "shrink_pct": round(_shrink_pct(before, after), 4),
                "request_id": request_id,
            },
        )
        text = after
    return text


def run_pipeline_sync(
    stages: list[MutationStage],
    text: str,
    ctx: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
    on_event: EventSink | None = None,
) -> str:
    """Sync façade (``asyncio.run``) for callsites without an event loop."""
    return asyncio.run(run_pipeline(stages, text, ctx, request_id=request_id, on_event=on_event))


__all__ = [
    "EventSink",
    "MutationStage",
    "OnViolation",
    "PipelineViolationError",
    "preserve_min_length",
    "preserve_question_marks",
    "run_pipeline",
    "run_pipeline_sync",
]
