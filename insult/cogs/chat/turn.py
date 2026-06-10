"""Single-turn entry point — thin wrapper around the stage pipeline.

Pre-PR2 this module contained a 580-line procedural ``run_turn`` that
interleaved 14+ concerns (attachments, memory, context, preset, flows,
LLM, mutations, persistence, side-effects, delivery, telemetry) in one
function. PR 2 splits those concerns into typed stages
(``cogs/chat/stages.py``) executed by an orchestrator
(``cogs/chat/pipeline.py``). This file is now the cog's entry point:

  1. Build a ``TurnCtx`` from the cog's arguments.
  2. Hand it + ``DEFAULT_STAGES`` to ``run_pipeline``.
  3. Map the ``PipelineResult`` to the outcome string the cog logs.

Outcomes a stage can produce:
  - ``"ok"``               — full pipeline ran cleanly
  - ``"trivial_skipped"``  — message matched triviality rules
  - ``"failed:<stage>"``   — typed failure surfaced; failure_stage +
                             failure_class are in ``chat_turn_failed``

The legacy outcomes (``"llm_failed"``, ``"delivery_failed"``,
``"delivery_crashed"``, ``"context_failed"``) are mapped from the new
``"failed:<stage>"`` shape inside ``run_turn`` so the cog and its tests
keep their existing vocabulary while logs gain typed structure.
"""

from __future__ import annotations

import time

import discord
import structlog

from insult.cogs.chat.pipeline import TurnCtx, TurnRuntimeDeps, run_pipeline
from insult.cogs.chat.stages import DEFAULT_STAGES

log = structlog.get_logger()


# Map ``failed:<stage>`` outcomes back to the legacy outcome vocabulary
# the cog and its tests still rely on. Anything not in the map keeps the
# ``failed:<stage>`` literal so KQL still sees the structured shape.
_LEGACY_OUTCOME: dict[str, str] = {
    "failed:build_context": "context_failed",
    "failed:call_llm": "llm_failed",
    "failed:delivery": "delivery_failed",
}


async def run_turn(
    message: discord.Message,
    text: str,
    *,
    turn_start: float,
    deps: TurnRuntimeDeps,
) -> str:
    """Execute one full turn. Returns an outcome string for
    ``chat_turn_end``. See module docstring for the outcome vocabulary.

    ``deps`` is the host-wired runtime assembled at the composition edge
    (the cog, from ``app.Container`` + its own task-spawner); this entry
    point just seeds it into the ``TurnCtx`` and runs the pipeline.
    """
    ctx = TurnCtx(
        message=message,
        text=text,
        turn_start=turn_start,
        deps=deps,
    )

    result = await run_pipeline(ctx, DEFAULT_STAGES)

    # The orchestrator already emitted ``chat_turn_failed`` on failure.
    # Map to legacy outcome strings so the cog's terminal
    # ``chat_turn_end`` keeps the vocabulary tests assert on.
    outcome = _LEGACY_OUTCOME.get(result.outcome, result.outcome)

    # One terminal pipeline summary log — sibling to ``chat_turn_end``
    # but with the structured stage_timings the cog's log doesn't carry.
    # KQL alerts that want per-stage breakdowns key on this event.
    log.info(
        "chat_turn_pipeline_summary",
        outcome=outcome,
        failure_stage=result.failure_stage,
        failure_class=result.failure_class,
        stage_timings=result.stage_timings,
        total_ms=int((time.monotonic() - turn_start) * 1000),
        delivery_mode=ctx.delivery_mode or None,
    )

    return outcome
