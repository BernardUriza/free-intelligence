"""Mutation pipeline — re-exports fi_runner's engine + insult-specific invariants.

The generic Intercepting-Filter engine (``MutationStage``, ``run_pipeline``, the
``max_shrink_pct`` / ``must_preserve`` invariants and ``on_violation`` policies)
now lives in ``fi_runner.pipeline`` — one core, many runners. insult imports it
from fi_runner, not the other way around.

Why the engine moved: the incident that motivated it (a dedup stage silently
deleting 51% of a substantive reply to a vulnerable user — logged, not blocked)
is exactly the kind of guarantee that belongs in the shared core so EVERY runner
gets it, not just the one that got burned.

This module keeps:
- ``preserve_react_markers`` — the only insult-specific invariant ([REACT:…]
  blocks are an insult output convention; fi-core knows nothing about them).
- ``run_pipeline`` / ``run_pipeline_sync`` wrappers that forward the engine's
  telemetry to structlog, so insult's existing KQL queries on ``mutation_applied``
  / ``pipeline_violation`` keep working.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from fi_runner.pipeline import (
    EventSink,
    MutationStage,
    OnViolation,
    PipelineViolationError,
    preserve_min_length,
    preserve_question_marks,
)
from fi_runner.pipeline import run_pipeline as _run_pipeline
from fi_runner.pipeline import run_pipeline_sync as _run_pipeline_sync

log = structlog.get_logger()

_REACT_MARKER_RE = re.compile(r"\[REACT:[^\]]*\]")


def preserve_react_markers(before: str, after: str) -> bool:
    """The number of [REACT:emoji,…] markers must not decrease (insult-specific).

    deduplicate_opener — the stage that triggered the whole invariant design —
    nuked the first line of a response, which carried the ``[REACT:🌊💙…]`` block
    meant for the user. Stages other than strip_reactions must keep the count.
    """
    return len(_REACT_MARKER_RE.findall(after)) >= len(_REACT_MARKER_RE.findall(before))


def _structlog_sink(event: str, fields: dict[str, Any]) -> None:
    """Forward fi_runner pipeline events to structlog (keeps insult's KQL queries)."""
    if event in ("pipeline_violation", "pipeline_stage_raised"):
        log.warning(event, **fields)
    else:
        log.info(event, **fields)


async def run_pipeline(
    stages: list[MutationStage],
    text: str,
    ctx: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
) -> str:
    """Run the fi_runner mutation pipeline, forwarding telemetry to structlog."""
    return await _run_pipeline(stages, text, ctx, request_id=request_id, on_event=_structlog_sink)


def run_pipeline_sync(
    stages: list[MutationStage],
    text: str,
    ctx: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
) -> str:
    """Sync façade for the structlog-wired pipeline."""
    return _run_pipeline_sync(stages, text, ctx, request_id=request_id, on_event=_structlog_sink)


__all__ = [
    "EventSink",
    "MutationStage",
    "OnViolation",
    "PipelineViolationError",
    "preserve_min_length",
    "preserve_question_marks",
    "preserve_react_markers",
    "run_pipeline",
    "run_pipeline_sync",
]
