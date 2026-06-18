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

Turn lifecycle — S1 through S5
-------------------------------
Only S2, S4, and S5 have explicit Input/Result DTOs here. S1 and S3
operate directly on ``TurnCtx`` because:

- S1 (Intake): bind_identity → process_attachments → memory_store →
  ensure_not_trivial → build_context → load_facts. These stages
  populate ``TurnCtx`` itself; there is no meaningful input boundary
  to carve out — ``TurnCtx`` IS the intake accumulator.
- S3 (Prompt construction): classify_and_analyze + resolve_tools_and_model.
  The prompt is assembled inline from multiple ``TurnCtx`` fields via
  ``_build_behavioral_guidance``; a dedicated DTO would only proxy the
  same fields. When S3 grows a stable, testable seam it will earn one.

S2, S4, and S5 have DTOs because they each have a pure-function
implementation (``assemble_knowledge``, ``interpret_output``,
``assimilate_turn``) that is unit-tested in isolation. The DTO is the
boundary that makes that isolation possible.

Domain objects produced by S1 stages (``DisclosureResult``, ``PolicyBundle``)
live in their own modules (``disclosure.py``, ``capability_ports.py``) because
they belong to domain/capability services, not to the pipeline contract.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import discord
import structlog

if TYPE_CHECKING:
    from personas.insult.cogs.chat.capability_ports import (
        HostDegraderPort,
        OutputMutationPort,
        PresetEnginePort,
        RetrievalPort,
        S1bPolicyPort,
    )
    from personas.insult.cogs.chat.ports import ArcPort, FactsPort, StancePort

from personas.insult.cogs.chat._failure import (
    Criticality,
    FailureClass,
    StageFailure,
    StageStop,
)

log = structlog.get_logger()


@dataclass(frozen=True)
class TurnRuntimeDeps:
    """The host-wired runtime the turn pipeline runs *against*.

    Composition-root seam: these are the configuration / orchestration
    dependencies the cog injects ONCE per turn — the data plane
    (``memory``), the config singleton (``settings``), the Discord
    gateway handle (``bot``), the anti-repetition ledger
    (``expression_history``), the Opus spend budget (``opus_budget``),
    the background-task spawner (``spawn_task``), the tool catalogue
    (``all_tools``), and the two runner-backed LLM surfaces
    (``agent_client`` / ``judge_client``).

    They are grouped here, frozen, to separate *what the host supplies*
    from *the mutable turn state* a stage reads-and-writes on ``TurnCtx``.
    Stages reach them explicitly via ``ctx.deps.<name>`` instead of
    pulling loose fields off the context — making the orchestration
    boundary visible without moving any domain logic.

    The two runner-backed LLM surfaces (see ``app.Container``):
    ``agent_client`` drives the turn (``/v1/turn``); ``judge_client``
    serves one-shot utility calls (``/v1/judge``): image summary, preset
    classifier, fact extraction, tool inauguration. Both may be ``None``
    only when the runner isn't configured.
    """

    memory: Any
    settings: Any
    bot: Any
    expression_history: Any
    opus_budget: Any
    spawn_task: Callable[..., None]
    all_tools: list
    # Domain-service ports (S2 render + S5 write) and capability ports, wired
    # by insult.composition. The pipeline depends on the Protocol, never the
    # insult.core.* impl.
    facts: FactsPort
    stance: StancePort
    arc: ArcPort
    retrieval: RetrievalPort
    preset_engine: PresetEnginePort
    policy: S1bPolicyPort
    mutation: OutputMutationPort
    agent_client: Any = None
    judge_client: Any = None
    # Host degrader (gpt-4.1 honest-degradation capability). INERT by default:
    # None unless ``host_router_enabled`` is True, in which case the
    # honest-degradation tail asks it for the notice instead of the static one.
    host_degrader: HostDegraderPort | None = None
    # Deterministic shadow router (HOST 5/6 slice A). A pure ``str -> ShadowDecision``
    # callable from demux_ai, or None when ``shadow_router_enabled`` is False. The
    # bind-identity stage calls it to LOG ``shadow_router_decision`` (current vs
    # shadow target) — it never changes where the turn routes. No LLM, no spend.
    shadow_route: Callable[[str], Any] | None = None
    # LLM shadow router (HOST 5/6 slice A.2). An ASYNC ``str -> LLMShadowDecision``
    # callable (gpt-4.1 via demux_ai), or None when ``llm_shadow_router_enabled`` is
    # False (default — it SPENDS). The bind-identity stage runs it OFF the critical
    # path (a background task) to LOG ``llm_shadow_router_decision`` (current vs the
    # host brain's independent target) — never changes routing, no cutover.
    llm_shadow_route: Callable[[str], Any] | None = None


