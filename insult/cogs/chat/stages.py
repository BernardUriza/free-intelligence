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

from insult.cogs.chat._failure import (
    Criticality,
    FailureClass,
    StageFailure,
    StageStop,
    classify_discord_exception,
    send_with_reaction_fallback,
    spawn_typing_indicator,
)
from insult.cogs.chat.context import (
    build_context,
    load_facts_smart,
    load_other_participants_facts,
    load_server_pulse,
    store_assistant_message,
    store_user_message,
    summarize_user_images_into_text,
    update_style_profile,
)
from insult.cogs.chat.pipeline import Stage, TurnCtx
from insult.cogs.chat.tasks import extract_user_facts
from insult.cogs.chat.tools import execute_reminder_call, execute_tool_calls
from insult.core.arc_tracker import ArcState, arc_from_dict, arc_to_dict, build_arc_prompt, update_arc
from insult.core.attachments import process_attachments
from insult.core.character import (
    MutationStage,
    build_adaptive_prompt,
    compose_extra_layers,
    deduplicate_opener,
    enforce_length_variation,
    preserve_react_markers,
    strip_echoed_quotes,
)
from insult.core.character import (
    run_pipeline as run_character_pipeline,
)
from insult.core.delivery import MESSAGE_DELIMITER, send_response
from insult.core.disclosure import scan_disclosure
from insult.core.errors import ErrorType, classify_error, get_error_response
from insult.core.facts import build_facts_prompt
from insult.core.flows import analyze_flows, build_flow_prompt, detect_lifelessness, validate_flow_adherence
from insult.core.llm import WEB_SEARCH_TOOL
from insult.core.presets import PresetModifier
from insult.core.presets_llm import classify_preset_llm
from insult.core.reactions import add_reactions, parse_reactions, strip_reactions
from insult.core.reminders import detect_reminder_intent
from insult.core.routing import ModelTier, select_model
from insult.core.stance_log import build_stance_prompt
from insult.core.triviality import is_trivial

log = structlog.get_logger()


_REMINDER_TOOL_NAMES = {"create_reminder", "list_reminders", "cancel_reminder"}


# --- Stage 01: identity binding (no I/O, just derive fields from message) ---


async def _stage_bind_identity(ctx: TurnCtx) -> None:
    msg = ctx.message
    ctx.channel_id = str(msg.channel.id)
    ctx.user_id = str(msg.author.id)
    ctx.user_name = msg.author.display_name
    ctx.guild_id = str(msg.guild.id) if msg.guild else None
    ctx.channel_name = msg.channel.name if hasattr(msg.channel, "name") else None
    ctx.context_key = f"{ctx.channel_id}:{ctx.user_id}"

    log.info(
        "chat_turn_start",
        text_len=len(ctx.text),
        text_preview=ctx.text[:120],
        attachments=len(msg.attachments),
        is_voice=bool(msg.flags.voice),
        guild_id=ctx.guild_id,
        channel_name=ctx.channel_name,
    )


# --- Stage 02: emit typing (BACKGROUND — never blocks LLM) ---


