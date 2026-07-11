"""Concrete stage implementations for the turn pipeline.

Each ``async def _stage_xxx(ctx: TurnCtx)`` reads from and writes to
the context, raising:
  - ``StageStop(outcome)`` to short-circuit the pipeline cleanly
    (trivial messages, context build refusal, etc.)
  - ``StageFailure(...)`` with typed ``FailureClass`` when the stage
    cannot complete and the user should see an in-character error

Stages are wired into a single ordered list at the bottom of this
module (``DEFAULT_STAGES``). The cog's ``run_turn`` constructs a
``TurnCtx`` and hands it + ``DEFAULT_STAGES`` to ``run_pipeline``.

Logging convention: each stage emits one ``stage_<name>_done`` event
with elapsed_ms + the structured outputs of that stage. The
orchestrator owns the terminal ``chat_turn_end`` log so the cog stays
in charge of the ``request_id``/``user_id``/``channel_id``
contextvars binding.
"""

from __future__ import annotations

import asyncio
import json as _json
import time
from typing import Any

import anthropic
import discord
import structlog

from khimeras_shared.attachments import process_attachments
from khimeras_shared.corpus import (
    animal_liberation_guidance,
    animal_tactics_guidance,
    film_criticism_guidance,
)
from khimeras_shared.reactions import add_reactions, harvest_orphan_emojis, parse_reactions
from khimeras_shared.research_marker import parse_research, strip_research
from personas.insult.cogs.chat._arbiter import supervise_runner_turn
from personas.insult.cogs.chat._failure import (
    Criticality,
    FailoverReason,
    FailureClass,
    StageFailure,
    StageStop,
    classify_discord_exception,
    decide_failover,
    send_with_reaction_fallback,
    spawn_typing_keepalive,
)
from personas.insult.cogs.chat.capability_ports import OutputMutationPort, RetrievalPort, S1bPolicyPort
from personas.insult.cogs.chat.context import (
    build_context,
    load_facts_smart,
    load_other_participants_facts,
    load_server_pulse,
    store_assistant_message,
    store_user_message,
    update_style_profile,
)
from personas.insult.cogs.chat.disclosure import scan_disclosure
from personas.insult.cogs.chat.invites import fire_invite, parse_invite
from personas.insult.cogs.chat.pipeline import (
    S2KnowledgeAssemblyInput,
    S2KnowledgeAssemblyResult,
    S4OutputInterpretationInput,
    S4OutputInterpretationResult,
    S5TurnAssimilationInput,
    S5TurnAssimilationResult,
    Stage,
    TurnCtx,
)
from personas.insult.cogs.chat.remembers import parse_remembers, persist_remembers
from personas.insult.cogs.chat.reminds import fire_remind, parse_remind
from personas.insult.cogs.chat.tasks import extract_user_facts
from personas.insult.core.delivery import MESSAGE_DELIMITER, send_response
from personas.insult.core.errors import ErrorType, classify_error, get_error_response
from personas.insult.core.image_transcript import persist_image_transcript
from personas.insult.core.reminders import detect_reminder_intent
from personas.insult.core.triviality import is_trivial

log = structlog.get_logger()


# Upper bound for the host degrader (gpt-4.1) in the honest-degradation tail. The
# notice is a 2-sentence completion and the static fallback is instant, so the
# already-failed turn must never hang waiting on it. A timeout falls into the
# conservative fallback below (TimeoutError → static notice), same as any other
# degrader failure.
HOST_DEGRADE_TIMEOUT_S = 12.0


# --- Stage 01: identity binding (no I/O, just derive fields from message) ---


# How many recent channel messages ride into the routing decision as context.
# Small on purpose: enough to detect "this is a continuation of frugivoro's
# exchange" (the 2026-07-06 P0: Alex's bare pantry list mid-fruit-conversation
# routed default_insult because the router saw the message alone), tiny enough
# to keep the per-call token cost in the hundreds.
ROUTER_CONTEXT_MESSAGES = 8


async def _fetch_router_context(memory: Any, channel_id: str) -> str | None:
    """Last N channel messages as ``user: message`` lines (oldest first) for the
    routing brain. Best-effort: any fault returns None (route without context)
    rather than failing the shadow decision."""
    if memory is None:
        return None
    try:
        rows = await memory.get_recent(channel_id, limit=ROUTER_CONTEXT_MESSAGES)
    except Exception:
        log.exception("llm_router_context_fetch_failed", channel_id=channel_id)
        return None
    lines = [
        f"{row.get('user_name', '?')}: {str(row.get('content', ''))[:300]}"
        for row in rows
        if str(row.get("content", "")).strip()
    ]
    return "\n".join(lines) if lines else None


async def _run_llm_shadow_decision(
    llm_shadow_route: Any,
    raw_text: str,
    current_target: str,
    guild_id: str | None,
    channel_id: str,
    router_budget: Any = None,
    memory: Any = None,
) -> None:
    """Run the gpt-4.1 LLM shadow route (HOST 5/6 slice A.2) and LOG its decision
    next to where the turn ACTUALLY went. Runs as a BACKGROUND task so the Azure
    call never delays the user's reply (no observable behavior change, no cutover).
    Wrapped: a shadow fault logs ``llm_shadow_router_failed`` and is invisible to
    the turn — it must never raise into the pipeline.

    Context-aware (HOST paso 2): fetches the last ``ROUTER_CONTEXT_MESSAGES``
    channel messages INSIDE this background task (never on the turn's critical
    path) so the brain can route continuations to the persona already holding
    the exchange.

    Spend-capped: ``router_budget`` ($5/week, Bernard 2026-06-21) is checked BEFORE
    the Azure call and the call's real token cost recorded after. Over the weekly cap
    the router fails SAFE (skips the call) — an honored budget, not a 'trust me it's
    cheap'."""
    if router_budget is not None and not router_budget.can_spend():
        log.warning(
            "llm_router_budget_exceeded",
            spent_usd=round(router_budget.spent_this_week(), 4),
            cap_usd=router_budget.cap_usd,
            guild_id=guild_id,
            channel_id=channel_id,
        )
        return
    context = await _fetch_router_context(memory, channel_id)
    try:
        decision = await llm_shadow_route(raw_text, context)
        if router_budget is not None:
            total = router_budget.record(decision.input_tokens, decision.output_tokens)
            log.info(
                "llm_router_spend",
                call_input_tokens=decision.input_tokens,
                call_output_tokens=decision.output_tokens,
                week_spent_usd=round(total, 4),
                cap_usd=router_budget.cap_usd,
            )
        log.info(
            "llm_shadow_router_decision",
            current_target=current_target,
            llm_shadow_target=decision.target,
            llm_shadow_reason=decision.reason,
            llm_diverged=decision.target != current_target,
            guild_id=guild_id,
            channel_id=channel_id,
            route_input_len=len(raw_text),
            route_context_chars=len(context) if context else 0,
            llm_input_tokens=decision.input_tokens,
            llm_output_tokens=decision.output_tokens,
        )
    except Exception:
        log.exception("llm_shadow_router_failed")