@dataclass
class TurnCtx:
    """Mutable state carried through the pipeline.

    Inputs are set at construction by the cog; outputs are filled
    progressively as stages run. A stage reads only what previous
    stages wrote — no global state, no module-level singletons (except
    the health state ledger which is intentionally a singleton).

    The host-wired runtime dependencies live on ``deps`` (a frozen
    ``TurnRuntimeDeps``); everything else here is per-turn input or
    progressively-filled output.
    """

    # --- Inputs ---
    message: discord.Message
    text: str
    turn_start: float
    # Host-wired runtime (config / orchestration), injected by the cog.
    deps: TurnRuntimeDeps

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
    # Background task running PresetEnginePort.resolve() in parallel with
    # the disclosure / arc I/O so the Haiku call latency is masked. The
    # engine owns timeout/fallback/shadow-run internally; the pipeline only
    # owns the scheduling (create_task in stage 06, await in stage 08).
    preset_task: Any = None
    # PresetEngineResult awaited from preset_task: selection (contracts
    # vocabulary) + classifier telemetry scalars + rendered guidance_block.
    preset_result: Any = None
    flow_analysis: Any = None
    # Rendered flow-guidance fragment from PolicyBundle — the runner path
    # (_build_behavioral_guidance) reuses it so flows render ONCE per turn.
    flow_guidance: str = ""
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

    # --- Multi-persona routing ---
    # Set by Stage 01 when the message starts with "@vultur " or "~vultur ".
    # The runner loads shared/personas/vultur.md instead of the default Insult
    # persona. None = Insult (default).
    persona_id: str | None = None

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


@dataclass
class S4OutputInterpretationInput:
    """S4 (Output Interpretation) dependency surface.

    Declares the minimal context the post-LLM interpretation needs to turn the
    model's raw text into the deliverable response + side-channel markers,
    instead of handing it the whole ``TurnCtx``. The interpreter owns no state
    and reads nothing — every value it needs is captured here at the call site.

    - ``raw_text``: the model's verbatim output (before any mutation).
    - ``user_text``: the originating user message — only ``strip_echoed_quotes``
      consumes it (to detect quoted-back fragments).
    - ``recent_openers`` / ``recent_response_lengths``: the anti-repetition
      windows feeding ``deduplicate_opener`` / ``enforce_length_variation``.
    - ``intent_unattended``: whether a reminder intent went unhandled this turn,
      which appends the in-character "no agendé recordatorio" tail.
    """

    raw_text: str
    user_text: str
    recent_openers: list = field(default_factory=list)
    recent_response_lengths: list = field(default_factory=list)
    intent_unattended: bool = False


@dataclass
class S4OutputInterpretationResult:
    """The interpreted post-LLM output, split into its delivery + side channels.

    S4 owns neither persistence nor delivery — it parses and mutates the raw
    text and bundles the results. The stage applies the side effects (spawning
    the ``persist_remembers`` task, setting ``ctx`` fields, logging). Behavior is
    identical to the inline post-LLM block this replaces (same parsers, same
    mutation order, same orphan-emoji harvest).

    - ``response_text``: the final, mutation-applied text to deliver.
    - ``reactions``: the emoji reactions to fire (parsed markers + harvested
      inline orphans).
    - ``remembered_facts``: facts parsed from ``[REMEMBER:]`` markers, handed
      back for the stage to persist (parsing here, persistence in the stage).
    - ``emojis_harvested_inline``: count of inline emojis rescued into
      ``reactions`` despite the model ignoring the ``[REACT:]`` wrapper — kept
      for telemetry parity with the legacy ``stage_post_llm_done`` event.
    """

    response_text: str = ""
    reactions: list = field(default_factory=list)
    remembered_facts: list = field(default_factory=list)
    emojis_harvested_inline: int = 0


@dataclass
class S5TurnAssimilationInput:
    """S5 (Turn Assimilation) dependency surface.

    Declares the minimal set of turn outputs the assimilation write-back needs
    to persist the completed turn into long-term state, instead of handing it
    the whole ``TurnCtx``. The assimilator owns the write orchestration; the
    domain stores (``memory``) still own the actual rows.

    - ``response_text``: the delivered reply (pre delimiter-normalization — the
      assimilator applies the same ``MESSAGE_DELIMITER`` → newline cleanup the
      inline stage did).
    - identity (``channel_id``/``user_id``/``guild_id``/``channel_name``/
      ``bot_user_id``/``bot_user_name``) + ``model_used``: the message row.
    - ``arc_state`` + ``disclosure_severity`` / ``user_state`` / ``preset_mode``:
      the inputs to the per-turn arc advance.
    - ``assertion_density``: gates stance extraction (≥ 0.4) and feeds it.
    """

    response_text: str
    channel_id: str
    user_id: str
    guild_id: str | None
    channel_name: str | None
    bot_user_id: str
    bot_user_name: str
    model_used: str | None
    arc_state: Any = None
    disclosure_severity: Any = None
    user_state: str = ""
    preset_mode: str = ""
    assertion_density: float = 0.0


@dataclass
class S5TurnAssimilationResult:
    """Summary of what the turn assimilation wrote back.

    S5 is the terminal write-back phase — nothing downstream consumes its
    output, so production ignores this result. It exists for symmetry with the
    S2/S4 contracts and for tests/observability to assert *what* was assimilated
    without re-reading the stores. Behavior is identical to the inline stage
    this replaces (same writes, same order, same stance gate; no new logs).

    - ``message_stored``: whether the assistant message row was written (skipped
      when the cleaned response is blank).
    - ``arc_phase``: the phase the arc advanced to this turn (always upserted).
    - ``stances_stored``: count of stance rows extracted + persisted this turn.
    """

    message_stored: bool = False
    arc_phase: str | None = None
    stances_stored: int = 0


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
                ctx.deps.spawn_task(stage.fn(ctx), name=stage.name)
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