async def _stage_emit_typing(ctx: TurnCtx) -> None:
    """Fire-and-forget typing indicator. Replaces the
    ``async with channel.typing():`` that caused the 2026-05-08T23:59
    outage by 429-ing inside ``__aenter__``."""
    # Registered as BACKGROUND so the pipeline does not await it.
    # Imported here so the helper is co-located with the rest of
    # _failure.py's surface area.
    from insult.cogs.chat._failure import emit_typing_safe

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
    image_blocks = [b for b in ctx.attachment_blocks if isinstance(b, dict) and b.get("type") == "image"]
    ctx.text_for_memory = await summarize_user_images_into_text(
        image_blocks, ctx.llm, ctx.settings.summary_model, ctx.text
    )

    await store_user_message(
        ctx.memory,
        ctx.channel_id,
        ctx.user_id,
        ctx.user_name,
        ctx.text_for_memory,
        ctx.guild_id,
        ctx.channel_name,
    )

    # Style profile BEFORE the trivial gate so short-message users still
    # accumulate signal for language/formality/emoji detection.
    ctx.profile = await update_style_profile(ctx.memory, ctx.user_id, ctx.text)

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
    context, recent = await build_context(ctx.memory, ctx.settings, ctx.channel_id, ctx.text, ctx.attachment_blocks)
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
    ctx.user_facts = await load_facts_smart(ctx.memory, ctx.user_id, ctx.text)
    log.info("stage_facts_loaded", facts_count=len(ctx.user_facts), elapsed_ms=ctx.elapsed_ms())
    ctx.other_participants_facts = await load_other_participants_facts(ctx.memory, ctx.channel_id, ctx.user_id)
    ctx.server_pulse = await load_server_pulse(ctx.memory, ctx.message, ctx.channel_id, ctx.text)

    # v3.8.0: pull the latest SerenityOps snapshot for the author. Cheap
    # single-row lookup keyed by user_id — the per-user index makes this an
    # index scan even at scale. None → user hasn't synced, prompt omits the
    # block entirely (the omission carries information too: Insult shouldn't
    # claim to "have your CV" when no row exists).
    try:
        ctx.serenityops_snapshot = await ctx.memory.get_latest_serenityops_snapshot(ctx.user_id)
    except Exception:
        log.exception("serenityops_snapshot_load_failed", user_id=ctx.user_id)
        ctx.serenityops_snapshot = None

    # Launch the LLM preset classifier as a background task so its Haiku
    # latency overlaps with the remaining pre-LLM stages (disclosure scan,
    # arc load, flow analysis setup). `_stage_classify_and_analyze` awaits
    # the task with a timeout and falls back to the regex classifier on
    # failure. Disabled-by-flag path leaves ctx.preset_task as None and
    # the awaiter goes straight to regex.
    if getattr(ctx.settings, "preset_classifier_llm_enabled", False):
        ctx.preset_task = asyncio.create_task(
            classify_preset_llm(
                ctx.text,
                ctx.recent,
                ctx.user_facts,
                ctx.llm,
                model=getattr(ctx.settings, "preset_classifier_model", "claude-haiku-4-5-20251001"),
            )
        )


# --- Stage 07: disclosure scan + arc state ---


async def _stage_scan_disclosure(ctx: TurnCtx) -> None:
    ctx.disclosure = scan_disclosure(ctx.text)
    if ctx.disclosure.detected:
        await ctx.memory.store_disclosure(
            ctx.channel_id,
            ctx.user_id,
            ctx.disclosure.category,
            ctx.disclosure.severity,
            _json.dumps(ctx.disclosure.signals),
            ctx.text[:200],
        )
    arc_data = await ctx.memory.get_arc(ctx.channel_id, ctx.user_id)
    ctx.arc_state = arc_from_dict(arc_data) if arc_data else ArcState()

    ctx.recent_response_lengths = [len(m.get("content", "").split()) for m in ctx.recent if m["role"] == "assistant"][
        -5:
    ]


# --- Stage 08: preset + flows ---