async def _stage_bind_identity(ctx: TurnCtx) -> None:
    msg = ctx.message
    ctx.channel_id = str(msg.channel.id)
    ctx.user_id = str(msg.author.id)
    ctx.user_name = msg.author.display_name
    ctx.guild_id = str(msg.guild.id) if msg.guild else None
    ctx.channel_name = msg.channel.name if hasattr(msg.channel, "name") else None
    ctx.context_key = f"{ctx.channel_id}:{ctx.user_id}"

    # Prefix addressing (`@vultur ` / `~vultur ` as literal TEXT) is DEAD — retired
    # 2026-07-08 with the strangler-fig's last cut, once the gpt-4.1 cutover went
    # live. A sibling is now reached by a real Discord mention or a vocative alias
    # ("frugi, ..."), both owned by the gateway's `should_respond`, or by the LLM
    # router summoning it through /invite. The deterministic shadow (slice A) and
    # its cutover (slice B) went with it: both mirrored this prefix rule BY
    # CONSTRUCTION, so with the rule gone they could only ever report themselves.

    log.info(
        "chat_turn_start",
        text_len=len(ctx.text),
        text_preview=ctx.text[:120],
        attachments=len(msg.attachments),
        is_voice=bool(msg.flags.voice),
        guild_id=ctx.guild_id,
        channel_name=ctx.channel_name,
        persona_id=ctx.persona_id,
    )

    # HOST 5/6 slice A.2 — gpt-4.1 LLM SHADOW router. Asks the host BRAIN to pick a
    # target INDEPENDENTLY, so a genuine divergence is observable (unlike the retired
    # deterministic shadow, which mirrored the prefix rule and could only agree with
    # it). Spend-gated (llm_shadow_route is None unless llm_shadow_router_enabled)
    # and run OFF the critical path via spawn_task — the Azure call must never delay
    # the reply. Behavior-neutral: never changes routing.
    llm_shadow_route = getattr(ctx.deps, "llm_shadow_route", None)
    if llm_shadow_route is not None:
        # Gap B (rev161 autopsy): an attachment-only / empty-text turn has no
        # user_message for the gpt-4.1 router, which raised a spurious error-level
        # ValueError. Skip it cleanly — non-error, behavior-neutral — so empty turns
        # don't pollute the A.2.3 measurement error rate.
        if not ctx.text.strip():
            log.info(
                "llm_shadow_router_skipped",
                reason="empty_input",
                guild_id=ctx.guild_id,
                channel_id=ctx.channel_id,
            )
        else:
            current_target = ctx.persona_id or "insult"
            ctx.deps.spawn_task(
                _run_llm_shadow_decision(
                    llm_shadow_route,
                    ctx.text,
                    current_target,
                    ctx.guild_id,
                    ctx.channel_id,
                    getattr(ctx.deps, "router_budget", None),
                    getattr(ctx.deps, "memory", None),
                ),
                name="llm_shadow_router",
            )


# --- Stage 02: emit typing (BACKGROUND — never blocks LLM) ---


async def _stage_emit_typing(ctx: TurnCtx) -> None:
    """Fire-and-forget typing indicator. Replaces the
    ``async with channel.typing():`` that caused the 2026-05-08T23:59
    outage by 429-ing inside ``__aenter__``."""
    # Registered as BACKGROUND so the pipeline does not await it.
    # Imported here so the helper is co-located with the rest of
    # _failure.py's surface area.
    from personas.insult.cogs.chat._failure import emit_typing_safe

    await emit_typing_safe(ctx.message.channel)


# --- Stage 03: process attachments ---


async def _stage_process_attachments(ctx: TurnCtx) -> None:
    msg = ctx.message
    if not msg.attachments or msg.flags.voice:
        return

    stage_start = time.monotonic()
    blocks, errors = await process_attachments(msg.attachments)
    ctx.attachment_blocks = blocks
    for err in errors:
        # Errors are user-facing notices about unsupported attachments;
        # they are NOT pipeline failures. Send via the safe path so a
        # rate-limited channel doesn't cancel the rest of the turn.
        await send_with_reaction_fallback(msg, err)
    log.info(
        "stage_attachments_processed",
        blocks=len(blocks),
        errors=len(errors),
        elapsed_ms=int((time.monotonic() - stage_start) * 1000),
    )


# --- Stage 04: store user message + style profile ---


async def _stage_memory_store(ctx: TurnCtx) -> None:
    ctx.text_for_memory = ctx.text

    await store_user_message(
        ctx.deps.memory,
        ctx.channel_id,
        ctx.user_id,
        ctx.user_name,
        ctx.text_for_memory,
        ctx.guild_id,
        ctx.channel_name,
        discord_message_id=str(ctx.message.id),
    )

    # Postgres only stores text, so an image-only message persists as an
    # EMPTY row and future turns rebuild context with zero trace of what the
    # image contained. The runner's native vision covers ONLY the live turn;
    # the prior assumption (removed image_summary, v3.9.25) that the bot's
    # own reply serves as the future-turn trace is false — the in-character
    # reply carries commentary, not content (2026-07-05: the prescription/
    # treatment-schedule image was re-sent repeatedly and re-hallucinated
    # every time). Best-effort background vision transcript via /v1/judge,
    # appended to the stored row by discord_message_id.
    image_blocks = [b for b in ctx.attachment_blocks if isinstance(b, dict) and b.get("type") == "image"]
    if image_blocks and ctx.deps.judge_client is not None:
        ctx.deps.spawn_task(
            persist_image_transcript(
                ctx.deps.judge_client,
                ctx.deps.memory,
                str(ctx.message.id),
                image_blocks,
                model=ctx.deps.settings.summary_model,
            ),
            name="image_transcript",
        )

    # Style profile BEFORE the trivial gate so short-message users still
    # accumulate signal for language/formality/emoji detection.
    ctx.profile = await update_style_profile(ctx.deps.memory, ctx.user_id, ctx.text)

    log.info(
        "stage_memory_stored",
        elapsed_ms=ctx.elapsed_ms(),
        profile_confident=bool(ctx.profile and ctx.profile.is_confident),
    )


# --- Stage 05: triviality gate (StageStop on trivial messages) ---


async def _stage_ensure_not_trivial(ctx: TurnCtx) -> None:
    if not ctx.message.attachments and is_trivial(ctx.text):
        log.info("skipped_trivial_message", text=ctx.text[:40])
        raise StageStop("trivial_skipped")


# --- Stage 04b: LLM router cutover (HOST 5/6 slice C) ---


def _routable_sibling_ids() -> frozenset[str]:
    """Gateway personas the LLM router may route a turn to — the registered
    siblings (never "insult": that is this pipeline continuing normally)."""
    from shared.personas.registry import all_personas

    return frozenset(p.persona_id for p in all_personas())


def _effort_to_budget_s(effort: str, settings: Any) -> float:
    """Map the router's effort estimate onto the arbiter's initial time budget.
    Unknown effort → the normal (middle) budget — never the shortest, so a
    misparse can't starve a real task of time. Reads via getattr with the config
    defaults so a settings object missing a budget field falls back to normal
    instead of crashing the stage (fail-safe on every edge)."""
    if effort == "light":
        return float(getattr(settings, "runner_budget_light_s", 45.0))
    if effort == "heavy":
        return float(getattr(settings, "runner_budget_heavy_s", 300.0))
    return float(getattr(settings, "runner_budget_normal_s", 120.0))


