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

from khimeras_shared.corpus import (
    animal_liberation_guidance,
    animal_tactics_guidance,
    film_criticism_guidance,
)
from personas.insult.cogs.chat._failure import (
    Criticality,
    FailoverReason,
    FailureClass,
    StageFailure,
    StageStop,
    classify_discord_exception,
    decide_failover,
    send_with_reaction_fallback,
    spawn_typing_indicator,
    spawn_typing_keepalive,
)
from personas.insult.cogs.chat.attachments import process_attachments
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
from personas.insult.cogs.chat.reactions import add_reactions, harvest_orphan_emojis, parse_reactions
from personas.insult.cogs.chat.remembers import parse_remembers, persist_remembers
from personas.insult.cogs.chat.tasks import extract_user_facts
from personas.insult.cogs.chat.tools import execute_reminder_call, execute_tool_calls
from personas.insult.core.contracts import PresetModifier
from personas.insult.core.delivery import MESSAGE_DELIMITER, send_response
from personas.insult.core.errors import ErrorType, classify_error, get_error_response
from personas.insult.core.llm import WEB_SEARCH_TOOL
from personas.insult.core.reminders import detect_reminder_intent
from personas.insult.core.routing import ModelTier, select_model
from personas.insult.core.triviality import is_trivial

log = structlog.get_logger()


_REMINDER_TOOL_NAMES = {"create_reminder", "list_reminders", "cancel_reminder"}

# Upper bound for the host degrader (gpt-4.1) in the honest-degradation tail. The
# notice is a 2-sentence completion and the static fallback is instant, so the
# already-failed turn must never hang waiting on it. A timeout falls into the
# conservative fallback below (TimeoutError → static notice), same as any other
# degrader failure.
HOST_DEGRADE_TIMEOUT_S = 12.0


# --- Stage 01: identity binding (no I/O, just derive fields from message) ---


_VULTUR_PREFIXES = ("@vultur ", "~vultur ")


