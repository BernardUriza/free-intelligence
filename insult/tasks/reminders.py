"""Reminder delivery + ack-overdue sweep + snooze/ack reaction handling.

Three pieces of the reminders domain that used to live inline in
``bot._build``:

- ``_reminder_check`` (30s loop): deliver due reminders in-character (via
  the runner's /v1/judge, with a hardcoded fallback), add snooze/ack
  reactions, advance recurring schedules.
- ``_ack_overdue`` (5min loop): re-fire requires_ack reminders that were
  never ✅'d, capped at ACK_MAX_RETRIES.
- ``handle_snooze_reaction``: the ``on_raw_reaction_add`` body — ✅ acks,
  the snooze emojis re-arm the reminder.
"""

from __future__ import annotations

import time as _time

import structlog
from discord.ext import tasks

from insult.core.guild_setup import post_reminder_delivered
from insult.core.reminders import ACK_MAX_RETRIES, ACK_TIMEOUT_SECONDS, compute_next_occurrence
from insult.core.snooze import SNOOZE_EMOJIS, snooze_delta_for_emoji

log = structlog.get_logger()


def build_reminder_tasks(bot, container, memory) -> tuple[tasks.Loop, tasks.Loop]:
    """Return (reminder_check_loop, ack_overdue_loop), both unstarted."""

    @tasks.loop(seconds=30)
    async def _reminder_check_task():
        try:
            now = _time.time()
            pending = await memory.get_pending_reminders(now)
            for reminder in pending:
                channel = bot.get_channel(int(reminder["channel_id"]))
                if not channel:
                    await memory.mark_reminder_delivered(reminder["id"])
                    log.warning("reminder_channel_gone", reminder_id=reminder["id"], channel_id=reminder["channel_id"])
                    continue

                # Build mention string
                mentions = ""
                if reminder["mention_user_ids"]:
                    user_ids = reminder["mention_user_ids"].split(",")
                    mentions = " ".join(f"<@{uid.strip()}>" for uid in user_ids if uid.strip())

                # Generate in-character reminder via LLM
                reminder_prompt = (
                    f"{container.settings.system_prompt[:2000]}\n\n"
                    "## Special Task: Deliver a Reminder\n"
                    f"You need to deliver a reminder. The reminder is: '{reminder['description']}'. "
                    "Deliver it in-character — short, punchy, maybe a bit aggressive. "
                    "Don't explain you're a bot delivering a reminder. Just remind them naturally. "
                    "1-2 sentences max."
                )

                # Plain hardcoded fallback whenever the runner isn't wired or
                # the judge call fails/returns empty — the user must get actual
                # reminder content, never a bare mention with no body.
                fallback_text = f"⏰ Recordatorio: {reminder['description']}"
                if container.judge_client is None:
                    text = fallback_text
                else:
                    try:
                        response = await container.judge_client.utility_call(
                            reminder_prompt,
                            [{"role": "user", "content": f"Recordatorio: {reminder['description']}"}],
                        )
                        text = (response.text or "").strip() or fallback_text
                        if text is fallback_text:
                            log.info("reminder_llm_empty_fallback", reminder_id=reminder["id"])
                    except Exception:
                        log.exception("reminder_llm_failed", reminder_id=reminder["id"])
                        text = fallback_text

                msg = f"{mentions} {text}".strip() if mentions else text
                sent_msg = None
                try:
                    sent_msg = await channel.send(msg)
                except Exception:
                    log.exception("reminder_send_failed", reminder_id=reminder["id"])

                # Snooze affordance: only one-shot reminders get reactions —
                # recurring ones already re-fire on their own and the user
                # would conflate the two flows.
                if sent_msg is not None and reminder["recurring"] == "none":
                    try:
                        await memory.set_snooze_msg_id(reminder["id"], sent_msg.id)
                        for emoji in SNOOZE_EMOJIS:
                            try:
                                await sent_msg.add_reaction(emoji)
                            except Exception:
                                log.warning(
                                    "reminder_snooze_reaction_failed",
                                    reminder_id=reminder["id"],
                                    emoji=emoji,
                                )
                    except Exception:
                        log.exception("reminder_snooze_setup_failed", reminder_id=reminder["id"])

                # Ack affordance: when requires_ack is set, tag delivery time
                # and add the ✅ reaction. The overdue sweep below re-fires
                # one time if the ✅ is missing after ACK_TIMEOUT_SECONDS.
                if sent_msg is not None and reminder.get("requires_ack"):
                    try:
                        await memory.set_ack_metadata(reminder["id"], sent_msg.id, _time.time())
                        try:
                            await sent_msg.add_reaction("✅")
                        except Exception:
                            log.warning("reminder_ack_reaction_failed", reminder_id=reminder["id"])
                    except Exception:
                        log.exception("reminder_ack_setup_failed", reminder_id=reminder["id"])

                # Handle recurring
                if reminder["recurring"] != "none":
                    next_time = compute_next_occurrence(reminder["remind_at"], reminder["recurring"])
                    if next_time:
                        await memory.update_reminder_time(reminder["id"], next_time)
                    else:
                        await memory.mark_reminder_delivered(reminder["id"])
                else:
                    await memory.mark_reminder_delivered(reminder["id"])

                log.info("reminder_delivered", reminder_id=reminder["id"], channel_id=reminder["channel_id"])

                # Post delivery log to system reminders channel
                await post_reminder_delivered(
                    bot,
                    memory,
                    reminder.get("guild_id"),
                    reminder["description"],
                    mentions,
                    reminder["id"],
                )
        except Exception:
            log.exception("reminder_check_failed")

    @tasks.loop(seconds=300)
    async def _ack_overdue_task():
        try:
            now = _time.time()
            overdue = await memory.get_ack_overdue(now, ACK_TIMEOUT_SECONDS, ACK_MAX_RETRIES)
            for r in overdue:
                try:
                    new_id = await memory.save_reminder(
                        channel_id=r["channel_id"],
                        guild_id=r["guild_id"],
                        created_by=r["created_by"],
                        description=f"⚠️ Sin confirmar: {r['description']}",
                        remind_at=now + 60,  # re-fire in ~1 min so the sweep doesn't pick it up again before sending
                        mention_user_ids=r["mention_user_ids"] or "",
                        recurring="none",
                        requires_ack=False,  # avoid retry loops; one re-fire is the policy
                    )
                    await memory.increment_ack_retry(r["id"])
                    log.info(
                        "reminder_ack_overdue_refired",
                        original_id=r["id"],
                        new_id=new_id,
                        retry_count=r["ack_retry_count"] + 1,
                    )
                except Exception:
                    log.exception("reminder_ack_overdue_refire_failed", reminder_id=r["id"])
        except Exception:
            log.exception("ack_overdue_task_failed")

    return _reminder_check_task, _ack_overdue_task