async def _stage_llm_router_cutover(ctx: TurnCtx) -> None:
    """ACT on the context-aware gpt-4.1 routing decision for IMPLICIT turns
    (HOST 5/6 slice C — the LLM sibling of the deterministic slice-B cutover).

    Runs AFTER memory_store on purpose: the user's message is already in the
    shared Postgres, so a summoned sibling's ``get_recent`` sees the turn it is
    answering. Explicit addressing always outranks this stage (persona_id set →
    skip); a sibling decision suppresses Insult's reply and summons the persona
    through the gateway ``/invite`` (its own bot face, the canonical delivery).

    Fail-safe on EVERY edge — no route wired, empty text, budget cap, timeout,
    router fault, unknown target, non-202 invite → the stage returns and Insult
    answers exactly as today. A routing fault must never produce a mute turn.
    """
    route = getattr(ctx.deps, "llm_router_cutover_route", None)
    if route is None:
        return
    if ctx.persona_id is not None:
        return
    if not ctx.text.strip():
        return
    budget = getattr(ctx.deps, "router_budget", None)
    if budget is not None and not budget.can_spend():
        log.warning(
            "llm_router_cutover_budget_exceeded",
            spent_usd=round(budget.spent_this_week(), 4),
            cap_usd=budget.cap_usd,
            channel_id=ctx.channel_id,
        )
        return
    timeout_s = float(ctx.deps.settings.llm_router_cutover_timeout_seconds)
    start = time.monotonic()
    try:
        context = await _fetch_router_context(ctx.deps.memory, ctx.channel_id)
        decision = await asyncio.wait_for(route(ctx.text, context), timeout_s)
    except Exception:
        log.exception(
            "llm_router_cutover_failed",
            channel_id=ctx.channel_id,
            latency_ms=int((time.monotonic() - start) * 1000),
        )
        return
    if budget is not None:
        budget.record(decision.input_tokens, decision.output_tokens)
    # The arbiter's time budget for this turn — from the same gpt-4.1 call that
    # picked the target. When the turn stays with Insult (below), _stage_call_llm
    # reads it to size the runner supervision. A sibling summon (StageStop) never
    # reaches the call stage, so its budget is moot.
    ctx.time_budget_s = _effort_to_budget_s(getattr(decision, "effort", "normal"), ctx.deps.settings)
    # NOT "diverged": nothing is being compared against. This says the router
    # picked someone other than Insult, which for a correct frugivoro/vultur
    # summon is the router WORKING. The old `diverged` name made every healthy
    # sibling route read as a disagreement and inflated the watch metric.
    routed_to_sibling = decision.target != "insult"
    log.info(
        "llm_router_cutover_decision",
        target=decision.target,
        reason=decision.reason,
        routed_to_sibling=routed_to_sibling,
        latency_ms=int((time.monotonic() - start) * 1000),
        guild_id=ctx.guild_id,
        channel_id=ctx.channel_id,
        route_input_len=len(ctx.text),
        llm_input_tokens=decision.input_tokens,
        llm_output_tokens=decision.output_tokens,
    )
    if not routed_to_sibling:
        return
    if decision.target not in _routable_sibling_ids():
        log.warning("llm_router_cutover_unroutable_target", target=decision.target)
        return
    summon_reason = f"{ctx.user_name}: «{ctx.text[:600]}»"
    accepted = await fire_invite(
        summon_reason,
        channel_id=ctx.channel_id,
        guild_id=ctx.guild_id,
        channel_name=ctx.channel_name,
        persona_id=decision.target,
        invited_by="host_router",
    )
    if not accepted:
        log.warning(
            "llm_router_cutover_invite_rejected",
            target=decision.target,
            channel_id=ctx.channel_id,
        )
        return
    log.info(
        "llm_router_cutover_routed",
        target=decision.target,
        channel_id=ctx.channel_id,
        guild_id=ctx.guild_id,
    )
    raise StageStop(f"routed_to_{decision.target}")


# --- Stage 06: build context + facts ---


async def _stage_build_context(ctx: TurnCtx) -> None:
    context, recent = await build_context(
        ctx.deps.memory, ctx.deps.settings, ctx.channel_id, ctx.text, ctx.attachment_blocks
    )
    if context is None:
        log.warning("chat_turn_aborted", reason="context_failed")
        await send_with_reaction_fallback(ctx.message, get_error_response(ErrorType.CONTEXT_FAILED))
        raise StageFailure(
            stage="build_context",
            failure_class=FailureClass.CONTEXT_FAILED,
            error_type="ContextBuildReturnedNone",
            error_msg="build_context returned None",
            elapsed_ms=ctx.elapsed_ms(),
        )
    ctx.context = context
    ctx.recent = recent
    log.info(
        "stage_context_built",
        context_len=len(context),
        recent_count=len(recent),
        elapsed_ms=ctx.elapsed_ms(),
    )


async def _stage_load_facts(ctx: TurnCtx) -> None:
    ctx.user_facts = await load_facts_smart(ctx.deps.memory, ctx.user_id, ctx.text)
    log.info("stage_facts_loaded", facts_count=len(ctx.user_facts), elapsed_ms=ctx.elapsed_ms())
    ctx.other_participants_facts = await load_other_participants_facts(ctx.deps.memory, ctx.channel_id, ctx.user_id)
    ctx.server_pulse = await load_server_pulse(ctx.deps.memory, ctx.message, ctx.channel_id, ctx.text)

    # v3.8.0: pull the latest SerenityOps snapshot for the author. Cheap
    # single-row lookup keyed by user_id — the per-user index makes this an
    # index scan even at scale. None → user hasn't synced, prompt omits the
    # block entirely (the omission carries information too: Insult shouldn't
    # claim to "have your CV" when no row exists).
    try:
        ctx.serenityops_snapshot = await ctx.deps.memory.get_latest_serenityops_snapshot(ctx.user_id)
    except Exception:
        log.exception("serenityops_snapshot_load_failed", user_id=ctx.user_id)
        ctx.serenityops_snapshot = None

    # Launch the Preset Engine as a background task so its Haiku latency
    # overlaps with the remaining pre-LLM stages (disclosure scan, arc
    # load). The ENGINE owns timeout/fallback/shadow-run internally
    # (PresetEnginePort contract); the pipeline owns only this scheduling —
    # the carry between stage 06 and stage 08 is a plain asyncio.Task.
    # Disabled-flag / no-judge paths resolve fast inside the engine (pure
    # regex), so the task is created unconditionally.
    ctx.preset_task = asyncio.create_task(ctx.deps.preset_engine.resolve(ctx.text, ctx.recent, ctx.user_facts))


# --- Stage 07: disclosure scan + arc state ---


async def _stage_scan_disclosure(ctx: TurnCtx) -> None:
    ctx.disclosure = scan_disclosure(ctx.text)
    if ctx.disclosure.detected:
        await ctx.deps.memory.store_disclosure(
            ctx.channel_id,
            ctx.user_id,
            ctx.disclosure.category,
            ctx.disclosure.severity,
            _json.dumps(ctx.disclosure.signals),
            ctx.text[:200],
        )
    arc_data = await ctx.deps.memory.get_arc(ctx.channel_id, ctx.user_id)
    # Opaque carry: only the ArcPort understands this value. stages transports
    # it (S2 render → S5 advance) without reading its fields.
    ctx.arc_state = ctx.deps.arc.load(arc_data)

    ctx.recent_response_lengths = [len(m.get("content", "").split()) for m in ctx.recent if m["role"] == "assistant"][
        -5:
    ]


# --- Stage 08: preset + flows ---