async def _run_llm_shadow_decision(
    llm_shadow_route: Any,
    raw_text: str,
    current_target: str,
    guild_id: str | None,
    channel_id: str,
) -> None:
    """Run the gpt-4.1 LLM shadow route (HOST 5/6 slice A.2) and LOG its decision
    next to where the turn ACTUALLY went. Runs as a BACKGROUND task so the Azure
    call never delays the user's reply (no observable behavior change, no cutover).
    Wrapped: a shadow fault logs ``llm_shadow_router_failed`` and is invisible to
    the turn — it must never raise into the pipeline."""
    try:
        decision = await llm_shadow_route(raw_text)
        log.info(
            "llm_shadow_router_decision",
            current_target=current_target,
            llm_shadow_target=decision.target,
            llm_shadow_reason=decision.reason,
            llm_diverged=decision.target != current_target,
            guild_id=guild_id,
            channel_id=channel_id,
            route_input_len=len(raw_text),
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

    # Multi-persona routing: @vultur / ~vultur prefix → route to Vultur persona.
    # Keep the RAW text (pre-strip) so the shadow router below sees the same input
    # the live rule did — otherwise it would never observe the prefix and falsely
    # diverge on every Vultur turn.
    raw_text = ctx.text
    lowered = ctx.text.lower()
    for prefix in _VULTUR_PREFIXES:
        if lowered.startswith(prefix):
            ctx.persona_id = "vultur"
            ctx.text = ctx.text[len(prefix) :].strip()
            break

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

    # HOST 5/6 slice A — SHADOW router. Compute what the demux host WOULD route to
    # and log it next to where the turn actually goes; NEVER change ctx.persona_id
    # (no cutover, no observable behavior change). Wrapped so a shadow fault is
    # invisible to the turn — the shadow must never break the happy path.
    shadow_route = getattr(ctx.deps, "shadow_route", None)
    if shadow_route is not None:
        try:
            current_target = ctx.persona_id or "insult"
            decision = shadow_route(raw_text)
            log.info(
                "shadow_router_decision",
                current_target=current_target,
                shadow_target=decision.target,
                shadow_reason=decision.reason,
                diverged=decision.target != current_target,
                guild_id=ctx.guild_id,
                explicit_vultur_trigger=decision.reason == "vultur_prefix",
                route_input_len=len(raw_text),
            )
        except Exception:
            log.exception("shadow_router_failed")

    # HOST 5/6 slice A.2 — gpt-4.1 LLM SHADOW router. The deterministic shadow
    # above mirrors the live @vultur rule by construction, so it can never diverge;
    # this one asks the host BRAIN to pick a target INDEPENDENTLY, so a genuine
    # divergence is finally observable. Spend-gated (llm_shadow_route is None unless
    # llm_shadow_router_enabled) and run OFF the critical path via spawn_task — the
    # Azure call must never delay the reply. Behavior-neutral: never changes routing.
    llm_shadow_route = getattr(ctx.deps, "llm_shadow_route", None)
    if llm_shadow_route is not None:
        current_target = ctx.persona_id or "insult"
        ctx.deps.spawn_task(
            _run_llm_shadow_decision(llm_shadow_route, raw_text, current_target, ctx.guild_id, ctx.channel_id),
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
    # Image summarization was removed: /v1/judge is text-only (can't see images),
    # and the agent runner has native vision in the turn itself + the workspace
    # renderer writes its image-describing reply to markdown — so the future-turn
    # trace the old [Imagen: ...] annotation provided is already covered. The
    # raw user text is what we persist.
    ctx.text_for_memory = ctx.text

    await store_user_message(
        ctx.deps.memory,
        ctx.channel_id,
        ctx.user_id,
        ctx.user_name,
        ctx.text_for_memory,
        ctx.guild_id,
        ctx.channel_name,
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


# --- Stage 09: tools + model routing ---


async def _stage_resolve_tools_and_model(ctx: TurnCtx) -> None:
    ctx.tools = [*ctx.deps.all_tools, WEB_SEARCH_TOOL]
    force_tool = PresetModifier.ACTION_INTENT in ctx.preset.modifiers
    ctx.tool_choice = {"type": "any"} if force_tool else None

    if getattr(ctx.deps.settings, "model_router_enabled", False):
        ctx.model_choice = select_model(
            ctx.preset,
            ctx.flow_analysis,
            ctx.disclosure.severity,
            casual_model=ctx.deps.settings.casual_model,
            depth_model=ctx.deps.settings.llm_model,
            crisis_model=ctx.deps.settings.crisis_model,
            opus_24h_count=ctx.deps.opus_budget.count(ctx.user_id),
            opus_24h_cap=ctx.deps.opus_budget.cap,
        )
        log.info(
            "model_routed",
            tier=ctx.model_choice.tier.value,
            primary=ctx.model_choice.primary,
            fallback=ctx.model_choice.fallback,
            reason=ctx.model_choice.reason,
            preset=ctx.preset.display_label,
            disclosure_severity=ctx.disclosure.severity,
            user_id=ctx.user_id,
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
        tools=[t.get("name", t.get("type", "?")) for t in ctx.tools],
        tool_choice=(ctx.tool_choice or {}).get("type"),
        primary_model=ctx.model_choice.primary if ctx.model_choice else ctx.deps.settings.llm_model,
        fallback_model=ctx.model_choice.fallback if ctx.model_choice else None,
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
        llm_kwargs: dict[str, Any] = {
            "tools": ctx.tools,
            "tool_choice": ctx.tool_choice,
            "on_timeout": _notify_retry,
        }
        if ctx.model_choice is not None:
            llm_kwargs["model"] = ctx.model_choice.primary
            llm_kwargs["fallback_model"] = ctx.model_choice.fallback
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
        ctx.llm_response = await llm_client.chat(ctx.system_prompt, ctx.context, **llm_kwargs)
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
                    f"FAILOVER: Insult (insult-runner) no respondió a este turno "
                    f"({type(e).__name__}). Toma tú el turn — responde directamente "
                    f"al último mensaje del usuario en este canal. No estás como "
                    f"compañera complementaria esta vez; estás como única voz que "
                    f"contesta. Mantén tu register, no imites a Insult."
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
    tool_names = [tc.name for tc in ctx.llm_response.tool_calls]
    log.info(
        "llm_call_complete",
        llm_ms=ctx.llm_ms,
        text_len=len(ctx.llm_response.text),
        tool_calls=len(ctx.llm_response.tool_calls),
        tool_names=tool_names,
        model_used=ctx.llm_response.model_used,
        elapsed_ms=ctx.elapsed_ms(),
    )

    # v3.8.3 no-op-tool-only retry: when force_tool was True and the model
    # responded with ONLY `get_channel_info` and no text, it picked the
    # lowest-impact tool just to satisfy tool_choice="any". The user gets
    # silence (or a generic error fallback). Retry once without forced
    # tools so the model actually engages with the message.
    is_force_tool = ctx.tool_choice == {"type": "any"}
    only_no_op = bool(tool_names) and set(tool_names) == {"get_channel_info"}
    if is_force_tool and only_no_op and not ctx.llm_response.text.strip():
        log.warning(
            "llm_no_op_tool_retry",
            original_tool_names=tool_names,
            reason="forced_tool_choice_picked_get_channel_info_only",
        )
        retry_tools = [t for t in ctx.tools if t.get("name") != "get_channel_info"]
        retry_kwargs: dict[str, Any] = {
            "tools": retry_tools,
            "tool_choice": None,
            "on_timeout": _notify_retry,
        }
        if ctx.model_choice is not None:
            retry_kwargs["model"] = ctx.model_choice.primary
            retry_kwargs["fallback_model"] = ctx.model_choice.fallback
        try:
            if backend == "agent_runner":
                retry_kwargs["channel_id"] = ctx.channel_id
                retry_kwargs["user_id"] = ctx.user_id
            ctx.llm_response = await llm_client.chat(ctx.system_prompt, ctx.context, **retry_kwargs)
            tool_names = [tc.name for tc in ctx.llm_response.tool_calls]
            log.info(
                "llm_no_op_tool_retry_complete",
                text_len=len(ctx.llm_response.text),
                tool_calls=len(ctx.llm_response.tool_calls),
                tool_names=tool_names,
            )
        except Exception as e:
            log.warning(
                "llm_no_op_tool_retry_failed",
                error_type=type(e).__name__,
                error_msg=str(e)[:200],
            )
            # Keep the original (empty-text) response — _stage_ensure_payload
            # will fall back to the generic in-character error.

    # v3.7.2-class safety net: warn if user clearly asked for a reminder
    # but the LLM did not call ``create_reminder``.
    ctx.intent_unattended = "create_reminder" not in tool_names and detect_reminder_intent(ctx.text)
    if ctx.intent_unattended:
        log.warning("reminder_intent_unattended", text_preview=ctx.text[:120], tool_names=tool_names)

    # Opus budget: only record on success so transient failures don't burn the cap.
    if ctx.model_choice is not None and ctx.model_choice.tier == ModelTier.CRISIS:
        ctx.deps.opus_budget.record(ctx.user_id)


# --- Stage 11: post-LLM mutations ---


async def interpret_output(
    src: S4OutputInterpretationInput, *, mutation: OutputMutationPort
) -> S4OutputInterpretationResult:
    """S4 Output Interpretation — turn the model's raw text into the deliverable
    response + its side channels (reactions, remembered facts).

    Orchestrates the post-LLM read of the model output: parse the ``[REACT:]`` /
    ``[REMEMBER:]`` markers, run the character mutation pipeline (echo-strip,
    length variation, opener dedup, marker stripping), apply the unattended-
    reminder tail, and harvest inline orphan emojis. S4 owns neither persistence
    nor delivery — it returns the parsed/mutated results and the stage applies
    the side effects. Behavior is identical to the inline block this replaces
    (same parsers, same mutation order, same harvest)."""
    reactions = parse_reactions(src.raw_text)
    remembered_facts = parse_remembers(src.raw_text)

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

    if src.intent_unattended and response.strip():
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

    ctx.reactions = result.reactions
    ctx.response_text = result.response_text

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


# --- Stage 13: spawn reaction/tool tasks (BACKGROUND) ---


async def _stage_spawn_side_effects(ctx: TurnCtx) -> None:
    if ctx.reactions:
        ctx.deps.spawn_task(add_reactions(ctx.message, ctx.reactions), name="reactions")

    if ctx.llm_response.tool_calls:
        reminder_calls = [tc for tc in ctx.llm_response.tool_calls if tc.name in _REMINDER_TOOL_NAMES]
        other_calls = [tc for tc in ctx.llm_response.tool_calls if tc.name not in _REMINDER_TOOL_NAMES]
        for rc in reminder_calls:
            ctx.deps.spawn_task(
                execute_reminder_call(ctx.message, rc, ctx.deps.memory, ctx.deps.bot),
                name=f"reminder:{rc.name}",
            )
        if other_calls and ctx.message.guild:
            ctx.deps.spawn_task(
                execute_tool_calls(
                    ctx.message,
                    other_calls,
                    memory=ctx.deps.memory,
                    judge=ctx.deps.judge_client,
                    settings=ctx.deps.settings,
                    spawn_task=ctx.deps.spawn_task,
                ),
                name=f"tool_calls:{','.join(tc.name for tc in other_calls)}",
            )


# --- Stage 14: ensure non-empty payload (fallback to in-character generic) ---

# Tools whose handler does NOT post a user-visible message in the channel
# of origin. When the LLM emits one of these alone with no text body, the
# turn would deliver silence — so the empty-response fallback must fire.
# `get_channel_info` joined this set in v3.8.3 after the no-op tool dump
# regression; create_reminder / cancel_reminder have always been silent.
_NON_VISIBLE_TOOL_NAMES = {"get_channel_info", "create_reminder", "cancel_reminder"}


async def _stage_ensure_payload(ctx: TurnCtx) -> None:
    # Silent-tool-call recovery (v3.8.0) — MUST run BEFORE the empty-fallback
    # check. When the LLM fires `create_reminder` or `cancel_reminder` without
    # writing any user-facing text, the delivery stage skips entirely
    # (has_side_effects=True + empty body → `delivery_skipped`) and the
    # user sees nothing in the channel where they asked. The reminder
    # is saved, the side-channel #insult-reminders post fires, but the
    # author still sits staring at silence and re-asks. v3.7.x logs
    # showed this manifesting as "se volvió a morir por pedir un
    # recordatorio" — the bot wasn't dead, just mute. Inject a short
    # in-character confirmation so the conversation channel acknowledges
    # the action. Other tool calls (`list_reminders`, channel ops) already
    # post their own visible artifact in `tools.py` so they don't need it.
    if not ctx.response_text.strip() and ctx.llm_response.tool_calls:
        silent_tool_names = {"create_reminder", "cancel_reminder"}
        silent_tools = [tc.name for tc in ctx.llm_response.tool_calls if tc.name in silent_tool_names]
        if silent_tools:
            confirmations = {
                "create_reminder": "Ya. Te aviso.",
                "cancel_reminder": "Cancelado.",
            }
            ctx.response_text = confirmations[silent_tools[0]]
            log.info(
                "silent_tool_call_recovered",
                tool=silent_tools[0],
                injected_text_len=len(ctx.response_text),
            )

    # Empty-response fallback: after silent-tool recovery, if still empty
    # AND no visible side effects, deliver an in-character generic error.
    # `get_channel_info` is in `_NON_VISIBLE_TOOL_NAMES` since v3.8.4 — when
    # it's the only tool call with no text, the no-op-retry in
    # `_stage_call_llm` already produced a real response or this falls back.
    visible_tool_calls = [tc for tc in ctx.llm_response.tool_calls if tc.name not in _NON_VISIBLE_TOOL_NAMES]
    has_side_effects = bool(ctx.reactions or visible_tool_calls)
    if not ctx.response_text.strip() and not has_side_effects:
        log.warning(
            "empty_response_fallback",
            raw_llm_len=len(ctx.raw_response_text),
            raw_llm_preview=ctx.raw_response_text[:200],
            final_len=len(ctx.response_text),
            tool_calls=len(ctx.llm_response.tool_calls),
        )
        ctx.response_text = get_error_response(ErrorType.GENERIC)
        return


# --- Stage 15: delivery ---


async def _stage_deliver(ctx: TurnCtx) -> None:
    visible_tool_calls = [tc for tc in ctx.llm_response.tool_calls if tc.name not in _NON_VISIBLE_TOOL_NAMES]
    has_side_effects = bool(ctx.reactions or visible_tool_calls)
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
            "tools": [tc.name for tc in ctx.llm_response.tool_calls] if ctx.llm_response.tool_calls else [],
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
    Stage("emit_typing", Criticality.BACKGROUND, _stage_emit_typing),
    Stage("process_attachments", Criticality.BUSINESS, _stage_process_attachments),
    Stage("memory_store", Criticality.BUSINESS, _stage_memory_store),
    Stage("ensure_not_trivial", Criticality.BUSINESS, _stage_ensure_not_trivial),
    Stage("build_context", Criticality.BUSINESS, _stage_build_context),
    Stage("load_facts", Criticality.BUSINESS, _stage_load_facts),
    Stage("scan_disclosure", Criticality.BUSINESS, _stage_scan_disclosure),
    Stage("classify_and_analyze", Criticality.BUSINESS, _stage_classify_and_analyze),
    Stage(
        "resolve_tools_and_model",
        Criticality.BUSINESS,
        _stage_resolve_tools_and_model,
    ),
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


# We keep ``spawn_typing_indicator`` import alive even though emit_typing
# is now a stage — other callers (e.g. CLI smoke tests) can still spawn
# typing without going through the pipeline.
_ = spawn_typing_indicator
