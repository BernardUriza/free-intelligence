"""Stage-based turn orchestrator.

Replaces the monolithic ``turn.run_turn`` body. Each stage is a
self-contained step that reads and writes ``TurnCtx``. The orchestrator
walks the stage list, captures typed ``StageFailure`` / ``StageStop``,
records per-stage timings, and emits a single ``chat_turn_end`` event
with the full structured shape:

    {
      "outcome": "ok" | "trivial_skipped" | "llm_failed" | ...,
      "failure_stage": null | "llm_call" | "delivery" | ...,
      "failure_class": null | "llm_failed" | "discord_throttled" | ...,
      "total_ms": int,
      "stage_timings": {"process_attachments": 12, "call_llm": 2300, ...}
    }

This shape is what the 2026-05-08T23:59 post-mortem found missing. The
pre-PR2 flat ``chat_llm_failed`` event lied when the LLM never ran (it
was actually ``channel.typing()`` that exploded), and the KQL alert
side could not distinguish stages without parsing free-form strings.

Stage authoring contract:

    @dataclass(frozen=True)
    class Stage:
        name: str               # appears in logs as failure_stage
        criticality: Criticality
        fn: Callable[[TurnCtx], Awaitable[None]]

The ``fn`` mutates ``TurnCtx`` to hand state to later stages. It can:

- ``return`` normally → stage succeeded; pipeline continues.
- ``raise StageStop(outcome)`` → pipeline ends with that outcome,
  treated as success (no failure log).
- ``raise StageFailure(...)`` → pipeline ends with the typed failure
  log, ``outcome = "failed:<stage>"``.
- Raise any other ``Exception`` → orchestrator wraps it in a
  ``StageFailure`` of class ``UNEXPECTED``. This is the catch-all so
  no exception ever bubbles past the cog.

``BACKGROUND`` stages are spawned via ``ctx.spawn_task`` and the
pipeline does not await them. They CAN raise; the cog's task tracker
logs and isolates the failure.

``COSMETIC`` stages run inline but their failures are swallowed —
``StageFailure`` becomes a ``stage_cosmetic_failed`` warning and the
pipeline continues.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import discord
import structlog

from insult.cogs.chat._failure import (
    Criticality,
    FailureClass,
    StageFailure,
    StageStop,
)

log = structlog.get_logger()


@dataclass
class TurnCtx:
    """Mutable state carried through the pipeline.

    Inputs are set at construction by the cog; outputs are filled
    progressively as stages run. A stage reads only what previous
    stages wrote — no global state, no module-level singletons (except
    the health state ledger which is intentionally a singleton).
    """

    # --- Inputs ---
    message: discord.Message
    text: str
    turn_start: float
    memory: Any
    settings: Any
    bot: Any
    expression_history: Any
    opus_budget: Any
    spawn_task: Callable[..., None]
    all_tools: list
    # The two runner-backed LLM surfaces (see app.Container). agent_client
    # drives the turn (/v1/turn); judge_client serves one-shot utility calls
    # (/v1/judge): image summary, preset classifier, fact extraction, tool
    # inauguration. Both may be None only when the runner isn't configured.
    agent_client: Any = None
    judge_client: Any = None

    # --- Derived identity (filled by the first stage) ---
    channel_id: str = ""
    user_id: str = ""
    user_name: str = ""
    guild_id: str | None = None
    channel_name: str | None = None
    context_key: str = ""

    # --- Attachments ---
    attachment_blocks: list = field(default_factory=list)
    text_for_memory: str = ""  # original text + image summary

    # --- Style / profile ---
    profile: Any = None

    # --- Context build ---
    context: list = field(default_factory=list)
    recent: list = field(default_factory=list)
    user_facts: list = field(default_factory=list)
    other_participants_facts: dict = field(default_factory=dict)
    serenityops_snapshot: Any = None
    server_pulse: Any = None

    # --- Pre-LLM analysis ---
    disclosure: Any = None
    arc_state: Any = None
    preset: Any = None
    # Background task running classify_preset_llm() in parallel with the
    # disclosure / arc / facts I/O so the Haiku call latency is masked.
    # Awaited in `_stage_classify_and_analyze` with a timeout; on failure
    # the regex classifier becomes the result. Set to None when the LLM
    # middleware is disabled via settings or when the cog is in a path
    # that doesn't use it.
    preset_task: Any = None
    flow_analysis: Any = None
    stances: list = field(default_factory=list)

    # --- Prompt + tool config ---
    system_prompt: str = ""
    tools: list = field(default_factory=list)
    tool_choice: dict | None = None
    model_choice: Any = None  # ModelChoice from routing

    # --- LLM output ---
    llm_response: Any = None
    llm_ms: int = 0
    intent_unattended: bool = False

    # --- Post-LLM transforms ---
    response_text: str = ""
    raw_response_text: str = ""  # before mutations, for telemetry
    reactions: list = field(default_factory=list)
    recent_openers: list = field(default_factory=list)
    recent_response_lengths: list = field(default_factory=list)

    # --- Telemetry / outcome ---
    delivery_mode: str = ""  # "text" | "reaction" | "silent"

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.turn_start) * 1000)


@dataclass(frozen=True)
class Stage:
    """Declarative stage definition. ``fn`` mutates ``TurnCtx``; the
    orchestrator handles failure classification, timing, and logs."""

    name: str
    criticality: Criticality
    fn: Callable[[TurnCtx], Awaitable[None]]


@dataclass
class PipelineResult:
    """Final shape returned by ``run_pipeline``. The cog turns this
    into the values the legacy ``chat_turn_end`` expects."""

    outcome: str
    failure_stage: str | None = None
    failure_class: str | None = None
    stage_timings: dict[str, int] = field(default_factory=dict)


@dataclass
class S2KnowledgeAssemblyInput:
    """S2 (Knowledge Assembly) dependency surface.

    Declares the minimal set of read-facet *sources* S2 needs to assemble the
    per-turn knowledge blocks, instead of handing it the whole ``TurnCtx``.
    Domain services still own the actual reads — this is just the input the
    assembly orchestrator consumes. ``text``/``user_id`` are duck-type
    compatible with the existing retrieval helpers.
    """

    user_id: str
    text: str
    other_participants_facts: dict = field(default_factory=dict)


@dataclass
class S2KnowledgeAssemblyResult:
    """The assembled read-facet fragments for the runner payload.

    Each field is a final string fragment (or ``None`` when the facet produced
    nothing). S2 owns neither retrieval nor state — it bundles what the domain
    services returned.

    Scope (smallest safe seam): covers only the read facets genuinely assembled
    at the LLM-payload point today — semantic retrieval (deep_memory),
    film-corpus retrieval, and the third-party facts fragment. The
    arc/stance/style/author-facts fragments currently flow through the
    prompt-composition path (``system_prompt``, built earlier in
    ``classify_and_analyze``) and are intentionally NOT routed here yet —
    doing so would change behavior and belongs to a later S3 seam.
    """

    relevant_memory_block: str | None = None
    film_references_block: str | None = None
    combined_memory: str | None = None
    other_people_block: str | None = None


async def run_pipeline(ctx: TurnCtx, stages: list[Stage]) -> PipelineResult:
    """Execute stages sequentially. ``BACKGROUND`` stages are spawned
    via ``ctx.spawn_task`` and the pipeline moves on immediately.
    ``BUSINESS`` stages abort the pipeline on failure. ``COSMETIC``
    stages log and continue.

    Returns a ``PipelineResult`` with outcome + structured failure
    metadata; the cog emits ``chat_turn_end`` from these fields so the
    log shape is consistent regardless of which stage exited the
    pipeline.
    """
    stage_timings: dict[str, int] = {}

    for stage in stages:
        if stage.criticality == Criticality.BACKGROUND:
            # Fire and forget. Failures inside the task are surfaced by
            # the cog's task tracker (``spawn_task`` wraps them).
            try:
                ctx.spawn_task(stage.fn(ctx), name=stage.name)
            except Exception:
                log.exception("stage_background_spawn_failed", stage=stage.name)
            continue

        stage_start = time.monotonic()
        try:
            await stage.fn(ctx)
        except StageStop as stop:
            stage_timings[stage.name] = int((time.monotonic() - stage_start) * 1000)
            return PipelineResult(outcome=stop.outcome, stage_timings=stage_timings)
        except StageFailure as f:
            stage_timings[stage.name] = int((time.monotonic() - stage_start) * 1000)
            if stage.criticality == Criticality.COSMETIC:
                log.warning(
                    "stage_cosmetic_failed",
                    stage=stage.name,
                    failure_class=f.failure_class.value,
                    error_type=f.error_type,
                    error_msg=f.error_msg,
                    stage_elapsed_ms=f.elapsed_ms,
                )
                continue
            # BUSINESS failure: log structured event, abort.
            log.error(
                "chat_turn_failed",
                failure_stage=f.stage,
                failure_class=f.failure_class.value,
                error_type=f.error_type,
                error_msg=f.error_msg,
                stage_elapsed_ms=f.elapsed_ms,
                stage_timings=stage_timings,
            )
            return PipelineResult(
                outcome=f"failed:{f.stage}",
                failure_stage=f.stage,
                failure_class=f.failure_class.value,
                stage_timings=stage_timings,
            )
        except Exception as e:
            stage_timings[stage.name] = int((time.monotonic() - stage_start) * 1000)
            if stage.criticality == Criticality.COSMETIC:
                log.exception(
                    "stage_cosmetic_crashed",
                    stage=stage.name,
                    error_type=type(e).__name__,
                    error_msg=str(e)[:200],
                )
                continue
            # Unexpected crash in a BUSINESS stage — wrap as UNEXPECTED
            # so the log shape is uniform and KQL filters stay simple.
            log.exception(
                "chat_turn_failed",
                failure_stage=stage.name,
                failure_class=FailureClass.UNEXPECTED.value,
                error_type=type(e).__name__,
                error_msg=str(e)[:200],
                stage_timings=stage_timings,
            )
            return PipelineResult(
                outcome=f"failed:{stage.name}",
                failure_stage=stage.name,
                failure_class=FailureClass.UNEXPECTED.value,
                stage_timings=stage_timings,
            )
        stage_timings[stage.name] = int((time.monotonic() - stage_start) * 1000)

    return PipelineResult(outcome="ok", stage_timings=stage_timings)