async def _stage_classify_and_analyze(ctx: TurnCtx) -> None:
    # Settle the Preset Engine task launched in stage 06. The engine already
    # arbitrated LLM-vs-regex (timeout, fallback, shadow-run, divergence
    # telemetry) inside resolve(); what arrives here is the final result.
    ctx.preset_result = await ctx.preset_task
    effective_preset = ctx.preset_result.selection

    # Stance read pulled ahead of compose(): it is an independent data-plane
    # read and compose() is pure computation — same data, same renders.
    ctx.stances = await ctx.deps.memory.get_stances(ctx.channel_id, ctx.user_id, limit=5)

    bundle = ctx.deps.policy.compose(
        base_prompt=ctx.deps.settings.system_prompt,
        profile=ctx.profile,
        context_len=len(ctx.context),
        preset=effective_preset,
        text=ctx.text,
        recent=ctx.recent,
        user_facts=ctx.user_facts,
        context_key=ctx.context_key,
        server_pulse=ctx.server_pulse,
        recent_response_lengths=ctx.recent_response_lengths,
        arc_block=ctx.deps.arc.render_block(ctx.arc_state),
        stance_block=ctx.deps.stance.render_block(ctx.stances) if ctx.stances else "",
        facts_block=ctx.deps.facts.render_block(ctx.user_name, ctx.user_facts),
        other_participants_facts=ctx.other_participants_facts,
        serenityops_snapshot=ctx.serenityops_snapshot,
        serenityops_user_name=ctx.user_name,
    )
    ctx.preset = bundle.preset
    ctx.flow_analysis = bundle.flow_analysis
    ctx.flow_guidance = bundle.flow_guidance
    ctx.system_prompt = bundle.system_prompt

    log.info(
        "preset_classified",
        preset=ctx.preset.display_label,
        preset_internal=ctx.preset.mode.value,
        modifiers=[m.value for m in ctx.preset.modifiers],
        classifier_source=ctx.preset_result.classifier_source,
        classifier_ms=ctx.preset_result.classifier_ms,
        disclosure_severity=ctx.disclosure.severity,
        disclosure_category=ctx.disclosure.category,
        arc_phase=ctx.deps.arc.phase(ctx.arc_state),
        elapsed_ms=ctx.elapsed_ms(),
    )
    log.info(
        "stage_flows_analyzed",
        pressure=ctx.flow_analysis.pressure.pressure_level,
        user_state=ctx.flow_analysis.pressure.detected_state.value,
        shape=ctx.flow_analysis.expression.selected_shape.value,
        flavor=ctx.flow_analysis.expression.selected_flavor.value,
        awareness=ctx.flow_analysis.awareness.detected_pattern.value,
        epistemic_move=ctx.flow_analysis.epistemic.recommended_move.value,
        agreement_streak=ctx.flow_analysis.agreement_streak,
        elapsed_ms=ctx.elapsed_ms(),
    )

    if ctx.profile and ctx.profile.is_confident:
        log.info(
            "style_adapted",
            user_id=ctx.user_id,
            preset=ctx.preset.display_label,
            preset_modifiers=[m.value for m in ctx.preset.modifiers],
            language=ctx.profile.detected_language,
            formality=round(ctx.profile.formality, 2),
            technical=round(ctx.profile.technical_level, 2),
            verbosity=round(ctx.profile.avg_word_count, 1),
        )


# --- Stage 10: LLM call (BUSINESS-critical, the heart of the turn) ---
#
# Every turn rides the agent runner (/v1/turn) now — there is no legacy
# per-user flag and no direct-Anthropic fallback. The old
# `_pick_llm_for_turn` / `_user_in_agent_flag` branching (agent vs legacy
# legacy direct-Anthropic client, gated on INSULT_AGENT_SDK_USER_IDS) was
# removed when that client died. `_stage_call_llm` binds `ctx.deps.agent_client`
# directly.


# --- deep_memory auto-retrieval (v4.3.0) ---
# The runner exposes deep_memory as an opt-in MCP tool, but the agent called
# it on ~1.2% of turns (7/574 in 7d) — so the longitudinal history was a dead
# safety net. We instead PRE-FETCH the most relevant raw-history chunks,
# deterministically, and inject them into the turn payload so the agent always
# sees them. This is the other half of the "Larisa" fix: the ingest now works,
# and retrieval no longer depends on the model choosing to look.
#
# PR-D RetrievalPort (capability seam): the pre-fetch + rendering policy that
# used to live inline here moved behind ``RetrievalPort``
# (``capability_ports.py``) — the pipeline asks for finished blocks via
# ``ctx.deps.retrieval`` and no longer imports ``insult.core.deep_memory``.


async def assemble_knowledge(
    src: S2KnowledgeAssemblyInput, *, retrieval: RetrievalPort, policy: S1bPolicyPort
) -> S2KnowledgeAssemblyResult:
    """S2 Knowledge Assembly — bundle the per-turn knowledge fragments injected
    into the runner payload.

    Orchestrates the read-facet calls (deep_memory semantic retrieval, film
    corpus retrieval, third-party facts fragment) and bundles their output. S2
    owns neither retrieval nor state — the retrieval capability and the domain
    services do their own reads; this just assembles. Best-effort throughout:
    each facet returns None on failure without breaking the turn. Behavior is
    identical to the inline assembly this replaces (same calls, same order,
    same join)."""
    relevant_memory = await retrieval.user_memory_block(user_id=src.user_id, text=src.text)
    film_refs = await retrieval.film_references_block(src.text)
    combined = "\n\n".join(b for b in (relevant_memory, film_refs) if b) or None
    other_people = None
    if src.other_participants_facts:
        other_people = policy.other_people_block(src.other_participants_facts) or None
    return S2KnowledgeAssemblyResult(
        relevant_memory_block=relevant_memory,
        film_references_block=film_refs,
        combined_memory=combined,
        other_people_block=other_people,
    )


def _build_behavioral_guidance(ctx: TurnCtx) -> str:
    """Rebuild the per-turn behavioral layer for the agent runner.

    The legacy path baked preset + vulnerability overlay into the system
    prompt; the runner path discards `system_prompt`, so without this the
    classifier's tone decision never reaches the model — Insult answers in
    the raw persona.md base tone (the 2026-05-22 "muy agresivo" bug, where
    a vulnerable user's relational_probe + overlay was computed and dropped).

    We reconstruct ONLY the behavioral layer (not persona/facts, which the
    runner already has). The preset + vulnerability-overlay fragment arrives
    pre-rendered from the Preset Engine (`ctx.preset_result.guidance_block`,
    same core builders `build_adaptive_prompt` uses, so the two paths can't
    drift); flow + corpus guidance are appended here. Returns "" when
    there's nothing to add — the runner then behaves exactly as before.
    """
    parts = [ctx.preset_result.guidance_block]
    if ctx.flow_guidance:
        parts.append(ctx.flow_guidance)
    # Universal values corpus (shared with ALICE): the animal-liberation frame
    # activates by TOPIC, not by user. Appended LAST and AFTER the vulnerability
    # overlay on purpose — the corpus itself yields to safety, so safety
    # guidance must already be in `parts` above it. Empty string when the topic
    # is absent → no-op.
    corpus = animal_liberation_guidance(ctx.text)
    if corpus:
        parts.append(corpus)
        # Phase B: fine tactics via LEXICAL retrieval (post-histerical-search
        # pulido). Lexical scored 6/6 on this objection corpus, is model-less,
        # and matches ALICE's path exactly — semantic (all-MiniLM) added nothing
        # and is weak in Spanish. Only runs when the topic is present.
        tactics = animal_tactics_guidance(ctx.text)
        if tactics:
            parts.append(tactics)
    # Film-criticism (Vultur) method frame — same khimeras_shared/corpus mechanism,
    # topic-gated, expressed in Insult's own acid voice. Theory RAG (the 2 PDF
    # books) is retrieved separately and injected as `relevant_memory` so the
    # async embed call doesn't block this sync prompt builder.
    film = film_criticism_guidance(ctx.text)
    if film:
        parts.append(film)
    return "\n\n".join(p for p in parts if p)