async def _stage_classify_and_analyze(ctx: TurnCtx) -> None:
    # Resolve the LLM classifier task launched in stage 06 (if enabled).
    # Strategy: await with a hard timeout. On timeout / API error / invalid
    # JSON, the regex classifier (which still runs inside build_adaptive_prompt
    # when preset is None) becomes the result. Telemetry logs source +
    # divergence so we can measure how often the LLM agrees with regex.
    llm_preset = None
    classifier_source = "regex"
    classifier_ms = 0
    if ctx.preset_task is not None:
        classifier_start = time.monotonic()
        timeout_s = float(getattr(ctx.settings, "preset_classifier_timeout_ms", 1500)) / 1000.0
        try:
            llm_preset = await asyncio.wait_for(ctx.preset_task, timeout=timeout_s)
        except TimeoutError:
            ctx.preset_task.cancel()
            log.warning("preset_llm_timeout_fallback", timeout_s=timeout_s)
            llm_preset = None
        except Exception:
            log.exception("preset_llm_task_failed_fallback")
            llm_preset = None
        classifier_ms = int((time.monotonic() - classifier_start) * 1000)
        if llm_preset is not None:
            classifier_source = "llm"

    # Shadow-run the regex classifier ALWAYS so we can detect LLM/regex
    # divergence (F5 hybrid recommendation). Cost is ~0.1ms vs the Haiku
    # 300ms — trivial. The regex is also the fallback when llm_preset is None.
    from insult.core.presets import classify_preset as _classify_regex

    regex_preset = _classify_regex(ctx.text, ctx.recent, ctx.user_facts)
    effective_preset = llm_preset if llm_preset is not None else regex_preset

    if llm_preset is not None and llm_preset.mode != regex_preset.mode:
        log.info(
            "preset_llm_regex_divergence",
            llm_mode=llm_preset.mode.value,
            regex_mode=regex_preset.mode.value,
            llm_reason=llm_preset.reason,
            regex_reason=regex_preset.reason,
            llm_modifiers=[m.value for m in llm_preset.modifiers],
            regex_modifiers=[m.value for m in regex_preset.modifiers],
        )

    system_prompt, preset = build_adaptive_prompt(
        ctx.settings.system_prompt,
        ctx.profile,
        len(ctx.context),
        preset=effective_preset,
        current_message=ctx.text,
        recent_messages=ctx.recent,
        user_facts=ctx.user_facts,
        server_pulse=ctx.server_pulse,
        recent_response_lengths=ctx.recent_response_lengths,
    )
    ctx.preset = preset
    log.info(
        "preset_classified",
        preset=preset.display_label,
        preset_internal=preset.mode.value,
        modifiers=[m.value for m in preset.modifiers],
        classifier_source=classifier_source,
        classifier_ms=classifier_ms,
        disclosure_severity=ctx.disclosure.severity,
        disclosure_category=ctx.disclosure.category,
        arc_phase=ctx.arc_state.phase,
        elapsed_ms=ctx.elapsed_ms(),
    )

    ctx.flow_analysis = analyze_flows(ctx.text, ctx.recent, preset, ctx.expression_history, ctx.context_key)
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

    ctx.stances = await ctx.memory.get_stances(ctx.channel_id, ctx.user_id, limit=5)

    ctx.system_prompt = compose_extra_layers(
        system_prompt,
        flow_prompt=build_flow_prompt(ctx.flow_analysis),
        arc_prompt=build_arc_prompt(ctx.arc_state),
        stance_prompt=build_stance_prompt(ctx.stances) if ctx.stances else "",
        facts_prompt=build_facts_prompt(ctx.user_name, ctx.user_facts),
        other_participants_facts=ctx.other_participants_facts,
        serenityops_snapshot=ctx.serenityops_snapshot,
        serenityops_user_name=ctx.user_name,
    )

    if ctx.profile and ctx.profile.is_confident:
        log.info(
            "style_adapted",
            user_id=ctx.user_id,
            preset=preset.display_label,
            preset_modifiers=[m.value for m in preset.modifiers],
            language=ctx.profile.detected_language,
            formality=round(ctx.profile.formality, 2),
            technical=round(ctx.profile.technical_level, 2),
            verbosity=round(ctx.profile.avg_word_count, 1),
        )


# --- Stage 09: tools + model routing ---