async def handle_snooze_reaction(payload, bot, memory) -> None:
    """``on_raw_reaction_add`` body — ack (✅) or snooze (emoji map) handling.

    Uses raw events so it works for delivered reminders no longer in the
    message cache (typical after a restart). Skips the bot's own reactions
    (we add the snooze emojis ourselves) and any emoji that isn't in the
    snooze set.
    """
    if bot.user is not None and payload.user_id == bot.user.id:
        return
    emoji = str(payload.emoji)
    # Ack path: a ✅ on a delivered requires_ack reminder marks it confirmed
    # and skips the overdue re-fire. We try this BEFORE snooze so a single
    # ✅ on a reminder that has both affordances (rare but possible) acks
    # rather than snoozing.
    if emoji == "✅":
        if await memory.mark_ack_received(payload.message_id):
            log.info(
                "reminder_ack_received",
                ack_msg_id=payload.message_id,
                user_id=payload.user_id,
            )
        return
    delta = snooze_delta_for_emoji(emoji)
    if delta is None:
        return
    reminder = await memory.get_reminder_for_snooze(payload.message_id)
    if reminder is None:
        return
    # Re-arm before clearing the pointer so a crash between the two
    # leaves the snooze pointer intact (user can react again).
    new_remind_at = _time.time() + delta
    try:
        new_id = await memory.save_reminder(
            channel_id=reminder["channel_id"],
            guild_id=reminder["guild_id"],
            created_by=reminder["created_by"],
            description=reminder["description"],
            remind_at=new_remind_at,
            mention_user_ids=reminder["mention_user_ids"] or "",
            recurring="none",
        )
    except Exception:
        log.exception("reminder_snooze_create_failed", original_id=reminder["id"], delta=delta)
        return
    await memory.clear_snooze_msg_id(payload.message_id)
    log.info(
        "reminder_snoozed",
        original_id=reminder["id"],
        new_id=new_id,
        delta_seconds=delta,
        emoji=emoji,
        user_id=payload.user_id,
    )