async def _stage_call_llm(ctx: TurnCtx) -> None:
    async def _notify_retry() -> None:
        notify_start = time.monotonic()
        try:
            await ctx.message.channel.send(get_error_response(ErrorType.RETRY_NOTICE))
        except Exception:
            log.exception(
                "retry_notice_send_failed",
                delivery_ms=int((time.monotonic() - notify_start) * 1000),
            )
            return
        log.info("retry_notice_sent", delivery_ms=int((time.monotonic() - notify_start) * 1000))

    llm_start = time.monotonic()
    log.info(
        "llm_call_start",
        prompt_chars=len(ctx.system_prompt),
        context_messages=len(ctx.context),
        primary_model=ctx.deps.settings.llm_model,
    )
    # The agent runner is the only turn backend. ``backend`` is kept as a
    # constant so the agent-runner-specific payload blocks (channel_id,
    # behavioral_guidance, relevant_memory) and the ALICE-failover branch
    # below read self-documentingly.
    llm_client = ctx.deps.agent_client
    backend = "agent_runner"
    log.info("llm_backend_selected", backend=backend, user_id=ctx.user_id)
    # Keepalive the Discord typing indicator throughout the LLM call.
    # Discord's typing indicator times out at ~10s; agent runner turns can
    # legitimately take 15-90s (Sonnet + tool calls). The keepalive task
    # re-fires `send_typing` every ~7s and is cancelled in `finally`.
    typing_task = spawn_typing_keepalive(ctx.message.channel)
    try:
        # The retry_notice ("sigo en ello") is driven by the arbiter at budget
        # exhaustion now, NOT by chat()'s own on_timeout (which would only fire at
        # the hard cap, after the arbiter already decided).
        llm_kwargs: dict[str, Any] = {}
        if backend == "agent_runner":
            llm_kwargs["channel_id"] = ctx.channel_id
            llm_kwargs["user_id"] = ctx.user_id
            if ctx.persona_id:
                llm_kwargs["persona_id"] = ctx.persona_id
            guidance = _build_behavioral_guidance(ctx)
            if guidance:
                llm_kwargs["behavioral_guidance"] = guidance
                log.info(
                    "agent_behavioral_guidance_built",
                    preset=ctx.preset.display_label,
                    modifiers=[m.value for m in ctx.preset.modifiers],
                    vulnerable_overlay=ctx.preset_result.vulnerable_overlay,
                    guidance_chars=len(guidance),
                )
            # S2 Knowledge Assembly: bundle the per-turn knowledge fragments
            # injected into the runner payload. Covers:
            #  - v4.3.0 deterministic deep_memory auto-retrieval (raw-history
            #    chunks the agent always sees, vs the dead opt-in MCP tool);
            #  - v4.20.0 film-theory corpus retrieval under the Vultur frame;
            #  - the 2026-06-03 "Other People" fix: the runner discards
            #    system_prompt and rebuilds only the AUTHOR's facts, so facts
            #    about OTHER participants are forwarded explicitly here.
            knowledge = await assemble_knowledge(
                S2KnowledgeAssemblyInput(
                    user_id=ctx.user_id,
                    text=ctx.text,
                    other_participants_facts=ctx.other_participants_facts,
                ),
                retrieval=ctx.deps.retrieval,
                policy=ctx.deps.policy,
            )
            if knowledge.combined_memory:
                llm_kwargs["relevant_memory"] = knowledge.combined_memory
            if knowledge.other_people_block:
                llm_kwargs["other_people"] = knowledge.other_people_block
                log.info("agent_other_people_forwarded", participants=len(ctx.other_participants_facts))
        # Arbiter supervision (2026-07-10): the gpt-4.1 router estimated this
        # turn's effort → time budget (ctx.time_budget_s); the runner read timeout
        # is the hard cap so httpx never cuts first, and the arbiter EXTENDS a
        # still-alive runner past the budget instead of failing it over. Only a
        # runner that stops answering /health (or the hard cap) raises
        # RunnerDownError into the failover/degradation path below.
        settings = ctx.deps.settings
        normal_budget_s = float(getattr(settings, "runner_budget_normal_s", 120.0))
        hard_cap_s = float(getattr(settings, "runner_hard_cap_s", 420.0))
        checkpoint_s = float(getattr(settings, "runner_checkpoint_s", 20.0))
        budget_s = ctx.time_budget_s if ctx.time_budget_s is not None else normal_budget_s
        llm_kwargs["timeout_s"] = hard_cap_s
        chat_task = asyncio.create_task(llm_client.chat(ctx.system_prompt, ctx.context, **llm_kwargs))
        ctx.llm_response = await supervise_runner_turn(
            chat_task,
            budget_s=budget_s,
            hard_cap_s=hard_cap_s,
            checkpoint_s=checkpoint_s,
            health_probe=llm_client.health,
            on_budget_exceeded=_notify_retry,
        )
    except Exception as e:
        if isinstance(e, anthropic.BadRequestError):
            failure_class = FailureClass.LLM_BAD_REQUEST
        else:
            failure_class = FailureClass.LLM_FAILED
        elapsed = int((time.monotonic() - llm_start) * 1000)

        # PR-4b slice 2: decide failover by POLICY, not by "any agent failure".
        # A real sibling-persona (ALICE) failover is attempted ONLY when the
        # runner PROCESS is genuinely down (RunnerDownError → runner_down). A
        # persona-turn error (4xx / invalid JSON → persona_error) means Insult's
        # brain is alive but THIS turn broke — failing over would fabricate a
        # 'fake ALICE'; we degrade honestly instead. BadRequestError keeps its
        # own no-failover path (a malformed request ALICE can't fix either).
        alice_failover_enabled = getattr(ctx.deps.settings, "alice_failover_enabled", True)
        decision = decide_failover(e, backend=backend, alice_failover_enabled=alice_failover_enabled)
        log.warning(
            "turn_backend_failed",
            backend=backend,
            failover_reason=decision.reason.value,
            attempt_alice=decision.attempt_alice,
            failure_class=failure_class.value,
            error_type=type(e).__name__,
            error_msg=str(e)[:200],
            elapsed_ms=elapsed,
        )

        if decision.attempt_alice:
            try:
                from personas.insult.core.alice_tool import execute_invoke_alice

                guild_id = str(ctx.guild_id) if ctx.guild_id else None
                fallover_reason = (
                    f"FAILOVER: Insult (persona-runner) no respondió a este turno "
                    f"({type(e).__name__}). Toma tú el turn — responde directamente "
                    f"al último mensaje del usuario en este canal. No estás como "
                    f"compañera complementaria esta vez; estás como única voz que "
                    f"contesta. Mantén tu register, no imites a Insult."
                )
                # ALICE's /invite carries no attachment — she literally cannot
                # see images the user posted. If THIS failed turn had an image,
                # tell her so she degrades honestly instead of fabricating what
                # the picture shows (no-fake-green doctrine).
                if any(b.get("type") == "image" for b in (ctx.attachment_blocks or [])):
                    fallover_reason += (
                        " OJO: el usuario adjuntó una IMAGEN que tú NO puedes ver "
                        "(el failover no te la pasa). NO inventes ni describas lo que "
                        "muestra; sé honesta: dilo y responde solo a lo que sí tienes "
                        "en texto."
                    )
                ok = await execute_invoke_alice(
                    {"reason": fallover_reason},
                    channel_id=ctx.channel_id,
                    guild_id=guild_id,
                    channel_name=ctx.channel_name,
                )
                if ok:
                    # Real ALICE (her own container) accepted the turn (202) —
                    # she will deliver asynchronously; discord-bot sends nothing.
                    log.info(
                        "alice_failover_invoked",
                        channel_id=ctx.channel_id,
                        failover_reason=decision.reason.value,
                    )
                    ctx.delivery_mode = "alice_failover"
                    raise StageStop("alice_failover") from e
                # ALICE's /invite did NOT accept (non-202 / unreachable) → she is
                # NOT really available. Fall through to honest degradation rather
                # than dropping the turn silently.
                log.warning(
                    "alice_failover_unavailable",
                    channel_id=ctx.channel_id,
                    failover_reason=decision.reason.value,
                )
            except StageStop:
                raise
            except Exception:
                log.exception("alice_failover_internal_error")
                # Fall through to honest degradation below.

        # Honest degradation — no persona could serve this turn. NEVER silent,
        # NEVER a fabricated persona voice: an in-character (non-impersonating)
        # operational notice via the reaction-fallback path, plus a distinct,
        # queryable event carrying WHY the turn degraded.
        log.warning(
            "honest_degradation",
            channel_id=ctx.channel_id,
            failover_reason=decision.reason.value,
            alice_failover_enabled=alice_failover_enabled,
            attempt_alice=decision.attempt_alice,
        )

        # The notice text. Default: the static in-character operational message
        # (today's behavior, the conservative fallback). When the gpt-4.1 host
        # degrader is wired (PR-4b slice 3, host_router_enabled) it AUTHORS the
        # notice instead — but the happy path is untouched: this only runs after
        # every persona path is exhausted. A host-router failure is matched BY
        # NAME ("HostRouterError" → ROUTER_ERROR) so this hot path never imports
        # demux_ai, and ANY degrader failure falls back to the static notice —
        # never a fake-green and never silent.
        degradation_text = get_error_response(classify_error(e))
        host_degrader = ctx.deps.host_degrader
        if host_degrader is not None:
            try:
                degraded = await asyncio.wait_for(
                    host_degrader.degrade(reason=decision.reason.value, user_text=ctx.text),
                    HOST_DEGRADE_TIMEOUT_S,
                )
                # A blank result is NOT an exception, so the except below can't
                # catch it — but an empty notice is a degraded signal too: it
                # would send "" to Discord (400 → only a ⏳ reaction), losing the
                # honest message. Adopt the degrader text ONLY when it is
                # non-blank; otherwise keep the static notice. This completes the
                # conservative fallback (blank → static, exception → static).
                if degraded and degraded.strip():
                    degradation_text = degraded
                    log.info(
                        "host_degrade_used",
                        channel_id=ctx.channel_id,
                        failover_reason=decision.reason.value,
                    )
                else:
                    log.warning(
                        "host_degrade_blank",
                        channel_id=ctx.channel_id,
                        failover_reason=decision.reason.value,
                    )
            except Exception as router_exc:
                is_router_error = type(router_exc).__name__ == "HostRouterError"
                log.warning(
                    "host_degrade_failed",
                    channel_id=ctx.channel_id,
                    failover_reason=(FailoverReason.ROUTER_ERROR.value if is_router_error else decision.reason.value),
                    router_error=is_router_error,
                    error_type=type(router_exc).__name__,
                    error_msg=str(router_exc)[:200],
                )
        await send_with_reaction_fallback(ctx.message, degradation_text)
        raise StageFailure(
            stage="call_llm",
            failure_class=failure_class,
            error_type=type(e).__name__,
            error_msg=str(e)[:200],
            elapsed_ms=elapsed,
        ) from e
    finally:
        # Stop the typing keepalive in BOTH the success and failure paths.
        # Cancellation is fire-and-forget — the loop exits on
        # CancelledError. We don't await because there's nothing to wait
        # for and any await here would re-introduce the original failure
        # mode where typing throttles could cancel the turn.
        typing_task.cancel()

    ctx.llm_ms = int((time.monotonic() - llm_start) * 1000)
    log.info(
        "llm_call_complete",
        llm_ms=ctx.llm_ms,
        text_len=len(ctx.llm_response.text),
        model_used=ctx.llm_response.model_used,
        elapsed_ms=ctx.elapsed_ms(),
    )

    # v3.7.2-class safety net: flag when the user clearly asked for a
    # reminder. S4 vetoes the flag if a ``[REMIND:]`` marker was emitted;
    # otherwise the in-character "no agendé recordatorio" tail fires.
    ctx.intent_unattended = detect_reminder_intent(ctx.text)


