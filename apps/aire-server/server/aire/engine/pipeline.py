"""The mutation pipeline — post-turn text stages, each policed by its invariants.

A GUARD is a safety net (detect, retry, sanitize). A STAGE here is a cosmetic or
normalizing mutation that runs AFTER the turn settles: language normalization,
list stripping, formatting. The danger of a blind mutation chain is that one
catch-all matcher silently nukes good content — so every stage declares what it
may not break (`invariants.py`) and a policy for when it does, and the runner
REJECTS the mutation instead of shipping it.

Origin, kept because it is the reason the invariants exist: a dedup stage in a
production Discord bot deleted 51% of a substantive reply to a vulnerable user.
It was logged, and shipped anyway. Copied here from fi-runner, which had already
generalized it out of that bot.

Zero-dep: telemetry leaves through an `on_event` sink (default stdlib logging),
so the daemon pulls in no structured-logging dependency and a consumer can
forward events wherever it already looks.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .invariants import MustPreserve, broken, shrink_pct

_log = logging.getLogger("aire.pipeline")

EventSink = Callable[[str, dict[str, Any]], None]
OnViolation = Literal["skip_stage", "abort_pipeline", "raise", "log_only"]


def _default_sink(event: str, fields: dict[str, Any]) -> None:
    _log.info("%s %s", event, fields)


@dataclass
class MutationStage:
    """One step in the post-turn mutation chain.

    `apply` is `(text, ctx) -> str` and may be sync or async. `ctx` carries the
    per-turn side data a stage needs without widening the engine's signature.
    `max_shrink_pct=None` disables the length guard, for a stage that legitimately
    removes almost everything."""

    name: str
    apply: Callable[[str, dict[str, Any]], str | Awaitable[str]]
    max_shrink_pct: float | None = 0.40
    must_preserve: list[MustPreserve] = field(default_factory=list)
    on_violation: OnViolation = "skip_stage"


class PipelineViolationError(Exception):
    """Raised when a stage broke its invariants and its policy is `raise`."""

    def __init__(self, stage: str, failed: list[str], before_len: int, after_len: int) -> None:
        super().__init__(f"stage={stage} violations={failed} {before_len}->{after_len} chars")
        self.stage = stage
        self.failed = failed
        self.before_len = before_len
        self.after_len = after_len


def _sizes(stage: MutationStage, before: str, after: str) -> dict[str, Any]:
    return {
        "stage": stage.name,
        "before_len": len(before),
        "after_len": len(after),
        "shrink_pct": round(shrink_pct(before, after), 4),
    }


async def _mutate(stage: MutationStage, text: str, ctx: dict[str, Any]) -> str | None:
    """The stage's output, or None if it raised — a raising stage does not get
    to mutate, and the turn keeps the text it already had."""
    try:
        result = stage.apply(text, ctx)
        if inspect.isawaitable(result):
            result = await result
        return result if isinstance(result, str) else str(result)
    except Exception:  # noqa: BLE001 — a broken stage never kills the turn
        return None


def _resolve(stage: MutationStage, before: str, after: str, failed: list[str]) -> str:
    """The text that survives a violation, per the stage's policy."""
    if stage.on_violation == "raise":
        raise PipelineViolationError(stage.name, failed, len(before), len(after))
    if stage.on_violation in ("abort_pipeline", "skip_stage"):
        return before
    return after


async def _step(
    stage: MutationStage, text: str, ctx: dict[str, Any],
    request_id: str | None, sink: EventSink,
) -> tuple[str, bool]:
    """One stage's contribution: the text after it, and whether the pipeline
    must stop here (its policy was `abort_pipeline` and it broke an invariant)."""
    before = text
    after = await _mutate(stage, text, ctx)
    if after is None:
        sink("pipeline_stage_raised", {"stage": stage.name, "request_id": request_id})
        return before, False
    if after == before:
        return before, False
    failed = broken(stage, before, after)
    if not failed:
        sink("mutation_applied", {**_sizes(stage, before, after), "request_id": request_id})
        return after, False
    sink("pipeline_violation", {**_sizes(stage, before, after), "policy": stage.on_violation,
                                "failed_invariants": failed, "request_id": request_id})
    return _resolve(stage, before, after, failed), stage.on_violation == "abort_pipeline"


async def run_pipeline(
    stages: list[MutationStage],
    text: str,
    ctx: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
    on_event: EventSink | None = None,
) -> str:
    """Apply `stages` in order, enforcing each stage's invariants.

    A mutation that breaks one is rejected per the stage's `on_violation` policy.
    Emits `mutation_applied` when the text changed and `pipeline_violation` when
    a mutation was refused — the incident that motivated this was logged but not
    blocked, so both halves ship together."""
    sink = on_event or _default_sink
    ctx = ctx or {}
    for stage in stages:
        text, stop = await _step(stage, text, ctx, request_id, sink)
        if stop:
            break
    return text
