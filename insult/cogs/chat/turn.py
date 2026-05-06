"""Single-turn response pipeline.

`run_turn` is the body of the old `ChatCog._respond_inner`, now a free
async function. The cog's `_respond` wrapper handles the contextvars
binding and the terminal `chat_turn_end` log; `run_turn` owns everything
between — attachments, memory store, context build, preset classification,
4-flow analysis, system-prompt composition, LLM call, post-generation
transforms, memory persistence, arc/stance updates, background task
spawning, delivery, and telemetry.

Returns an outcome string for `chat_turn_end`:
  - "ok"                — LLM responded and delivery succeeded
  - "trivial_skipped"   — message matched triviality rules, no LLM call
  - "context_failed"    — memory read failed, user notified
  - "llm_failed"        — LLM client raised after retries exhausted
  - "delivery_failed"   — Discord rejected the send (HTTPException)
  - "delivery_crashed"  — unexpected exception in delivery path
"""

from __future__ import annotations

import time
from collections.abc import Callable

import discord
import structlog

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
from insult.cogs.chat.tasks import extract_user_facts
from insult.cogs.chat.tools import execute_reminder_call, execute_tool_calls
from insult.core.arc_tracker import ArcState, arc_from_dict, arc_to_dict, build_arc_prompt, update_arc
from insult.core.attachments import process_attachments
from insult.core.character import (
    build_adaptive_prompt,
    compose_extra_layers,
    deduplicate_opener,
    enforce_length_variation,
    strip_echoed_quotes,
)
from insult.core.delivery import MESSAGE_DELIMITER, send_response
from insult.core.disclosure import scan_disclosure
from insult.core.errors import ErrorType, classify_error, get_error_response
from insult.core.facts import build_facts_prompt
from insult.core.flows import ExpressionHistory, analyze_flows, build_flow_prompt, validate_flow_adherence
from insult.core.llm import WEB_SEARCH_TOOL
from insult.core.presets import PresetModifier
from insult.core.reactions import add_reactions, parse_reactions, strip_reactions
from insult.core.reminders import detect_reminder_intent
from insult.core.routing import ModelTier, OpusBudget, select_model
from insult.core.stance_log import build_stance_prompt
from insult.core.triviality import is_trivial

log = structlog.get_logger()

_REMINDER_TOOL_NAMES = {"create_reminder", "list_reminders", "cancel_reminder"}