# --- Stage 11: post-LLM mutations ---


async def interpret_output(
    src: S4OutputInterpretationInput, *, mutation: OutputMutationPort
) -> S4OutputInterpretationResult:
    """S4 Output Interpretation — turn the model's raw text into the deliverable
    response + its side channels (reactions, remembered facts).

    Orchestrates the post-LLM read of the model output: parse the ``[REACT:]`` /
    ``[REMEMBER:]`` / ``[REMIND:]`` / ``[INVITE:]`` markers, run the character
    mutation pipeline (echo-strip, length variation, opener dedup, marker
    stripping), apply the unattended-reminder tail, and harvest inline orphan
    emojis. S4 owns neither persistence nor delivery — it returns the
    parsed/mutated results and the stage applies the side effects."""
    reactions = parse_reactions(src.raw_text)
    remembered_facts = parse_remembers(src.raw_text)
    invite_reason = parse_invite(src.raw_text)
    remind_request = parse_remind(src.raw_text)

    # PR-G OutputMutationPort (capability seam): the guardrailed mutation
    # pipeline that lived inline here (echo-strip, length variation, opener
    # dedup, marker stripping — order + shrink guardrails) moved behind the
    # port; the adapter in insult.composition owns it as internal policy.
    response = await mutation.mutate(
        src.raw_text,
        user_text=src.user_text,
        recent_response_lengths=src.recent_response_lengths,
        recent_openers=src.recent_openers,
    )

    if src.intent_unattended and remind_request is None and response.strip():
        response = response.rstrip() + "\n\n*(no agendé recordatorio formal — si querías uno, dime día y hora.)*"

    # Safety net: if the LLM emitted emojis inline (ignoring the `[REACT:...]`
    # marker), harvest them into the reactions list and strip them from visible
    # text. Opus 4.7 has been observed ignoring the persona's mandatory
    # wrapper rule (v3.9.11 reinforcement didn't fully fix it), so we
    # enforce the behavior in code rather than trust prompt adherence.
    harvested_reactions, response = harvest_orphan_emojis(response, reactions)
    emojis_harvested = len(harvested_reactions) - len(reactions)

    return S4OutputInterpretationResult(
        response_text=response,
        reactions=harvested_reactions,
        remembered_facts=remembered_facts,
        emojis_harvested_inline=emojis_harvested,
        invite_reason=invite_reason,
        remind_request=remind_request,
    )