async def _stage_resolve_tools_and_model(ctx: TurnCtx) -> None:
    ctx.tools = [*ctx.all_tools, WEB_SEARCH_TOOL]
    force_tool = PresetModifier.ACTION_INTENT in ctx.preset.modifiers
    ctx.tool_choice = {"type": "any"} if force_tool else None

    if getattr(ctx.settings, "model_router_enabled", False):
        ctx.model_choice = select_model(
            ctx.preset,
            ctx.flow_analysis,
            ctx.disclosure.severity,
            casual_model=ctx.settings.casual_model,
            depth_model=ctx.settings.llm_model,
            crisis_model=ctx.settings.crisis_model,
            opus_24h_count=ctx.opus_budget.count(ctx.user_id),
            opus_24h_cap=ctx.opus_budget.cap,
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
        primary_model=ctx.model_choice.primary if ctx.model_choice else ctx.settings.llm_model,
        fallback_model=ctx.model_choice.fallback if ctx.model_choice else None,
    )
    try:
        llm_kwargs: dict[str, Any] = {
            "tools": ctx.tools,
            "tool_choice": ctx.tool_choice,
            "on_timeout": _notify_retry,
        }
        if ctx.model_choice is not None:
            llm_kwargs["model"] = ctx.model_choice.primary
            llm_kwargs["fallback_model"] = ctx.model_choice.fallback
        ctx.llm_response = await ctx.llm.chat(ctx.system_prompt, ctx.context, **llm_kwargs)
    except Exception as e:
        if isinstance(e, anthropic.BadRequestError):
            failure_class = FailureClass.LLM_BAD_REQUEST
        else:
            failure_class = FailureClass.LLM_FAILED
        elapsed = int((time.monotonic() - llm_start) * 1000)
        # In-character user notice via the reaction-fallback path so a
        # rate-limited channel still produces *some* signal.
        await send_with_reaction_fallback(ctx.message, get_error_response(classify_error(e)))
        raise StageFailure(
            stage="call_llm",
            failure_class=failure_class,
            error_type=type(e).__name__,
            error_msg=str(e)[:200],
            elapsed_ms=elapsed,
        ) from e

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

    # v3.7.2-class safety net: warn if user clearly asked for a reminder
    # but the LLM did not call ``create_reminder``.
    ctx.intent_unattended = "create_reminder" not in tool_names and detect_reminder_intent(ctx.text)
    if ctx.intent_unattended:
        log.warning("reminder_intent_unattended", text_preview=ctx.text[:120], tool_names=tool_names)

    # Opus budget: only record on success so transient failures don't burn the cap.
    if ctx.model_choice is not None and ctx.model_choice.tier == ModelTier.CRISIS:
        ctx.opus_budget.record(ctx.user_id)


# --- Stage 11: post-LLM mutations ---


async def _stage_post_llm_mutations(ctx: TurnCtx) -> None:
    response = ctx.llm_response.text
    ctx.raw_response_text = response
    post_llm_len = len(response)

    ctx.reactions = parse_reactions(response)
    ctx.recent_openers = [m["content"].split("\n")[0] for m in ctx.recent if m["role"] == "assistant"][-5:]

    response = await run_character_pipeline(
        [
            MutationStage(
                name="strip_echoed_quotes",
                apply=lambda t, _ctx, _user_text=ctx.text: strip_echoed_quotes(t, _user_text),
                max_shrink_pct=0.30,
                on_violation="skip_stage",
            ),
            MutationStage(
                name="enforce_length_variation",
                apply=lambda t, _ctx, _lens=ctx.recent_response_lengths: enforce_length_variation(t, _lens),
                max_shrink_pct=0.50,
                on_violation="skip_stage",
            ),
            MutationStage(
                name="deduplicate_opener",
                apply=lambda t, _ctx, _openers=ctx.recent_openers: deduplicate_opener(t, _openers),
                max_shrink_pct=0.30,
                must_preserve=[preserve_react_markers],
                on_violation="skip_stage",
            ),
            MutationStage(
                name="strip_reactions",
                apply=lambda t, _ctx: strip_reactions(t),
                max_shrink_pct=None,
                on_violation="skip_stage",
            ),
        ],
        response,
        ctx={},
    )

    if ctx.intent_unattended and response.strip():
        response = response.rstrip() + "\n\n*(no agendé recordatorio formal — si querías uno, dime día y hora.)*"

    log.info(
        "stage_post_llm_done",
        raw_llm_len=post_llm_len,
        final_text_len=len(response),
        reactions=ctx.reactions,
        elapsed_ms=ctx.elapsed_ms(),
    )

    ctx.response_text = response


# --- Stage 12: persist assistant message + arc + stances ---


