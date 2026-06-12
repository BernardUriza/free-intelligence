"""Proactive check-in loop (every 30 min, context-aware).

~70% social check-in, ~30% world scan. Coordinates with the Moltbook
inbound digest through the shared ``ProactiveState`` so the two never
double-tap the same channel. Generation rides the runner's one-shot
/v1/judge; no-ops when the runner isn't wired.
"""

from __future__ import annotations

import structlog
from discord.ext import tasks

from personas.insult.core.delivery import MESSAGE_DELIMITER, split_response
from personas.insult.core.proactive import (
    generate_proactive_message,
    generate_world_scan_message,
    get_conversation_state,
    should_send_now,
    should_world_scan,
)
from personas.insult.tasks.channels import find_most_active_channel
from personas.insult.tasks.state import ProactiveState
from shared.time_context import _get_current_time_context

log = structlog.get_logger()


def build_proactive_task(bot, container, memory, state: ProactiveState) -> tasks.Loop:
    """Return the (unstarted) proactive loop. ``state`` is shared with the
    Moltbook inbound task for should_send_now coordination."""

    @tasks.loop(minutes=30)
    async def _proactive_task():
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo

        now = dt.now(ZoneInfo("America/Mexico_City"))

        # Find the most recently active text channel (by actual timestamp, not message count)
        target_channel = await find_most_active_channel(bot, memory, skip_event="proactive_channel_skip")
        if not target_channel:
            return

        # Get last USER message timestamp (not bot messages) for activity detection
        try:
            recent_msgs = await memory.get_recent(str(target_channel.id), limit=15)
            last_user_msg_ts = None
            for m in reversed(recent_msgs):
                if m["role"] == "user":
                    last_user_msg_ts = m["timestamp"]
                    break
        except Exception:
            log.exception("proactive_context_failed")
            return

        # Decision: should we send? (checks quiet hours, activity state, backoff)
        if not should_send_now(now.hour, state.last_proactive_ts, last_user_msg_ts, state.unanswered):
            return

        # Gather user facts for all known users
        try:
            all_user_data = await memory.get_all_user_messages(limit_per_user=5)
            user_facts = {}
            for uid, data in all_user_data.items():
                facts = await memory.get_facts(uid)
                if facts:
                    user_facts[data["user_name"]] = facts
        except Exception:
            log.exception("proactive_context_failed")
            return

        time_str = _get_current_time_context()

        # ~30% world scan, ~70% social check-in
        is_world_scan = should_world_scan()
        log.info(
            "proactive_mode_selected",
            mode="world_scan" if is_world_scan else "social",
            unanswered=state.unanswered,
            conversation_state=get_conversation_state(last_user_msg_ts).value,
        )

        if container.judge_client is None:
            log.info("proactive_skipped", reason="no_judge_client")
            return

        if is_world_scan:
            scan_result = await generate_world_scan_message(
                container.judge_client, container.settings.llm_model, time_str, user_facts, recent_msgs
            )
            msg = scan_result.commentary if scan_result else None
        else:
            scan_result = None
            msg = await generate_proactive_message(
                container.judge_client, container.settings.llm_model, time_str, user_facts, recent_msgs
            )

        if msg:
            # Proactive output now rides the runner's one-shot /v1/judge,
            # which applies none of the legacy post-generation guards
            # (character_break, language_cure, strip_metadata). For a
            # background check-in we accept the raw text as-is.

            try:
                parts = split_response(msg)
                for part in parts:
                    await target_channel.send(part)
                state.last_proactive_ts = dt.now().timestamp()
                state.unanswered += 1  # Increment until user responds

                # Store in conversation memory
                await memory.store(
                    str(target_channel.id),
                    str(bot.user.id),
                    bot.user.name,
                    "assistant",
                    msg.replace(MESSAGE_DELIMITER, "\n"),
                )

                # World scan: persist to internal DB + post to feed channel
                if scan_result:
                    await memory.store_world_scan(scan_result.topic, scan_result.findings, scan_result.commentary)
                    feed_channel_name = "insult-world-feed"
                    for guild in bot.guilds:
                        feed = next((ch for ch in guild.text_channels if ch.name == feed_channel_name), None)
                        if feed and feed.id != target_channel.id:
                            feed_parts = split_response(msg)
                            for part in feed_parts:
                                await feed.send(part)
                            log.info("world_scan_feed_posted", channel=feed.name)

                log.info(
                    "proactive_message_sent",
                    channel=target_channel.name,
                    length=len(msg),
                    mode="world_scan" if is_world_scan else "social",
                    unanswered=state.unanswered,
                )
            except Exception:
                log.exception("proactive_send_failed")

    return _proactive_task