async def _stage_post_llm_mutations(ctx: TurnCtx) -> None:
    response = ctx.llm_response.text
    ctx.raw_response_text = response
    post_llm_len = len(response)

    ctx.recent_openers = [m["content"].split("\n")[0] for m in ctx.recent if m["role"] == "assistant"][-5:]

    result = await interpret_output(
        S4OutputInterpretationInput(
            raw_text=response,
            user_text=ctx.text,
            recent_openers=ctx.recent_openers,
            recent_response_lengths=ctx.recent_response_lengths,
            intent_unattended=ctx.intent_unattended,
        ),
        mutation=ctx.deps.mutation,
    )

    if result.remembered_facts:
        log.info(
            "remember_markers_parsed",
            count=len(result.remembered_facts),
            user_id=ctx.user_id,
        )
        ctx.deps.spawn_task(
            persist_remembers(ctx.deps.memory, ctx.user_id, result.remembered_facts),
            name=f"persist_remembers:{ctx.user_id}",
        )

    if result.invite_reason:
        log.info(
            "invite_marker_parsed",
            channel_id=ctx.channel_id,
            reason_preview=result.invite_reason[:80],
        )
        ctx.deps.spawn_task(
            fire_invite(
                result.invite_reason,
                channel_id=ctx.channel_id,
                guild_id=str(ctx.guild_id) if ctx.guild_id else None,
                channel_name=ctx.channel_name,
            ),
            name=f"invite_marker:{ctx.channel_id}",
        )

    if result.remind_request is not None:
        ctx.remind_scheduled = True
        log.info(
            "remind_marker_parsed",
            channel_id=ctx.channel_id,
            when_raw=result.remind_request.when_raw[:80],
            description_preview=result.remind_request.description[:80],
            recurring=result.remind_request.recurring,
        )
        ctx.deps.spawn_task(
            fire_remind(
                result.remind_request,
                memory=ctx.deps.memory,
                bot=ctx.deps.bot,
                channel=ctx.message.channel,
                guild_id=str(ctx.guild_id) if ctx.guild_id else None,
                created_by=ctx.user_id,
            ),
            name=f"remind_marker:{ctx.channel_id}",
        )
    elif ctx.intent_unattended:
        log.warning("reminder_intent_unattended", text_preview=ctx.text[:120])

    ctx.reactions = result.reactions
    ctx.response_text = result.response_text

    # Durable research job for the HOST (Insult): the model emitted [RESEARCH: ...].
    # Queue it (the plumbing drain loop runs it via the runner and Insult posts the
    # report back) and strip the marker so only the in-character ack is delivered.
    # persona_id=None marks it Insult's — the gateway's per-persona loops skip it.
    research_prompt = parse_research(ctx.raw_response_text)
    if research_prompt:
        ctx.response_text = strip_research(ctx.response_text)
        try:
            await ctx.deps.memory.save_research_job(
                channel_id=ctx.channel_id,
                guild_id=str(ctx.guild_id) if ctx.guild_id else None,
                created_by=ctx.user_id,
                prompt=research_prompt,
                persona_id=None,
            )
            log.info("research_job_queued", channel_id=ctx.channel_id, prompt_chars=len(research_prompt))
        except Exception:
            log.exception("research_job_queue_failed", channel_id=ctx.channel_id)

    log.info(
        "stage_post_llm_done",
        raw_llm_len=post_llm_len,
        final_text_len=len(result.response_text),
        reactions=ctx.reactions,
        emojis_harvested_inline=result.emojis_harvested_inline,
        elapsed_ms=ctx.elapsed_ms(),
    )


# --- Stage 12: persist assistant message + arc + stances ---


async def assimilate_turn(src: S5TurnAssimilationInput, memory, stance, arc) -> S5TurnAssimilationResult:
    """S5 Turn Assimilation — write the completed turn back into long-term state.

    Orchestrates the terminal write-back: persist the assistant message row,
    advance + upsert the conversational arc, and extract + persist epistemic
    stances when the turn cleared the assertion-density gate. S5 owns the write
    orchestration; the ``memory`` store owns the rows. Behavior is identical to
    the inline stage this replaces — same writes, same order, same gates: the
    message is stored only when the cleaned response is non-blank, the arc is
    upserted on every turn, and stances are extracted only when the response is
    non-empty and ``assertion_density >= 0.4``."""
    clean_response = src.response_text.replace(MESSAGE_DELIMITER, "\n")
    message_stored = False
    if clean_response.strip():
        await store_assistant_message(
            memory,
            src.channel_id,
            src.bot_user_id,
            src.bot_user_name,
            clean_response,
            for_user_id=src.user_id,
            guild_id=src.guild_id,
            channel_name=src.channel_name,
            model_used=src.model_used,
        )
        message_stored = True

    new_arc = arc.advance(
        src.arc_state,
        disclosure_severity=src.disclosure_severity,
        user_state=src.user_state,
        preset_mode=src.preset_mode,
    )
    arc_dict = arc.dump(new_arc)
    await memory.upsert_arc(
        src.channel_id,
        src.user_id,
        arc_dict["phase"],
        arc_dict["phase_since"],
        arc_dict["crisis_depth"],
        arc_dict["recovery_signals"],
        arc_dict["turns_in_phase"],
    )

    stances_stored = 0
    if clean_response and src.assertion_density >= 0.4:
        extraction = stance.derive(clean_response, src.assertion_density, time.time())
        for entry in extraction.entries:
            await memory.store_stance(src.channel_id, src.user_id, entry.topic, entry.position, entry.confidence)
            stances_stored += 1

    return S5TurnAssimilationResult(
        message_stored=message_stored,
        arc_phase=arc_dict["phase"],
        stances_stored=stances_stored,
    )


async def _stage_persist_arc_and_message(ctx: TurnCtx) -> None:
    await assimilate_turn(
        S5TurnAssimilationInput(
            response_text=ctx.response_text,
            channel_id=ctx.channel_id,
            user_id=ctx.user_id,
            guild_id=ctx.guild_id,
            channel_name=ctx.channel_name,
            bot_user_id=str(ctx.deps.bot.user.id),
            bot_user_name=ctx.deps.bot.user.name,
            model_used=ctx.llm_response.model_used or None,
            arc_state=ctx.arc_state,
            disclosure_severity=ctx.disclosure.severity,
            user_state=ctx.flow_analysis.pressure.detected_state.value,
            preset_mode=ctx.preset.mode.value,
            assertion_density=ctx.flow_analysis.epistemic.assertion_density,
        ),
        ctx.deps.memory,
        ctx.deps.stance,
        ctx.deps.arc,
    )


# --- Stage 13: spawn reaction tasks (BACKGROUND) ---


async def _stage_spawn_side_effects(ctx: TurnCtx) -> None:
    if ctx.reactions:
        ctx.deps.spawn_task(add_reactions(ctx.message, ctx.reactions), name="reactions")


# --- Stage 14: ensure non-empty payload (fallback to in-character generic) ---


async def _stage_ensure_payload(ctx: TurnCtx) -> None:
    # Silent-marker recovery — MUST run BEFORE the empty-fallback check.
    # When the LLM emits ONLY a `[REMIND:]` marker with no visible text,
    # stripping the marker leaves an empty body and the user sits staring
    # at silence in the channel where they asked (the v3.7.x "se volvió a
    # morir por pedir un recordatorio" class — the bot wasn't dead, just
    # mute). Inject a short in-character confirmation so the conversation
    # channel acknowledges the scheduled reminder.
    if not ctx.response_text.strip() and ctx.remind_scheduled:
        ctx.response_text = "Ya. Te aviso."
        log.info(
            "silent_remind_marker_recovered",
            injected_text_len=len(ctx.response_text),
        )

    # Empty-response fallback: after silent-marker recovery, if still empty
    # AND no visible side effects (reactions), deliver an in-character
    # generic error.
    if not ctx.response_text.strip() and not ctx.reactions:
        log.warning(
            "empty_response_fallback",
            raw_llm_len=len(ctx.raw_response_text),
            raw_llm_preview=ctx.raw_response_text[:200],
            final_len=len(ctx.response_text),
        )
        ctx.response_text = get_error_response(ErrorType.GENERIC)
        return


# --- Stage 15: delivery ---