async def _stage_persist_arc_and_message(ctx: TurnCtx) -> None:
    clean_response = ctx.response_text.replace(MESSAGE_DELIMITER, "\n")
    if clean_response.strip():
        await store_assistant_message(
            ctx.memory,
            ctx.channel_id,
            str(ctx.bot.user.id),
            ctx.bot.user.name,
            clean_response,
            for_user_id=ctx.user_id,
            guild_id=ctx.guild_id,
            channel_name=ctx.channel_name,
            model_used=ctx.llm_response.model_used or None,
        )

    new_arc = update_arc(
        ctx.arc_state,
        disclosure_severity=ctx.disclosure.severity,
        user_state=ctx.flow_analysis.pressure.detected_state.value,
        preset_mode=ctx.preset.mode.value,
    )
    arc_dict = arc_to_dict(new_arc)
    await ctx.memory.upsert_arc(
        ctx.channel_id,
        ctx.user_id,
        arc_dict["phase"],
        arc_dict["phase_since"],
        arc_dict["crisis_depth"],
        arc_dict["recovery_signals"],
        arc_dict["turns_in_phase"],
    )

    if clean_response and ctx.flow_analysis.epistemic.assertion_density >= 0.4:
        from insult.core.stance_log import extract_stances

        extraction = extract_stances(clean_response, ctx.flow_analysis.epistemic.assertion_density, time.time())
        for entry in extraction.entries:
            await ctx.memory.store_stance(ctx.channel_id, ctx.user_id, entry.topic, entry.position, entry.confidence)


# --- Stage 13: spawn reaction/tool tasks (BACKGROUND) ---


async def _stage_spawn_side_effects(ctx: TurnCtx) -> None:
    if ctx.reactions:
        ctx.spawn_task(add_reactions(ctx.message, ctx.reactions), name="reactions")

    if ctx.llm_response.tool_calls:
        reminder_calls = [tc for tc in ctx.llm_response.tool_calls if tc.name in _REMINDER_TOOL_NAMES]
        other_calls = [tc for tc in ctx.llm_response.tool_calls if tc.name not in _REMINDER_TOOL_NAMES]
        for rc in reminder_calls:
            ctx.spawn_task(
                execute_reminder_call(ctx.message, rc, ctx.memory, ctx.bot),
                name=f"reminder:{rc.name}",
            )
        if other_calls and ctx.message.guild:
            ctx.spawn_task(
                execute_tool_calls(
                    ctx.message,
                    other_calls,
                    memory=ctx.memory,
                    llm=ctx.llm,
                    settings=ctx.settings,
                    spawn_task=ctx.spawn_task,
                ),
                name=f"tool_calls:{','.join(tc.name for tc in other_calls)}",
            )


# --- Stage 14: ensure non-empty payload (fallback to in-character generic) ---


async def _stage_ensure_payload(ctx: TurnCtx) -> None:
    has_side_effects = bool(ctx.reactions or ctx.llm_response.tool_calls)
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

    # Silent-tool-call recovery (v3.8.0):
    # When the LLM fires `create_reminder` or `cancel_reminder` without
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


# --- Stage 15: delivery ---


async def _stage_deliver(ctx: TurnCtx) -> None:
    has_side_effects = bool(ctx.reactions or ctx.llm_response.tool_calls)
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
    validate_flow_adherence(ctx.response_text, ctx.flow_analysis)

    # F2 (2026-05-11): soft-monitor for "competent but flat" replies. We do
    # NOT block, retry, or gate on this — F2 just measures whether the flat-
    # presence problem (the Alex DIF turn) exists at production scale. KQL:
    #   ContainerAppConsoleLogs_CL
    #   | where event_s == "lifelessness_check"
    #   | summarize count() by band_s, preset_s
    # Once we have a week of data we decide F3 retry policy.
    lifelessness = detect_lifelessness(ctx.response_text, ctx.text)
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

    from insult.core.quality import check_quality

    recent_shapes = ctx.expression_history.recent_shapes(ctx.context_key, n=5)
    check_quality(
        ctx.response_text,
        ctx.text,
        recent_shapes,
        agreement_streak=ctx.flow_analysis.agreement_streak,
    )

    from insult.core.metrics import record_message_trace

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
    ctx.spawn_task(
        extract_user_facts(
            ctx.llm,
            ctx.settings.summary_model,
            ctx.memory,
            ctx.bot,
            ctx.user_id,
            ctx.user_name,
            ctx.user_facts,
            ctx.recent,
            ctx.guild_id,
            ch_name,
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