async def run_turn(
    message: discord.Message,
    text: str,
    *,
    turn_start: float,
    memory,
    llm,
    settings,
    bot,
    expression_history: ExpressionHistory,
    opus_budget: OpusBudget,
    spawn_task: Callable[..., None],
    all_tools: list,
) -> str:
    """Execute one full turn. Returns an outcome string for terminal logging."""
    channel_id = str(message.channel.id)
    user_id = str(message.author.id)
    user_name = message.author.display_name

    log.info(
        "chat_turn_start",
        text_len=len(text),
        text_preview=text[:120],
        attachments=len(message.attachments),
        is_voice=bool(message.flags.voice),
        guild_id=str(message.guild.id) if message.guild else None,
        channel_name=message.channel.name if hasattr(message.channel, "name") else None,
    )

    def _stage_elapsed() -> int:
        return int((time.monotonic() - turn_start) * 1000)

    # --- Attachments ---
    # Skip for voice messages: the .ogg was already transcribed by Whisper
    # in batch.py and is now in `text`. If we also run process_attachments
    # on that same .ogg, the unsupported-file branch surfaces
    # "No puedo leer archivos .ogg..." as a ghost message in the channel
    # alongside the real response. Reported 2026-04-24 by bernard2389.
    attachment_blocks: list = []
    if message.attachments and not message.flags.voice:
        blocks, errors = await process_attachments(message.attachments)
        attachment_blocks = blocks
        for err in errors:
            await message.channel.send(err)
        log.info(
            "stage_attachments_processed",
            blocks=len(attachment_blocks),
            errors=len(errors),
            elapsed_ms=_stage_elapsed(),
        )

    # Short text description of images so future turns can reference them
    # from SQLite-backed context (which stores only text).
    image_blocks = [b for b in attachment_blocks if isinstance(b, dict) and b.get("type") == "image"]
    text_for_memory = await summarize_user_images_into_text(image_blocks, llm, settings.summary_model, text)

    guild_id = str(message.guild.id) if message.guild else None
    channel_name = message.channel.name if hasattr(message.channel, "name") else None

    # --- Memory store + style profile ---
    await store_user_message(
        memory,
        channel_id,
        user_id,
        user_name,
        text_for_memory,
        guild_id,
        channel_name,
    )

    # Update style profile BEFORE the trivial gate so short-message users
    # still accumulate signal for language/formality/emoji detection.
    profile = await update_style_profile(memory, user_id, text)

    log.info(
        "stage_memory_stored",
        elapsed_ms=_stage_elapsed(),
        profile_confident=bool(profile and profile.is_confident),
    )

    # Cost guard: skip LLM call for trivial messages (ok, gracias, lone emojis).
    # Message already stored + profile updated above.
    if not message.attachments and is_trivial(text):
        log.info("skipped_trivial_message", text=text[:40])
        return "trivial_skipped"

    # --- Context + facts ---
    context, recent = await build_context(memory, settings, channel_id, text, attachment_blocks)
    if context is None:
        log.warning("chat_turn_aborted", reason="context_failed")
        await message.channel.send(get_error_response(ErrorType.CONTEXT_FAILED))
        return "context_failed"

    log.info(
        "stage_context_built",
        context_len=len(context),
        recent_count=len(recent),
        elapsed_ms=_stage_elapsed(),
    )

    user_facts = await load_facts_smart(memory, user_id, text)
    log.info("stage_facts_loaded", facts_count=len(user_facts), elapsed_ms=_stage_elapsed())

    # Load facts for ALL other participants in channel (group-chat awareness)
    other_participants_facts = await load_other_participants_facts(memory, channel_id, user_id)

    # Server pulse (cross-channel awareness)
    server_pulse = await load_server_pulse(memory, message, channel_id, text)

    # --- Phase 1 (v3.0.0): pre-LLM disclosure scan ---
    disclosure = scan_disclosure(text)
    if disclosure.detected:
        import json as _json

        await memory.store_disclosure(
            channel_id,
            user_id,
            disclosure.category,
            disclosure.severity,
            _json.dumps(disclosure.signals),
            text[:200],
        )

    # Emotional arc state
    arc_data = await memory.get_arc(channel_id, user_id)
    arc_state = arc_from_dict(arc_data) if arc_data else ArcState()

    # Recent response lengths for Fix #3 (length variation hint)
    recent_response_lengths = [len(m.get("content", "").split()) for m in recent if m["role"] == "assistant"][-5:]

    # --- System prompt assembly (preset + flows + arc + facts) ---
    context_key = f"{channel_id}:{user_id}"
    system_prompt, preset = build_adaptive_prompt(
        settings.system_prompt,
        profile,
        len(context),
        current_message=text,
        recent_messages=recent,
        user_facts=user_facts,
        server_pulse=server_pulse,
        recent_response_lengths=recent_response_lengths,
    )
    log.info(
        "preset_classified",
        preset=preset.mode.value,
        modifiers=[m.value for m in preset.modifiers],
        disclosure_severity=disclosure.severity,
        disclosure_category=disclosure.category,
        arc_phase=arc_state.phase,
        elapsed_ms=_stage_elapsed(),
    )

    flow_analysis = analyze_flows(text, recent, preset, expression_history, context_key)
    log.info(
        "stage_flows_analyzed",
        pressure=flow_analysis.pressure.pressure_level,
        user_state=flow_analysis.pressure.detected_state.value,
        shape=flow_analysis.expression.selected_shape.value,
        flavor=flow_analysis.expression.selected_flavor.value,
        awareness=flow_analysis.awareness.detected_pattern.value,
        epistemic_move=flow_analysis.epistemic.recommended_move.value,
        agreement_streak=flow_analysis.agreement_streak,
        elapsed_ms=_stage_elapsed(),
    )

    stances = await memory.get_stances(channel_id, user_id, limit=5)

    system_prompt = compose_extra_layers(
        system_prompt,
        flow_prompt=build_flow_prompt(flow_analysis),
        arc_prompt=build_arc_prompt(arc_state),
        stance_prompt=build_stance_prompt(stances) if stances else "",
        facts_prompt=build_facts_prompt(user_name, user_facts),
        other_participants_facts=other_participants_facts,
    )

    if profile and profile.is_confident:
        log.info(
            "style_adapted",
            user_id=user_id,
            preset=preset.mode.value,
            preset_modifiers=[m.value for m in preset.modifiers],
            language=profile.detected_language,
            formality=round(profile.formality, 2),
            technical=round(profile.technical_level, 2),
            verbosity=round(profile.avg_word_count, 1),
        )

    # --- Tools: static + open web_search ---
    # Anthropic's API rejects two tools with the same name in one request,
    # and switching tool definitions between turns invalidates the prompt
    # cache (tools → system → messages hierarchy). So we register one
    # web_search and steer source selection via the vulnerable-user
    # overlay prompt when clinical citations matter (see
    # `_VULNERABLE_OVERLAY_PROMPT` in core/presets.py).
    tools = [*all_tools, WEB_SEARCH_TOOL]

    force_tool = PresetModifier.ACTION_INTENT in preset.modifiers
    tool_choice = {"type": "any"} if force_tool else None

    # 3-tier router — feature-flagged
    model_choice = None
    if getattr(settings, "model_router_enabled", False):
        model_choice = select_model(
            preset,
            flow_analysis,
            disclosure.severity,
            casual_model=settings.casual_model,
            depth_model=settings.llm_model,
            crisis_model=settings.crisis_model,
            opus_24h_count=opus_budget.count(user_id),
            opus_24h_cap=opus_budget.cap,
        )
        log.info(
            "model_routed",
            tier=model_choice.tier.value,
            primary=model_choice.primary,
            fallback=model_choice.fallback,
            reason=model_choice.reason,
            preset=preset.mode.value,
            disclosure_severity=disclosure.severity,
            user_id=user_id,
        )

    async def _notify_retry():
        notify_start = time.monotonic()
        try:
            await message.channel.send(get_error_response(ErrorType.RETRY_NOTICE))
        except Exception:
            log.exception("retry_notice_send_failed", delivery_ms=int((time.monotonic() - notify_start) * 1000))
            return
        log.info("retry_notice_sent", delivery_ms=int((time.monotonic() - notify_start) * 1000))

    # --- LLM call ---
    llm_start = time.monotonic()
    log.info(
        "llm_call_start",
        prompt_chars=len(system_prompt),
        context_messages=len(context),
        tools=[t.get("name", t.get("type", "?")) for t in tools],
        tool_choice=(tool_choice or {}).get("type"),
        primary_model=model_choice.primary if model_choice else settings.llm_model,
        fallback_model=model_choice.fallback if model_choice else None,
    )
    try:
        async with message.channel.typing():
            llm_kwargs: dict = {"tools": tools, "tool_choice": tool_choice, "on_timeout": _notify_retry}
            if model_choice is not None:
                llm_kwargs["model"] = model_choice.primary
                llm_kwargs["fallback_model"] = model_choice.fallback
            llm_response = await llm.chat(system_prompt, context, **llm_kwargs)
    except Exception as e:
        log.exception(
            "chat_llm_failed",
            error_type=type(e).__name__,
            error_msg=str(e)[:200],
            llm_ms=int((time.monotonic() - llm_start) * 1000),
        )
        await message.channel.send(get_error_response(classify_error(e)))
        return "llm_failed"

    llm_ms = int((time.monotonic() - llm_start) * 1000)
    tool_names = [tc.name for tc in llm_response.tool_calls]
    log.info(
        "llm_call_complete",
        llm_ms=llm_ms,
        text_len=len(llm_response.text),
        tool_calls=len(llm_response.tool_calls),
        tool_names=tool_names,
        model_used=llm_response.model_used,
        elapsed_ms=_stage_elapsed(),
    )

    # Safety net for the v3.7.2-class silent-fail: if the user obviously asked
    # for a reminder and the LLM did not call create_reminder, log a warning
    # and append a short nudge to the response so the user knows the formal
    # reminder was not set. Without this the bug is invisible from the user's
    # side — the bot replies in prose and they only notice when nothing fires.
    intent_unattended = "create_reminder" not in tool_names and detect_reminder_intent(text)
    if intent_unattended:
        log.warning(
            "reminder_intent_unattended",
            text_preview=text[:120],
            tool_names=tool_names,
        )

    # Opus budget: record only on success so transient failures don't burn the cap
    if model_choice is not None and model_choice.tier == ModelTier.CRISIS:
        opus_budget.record(user_id)

    # --- Post-generation transforms ---
    response = llm_response.text
    post_llm_len = len(response)

    def _log_mutation(stage: str, before: str, after: str) -> None:
        if before != after:
            log.info(
                "text_mutated",
                stage=stage,
                before_len=len(before),
                after_len=len(after),
                delta=len(after) - len(before),
            )

    before = response
    response = strip_echoed_quotes(response, text)
    _log_mutation("strip_echoed_quotes", before, response)

    before = response
    response = enforce_length_variation(response, recent_response_lengths)
    _log_mutation("enforce_length_variation", before, response)

    recent_openers = [m["content"].split("\n")[0] for m in recent if m["role"] == "assistant"][-5:]
    before = response
    response = deduplicate_opener(response, recent_openers)
    _log_mutation("deduplicate_opener", before, response)

    reactions = parse_reactions(response)
    before = response
    response = strip_reactions(response)
    _log_mutation("strip_reactions", before, response)

    # Reminder-intent nudge (see intent_unattended detection above). Appended
    # only when the LLM produced text — silent reaction-only turns would feel
    # bizarre with a meta footer and the warning log already captured the case.
    if intent_unattended and response.strip():
        response = response.rstrip() + "\n\n*(no agendé recordatorio formal — si querías uno, dime día y hora.)*"

    log.info(
        "stage_post_llm_done",
        raw_llm_len=post_llm_len,
        final_text_len=len(response),
        reactions=reactions,
        elapsed_ms=_stage_elapsed(),
    )

    # --- Persist response, update arc, extract stances ---
    clean_response = response.replace(MESSAGE_DELIMITER, "\n")
    if clean_response.strip():
        await store_assistant_message(
            memory,
            channel_id,
            str(bot.user.id),
            bot.user.name,
            clean_response,
            for_user_id=user_id,
            guild_id=guild_id,
            channel_name=channel_name,
            model_used=llm_response.model_used or None,
        )

    new_arc = update_arc(
        arc_state,
        disclosure_severity=disclosure.severity,
        user_state=flow_analysis.pressure.detected_state.value,
        preset_mode=preset.mode.value,
    )
    arc_dict = arc_to_dict(new_arc)
    await memory.upsert_arc(
        channel_id,
        user_id,
        arc_dict["phase"],
        arc_dict["phase_since"],
        arc_dict["crisis_depth"],
        arc_dict["recovery_signals"],
        arc_dict["turns_in_phase"],
    )

    if clean_response and flow_analysis.epistemic.assertion_density >= 0.4:
        from insult.core.stance_log import extract_stances

        extraction = extract_stances(clean_response, flow_analysis.epistemic.assertion_density, time.time())
        for entry in extraction.entries:
            await memory.store_stance(channel_id, user_id, entry.topic, entry.position, entry.confidence)

    # --- Background tasks: reactions + tool calls ---
    if reactions:
        spawn_task(add_reactions(message, reactions), name="reactions")

    if llm_response.tool_calls:
        reminder_calls = [tc for tc in llm_response.tool_calls if tc.name in _REMINDER_TOOL_NAMES]
        other_calls = [tc for tc in llm_response.tool_calls if tc.name not in _REMINDER_TOOL_NAMES]
        for rc in reminder_calls:
            spawn_task(execute_reminder_call(message, rc, memory, bot), name=f"reminder:{rc.name}")
        if other_calls and message.guild:
            spawn_task(
                execute_tool_calls(
                    message,
                    other_calls,
                    memory=memory,
                    llm=llm,
                    settings=settings,
                    spawn_task=spawn_task,
                ),
                name=f"tool_calls:{','.join(tc.name for tc in other_calls)}",
            )

    # Empty-response fallback (reaction-only / tool-only turns are allowed)
    if not response.strip() and not reactions and not llm_response.tool_calls:
        log.warning(
            "empty_response_fallback",
            raw_llm_len=post_llm_len,
            raw_llm_preview=llm_response.text[:200] if llm_response.text else "",
            final_len=len(response),
            tool_calls=len(llm_response.tool_calls),
        )
        response = get_error_response(ErrorType.GENERIC)

    # --- Delivery ---
    has_side_effects = bool(reactions or llm_response.tool_calls)
    delivery_start = time.monotonic()
    delivery_outcome = "ok"
    try:
        await send_response(message.channel, response, has_side_effects=has_side_effects)
        log.info(
            "chat_delivery_ok",
            final_text_len=len(response),
            delivery_ms=int((time.monotonic() - delivery_start) * 1000),
            llm_ms=llm_ms,
        )
    except discord.HTTPException as e:
        delivery_outcome = "delivery_failed"
        log.error(
            "chat_delivery_failed",
            error_type=type(e).__name__,
            status=getattr(e, "status", None),
            code=getattr(e, "code", None),
            error_msg=str(e)[:200],
            final_text_len=len(response),
            delivery_ms=int((time.monotonic() - delivery_start) * 1000),
        )
    except Exception:
        delivery_outcome = "delivery_crashed"
        log.exception(
            "chat_delivery_crashed",
            final_text_len=len(response),
            delivery_ms=int((time.monotonic() - delivery_start) * 1000),
        )

    # --- Post-generation telemetry ---
    validate_flow_adherence(response, flow_analysis)

    from insult.core.quality import check_quality

    recent_shapes = expression_history.recent_shapes(context_key, n=5)
    check_quality(response, text, recent_shapes, agreement_streak=flow_analysis.agreement_streak)

    from insult.core.metrics import record_message_trace

    record_message_trace(
        {
            "user": user_name,
            "user_id": user_id,
            "channel": channel_id,
            "input": text[:200],
            "response": response[:300],
            "preset": preset.mode.value,
            "preset_modifiers": [m.value for m in preset.modifiers],
            "pressure": flow_analysis.pressure.pressure_level,
            "expression_shape": flow_analysis.expression.selected_shape.value,
            "expression_flavor": flow_analysis.expression.selected_flavor.value,
            "epistemic_move": flow_analysis.epistemic.recommended_move.value,
            "awareness_pattern": flow_analysis.awareness.detected_pattern.value,
            "tools": [tc.name for tc in llm_response.tool_calls] if llm_response.tool_calls else [],
            "reactions": reactions,
        }
    )

    # Background fact extraction (posts new safe facts to the system channel)
    ch_name = getattr(message.channel, "name", "")
    spawn_task(
        extract_user_facts(
            llm,
            settings.summary_model,
            memory,
            bot,
            user_id,
            user_name,
            user_facts,
            recent,
            guild_id,
            ch_name,
        ),
        name="fact_extraction",
    )

    return delivery_outcome