async def _stage_deliver(ctx: TurnCtx) -> None:
    has_side_effects = bool(ctx.reactions)
    delivery_start = time.monotonic()
    try:
        await send_response(ctx.message.channel, ctx.response_text, has_side_effects=has_side_effects)
        ctx.delivery_mode = "text"
        log.info(
            "chat_delivery_ok",
            final_text_len=len(ctx.response_text),
            delivery_ms=int((time.monotonic() - delivery_start) * 1000),
            llm_ms=ctx.llm_ms,
        )
    except discord.HTTPException as e:
        failure_class = classify_discord_exception(e)
        elapsed = int((time.monotonic() - delivery_start) * 1000)
        log.error(
            "chat_delivery_failed",
            error_type=type(e).__name__,
            status=getattr(e, "status", None),
            code=getattr(e, "code", None),
            error_msg=str(e)[:200],
            final_text_len=len(ctx.response_text),
            delivery_ms=elapsed,
            failure_class=failure_class.value,
        )
        # Reaction fallback so the user knows something happened.
        try:
            await ctx.message.add_reaction("⏳")
            ctx.delivery_mode = "reaction"
            log.info(
                "discord_send_fallback_reaction_ok",
                channel_id=ctx.channel_id,
                reaction="⏳",
            )
        except Exception:
            ctx.delivery_mode = "silent"
            log.warning("discord_send_silent_giving_up", channel_id=ctx.channel_id)
        raise StageFailure(
            stage="delivery",
            failure_class=failure_class,
            error_type=type(e).__name__,
            error_msg=str(e)[:200],
            elapsed_ms=elapsed,
        ) from e


# --- Stage 16: telemetry (COSMETIC — never blocks) ---


async def _stage_telemetry(ctx: TurnCtx) -> None:
    ctx.deps.policy.assess_adherence(ctx.response_text, ctx.flow_analysis)

    # F2 (2026-05-11): soft-monitor for "competent but flat" replies. We do
    # NOT block, retry, or gate on this — F2 just measures whether the flat-
    # presence problem (the Alex DIF turn) exists at production scale. KQL:
    #   ContainerAppConsoleLogs_CL
    #   | where event_s == "lifelessness_check"
    #   | summarize count() by band_s, preset_s
    # Once we have a week of data we decide F3 retry policy.
    lifelessness = ctx.deps.policy.assess_lifelessness(ctx.response_text, ctx.text)
    log.info(
        "lifelessness_check",
        preset=ctx.preset.display_label,
        preset_reason=ctx.preset.reason,
        score=lifelessness["score"],
        band=lifelessness["band"],
        signals=lifelessness["signals"],
        therapy_speak_hits=lifelessness["therapy_speak_hits"],
        reflection_overlap=lifelessness["reflection_overlap"],
        has_movement_markers=lifelessness["has_movement_markers"],
        has_question=lifelessness["has_question"],
        response_chars=len(ctx.response_text),
        user_id=ctx.user_id,
        channel_id=ctx.channel_id,
    )

    from personas.insult.core.quality import check_quality

    recent_shapes = ctx.deps.expression_history.recent_shapes(ctx.context_key, n=5)
    check_quality(
        ctx.response_text,
        ctx.text,
        recent_shapes,
        agreement_streak=ctx.flow_analysis.agreement_streak,
    )

    from personas.insult.core.metrics import record_message_trace

    record_message_trace(
        {
            "user": ctx.user_name,
            "user_id": ctx.user_id,
            "channel": ctx.channel_id,
            "input": ctx.text[:200],
            "response": ctx.response_text[:300],
            "preset": ctx.preset.display_label,
            "preset_modifiers": [m.value for m in ctx.preset.modifiers],
            "pressure": ctx.flow_analysis.pressure.pressure_level,
            "expression_shape": ctx.flow_analysis.expression.selected_shape.value,
            "expression_flavor": ctx.flow_analysis.expression.selected_flavor.value,
            "epistemic_move": ctx.flow_analysis.epistemic.recommended_move.value,
            "awareness_pattern": ctx.flow_analysis.awareness.detected_pattern.value,
            "reactions": ctx.reactions,
        }
    )


# --- Stage 17: background fact extraction ---


async def _stage_spawn_fact_extraction(ctx: TurnCtx) -> None:
    ch_name = getattr(ctx.message.channel, "name", "")
    # Fact extraction rides the runner's one-shot /v1/judge (OAuth Max) — the
    # automatic safety net that catches facts the model didn't mark with
    # [REMEMBER:]. When the runner isn't wired (judge_client is None) there's
    # no backend to extract with, so skip the spawn entirely; the marker path
    # still works.
    if ctx.deps.judge_client is None:
        log.info("fact_extraction_skipped", reason="no_judge_client")
        return
    ctx.deps.spawn_task(
        extract_user_facts(
            ctx.deps.judge_client,
            ctx.deps.settings.summary_model,
            ctx.deps.memory,
            ctx.deps.bot,
            ctx.user_id,
            ctx.user_name,
            ctx.user_facts,
            ctx.recent,
            ctx.guild_id,
            ch_name,
            extract_facts_fn=ctx.deps.facts.extract_fn,
            merge_facts_fn=ctx.deps.facts.merge_fn,
        ),
        name="fact_extraction",
    )


# --- The wired-up stage list ---
# Order is load-bearing. Each entry documents its criticality (see
# pipeline.Criticality). To add a new stage, append it in the right
# position and decide its criticality based on whether the user sees
# a degraded reply when it fails.


DEFAULT_STAGES: list[Stage] = [
    Stage("bind_identity", Criticality.BUSINESS, _stage_bind_identity),
    Stage("process_attachments", Criticality.BUSINESS, _stage_process_attachments),
    Stage("memory_store", Criticality.BUSINESS, _stage_memory_store),
    Stage("llm_router_cutover", Criticality.BUSINESS, _stage_llm_router_cutover),
    Stage("ensure_not_trivial", Criticality.BUSINESS, _stage_ensure_not_trivial),
    # Typing fires ONLY after routing + triviality gates — so Insult never shows
    # a typing indicator for a turn the DeMux hands to a sibling (the 2026-07-11
    # smell: Insult "typing" during the router's deliberation on an implicit turn
    # that resolves to ALICE). A sibling-routed or trivial turn StageStops above
    # and this never runs.
    Stage("emit_typing", Criticality.BACKGROUND, _stage_emit_typing),
    Stage("build_context", Criticality.BUSINESS, _stage_build_context),
    Stage("load_facts", Criticality.BUSINESS, _stage_load_facts),
    Stage("scan_disclosure", Criticality.BUSINESS, _stage_scan_disclosure),
    Stage("classify_and_analyze", Criticality.BUSINESS, _stage_classify_and_analyze),
    Stage("call_llm", Criticality.BUSINESS, _stage_call_llm),
    Stage("post_llm_mutations", Criticality.BUSINESS, _stage_post_llm_mutations),
    Stage(
        "persist_arc_and_message",
        Criticality.BUSINESS,
        _stage_persist_arc_and_message,
    ),
    Stage("spawn_side_effects", Criticality.BUSINESS, _stage_spawn_side_effects),
    Stage("ensure_payload", Criticality.BUSINESS, _stage_ensure_payload),
    Stage("deliver", Criticality.BUSINESS, _stage_deliver),
    Stage("telemetry", Criticality.COSMETIC, _stage_telemetry),
    Stage(
        "spawn_fact_extraction",
        Criticality.BACKGROUND,
        _stage_spawn_fact_extraction,
    ),
]
