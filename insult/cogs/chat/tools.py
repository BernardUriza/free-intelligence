"""Tool-call execution: reminders, channel creation/info/edit, inauguration.

Free async functions. `run_turn` spawns them via the injected `spawn_task`
callback so each runs in its own tracked background task. The functions
take the dependencies they need explicitly rather than reaching through
`self` — same pattern as `context.py` and `tasks.py`.

`ALL_TOOLS` is the static tool definition list (channel + reminder) used
in every turn; web_search is added dynamically in `turn.run_turn` based
on the selected preset.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import discord
import structlog

from insult.core.actions import (
    CHANNEL_TOOLS,
    execute_create_channel,
    execute_edit_channel,
    execute_get_channel_info,
)
from insult.core.delivery import send_response
from insult.core.guild_setup import post_reminder_set
from insult.core.reminders import REMINDER_TOOLS, format_reminder_list, resolve_remind_at

log = structlog.get_logger()

# Static tool list — built once at import, reused every turn.
ALL_TOOLS: list = list(CHANNEL_TOOLS) + list(REMINDER_TOOLS)


async def execute_reminder_call(
    message: discord.Message,
    tool_call,
    memory,
    bot,
) -> None:
    """Execute a single reminder tool call (create, list, or cancel)."""
    try:
        if tool_call.name == "create_reminder":
            description = tool_call.input.get("description", "")
            remind_at_str = tool_call.input.get("remind_at") or None
            in_seconds = tool_call.input.get("in_seconds")
            mention_ids = tool_call.input.get("mention_user_ids", [])
            recurring = tool_call.input.get("recurring", "none")

            remind_at = resolve_remind_at(remind_at_str, in_seconds)
            if remind_at is None:
                log.warning(
                    "reminder_invalid_time",
                    remind_at=remind_at_str,
                    in_seconds=in_seconds,
                )
                return
            # Format an ISO string for downstream display (post_reminder_set
            # expects a string). When the LLM only sent in_seconds we
            # synthesize one in CDMX time.
            if not remind_at_str:
                from zoneinfo import ZoneInfo

                remind_at_str = datetime.fromtimestamp(remind_at, tz=ZoneInfo("America/Mexico_City")).isoformat()

            mention_str = ",".join(mention_ids) if mention_ids else ""
            guild_id = str(message.guild.id) if message.guild else None

            reminder_id = await memory.save_reminder(
                channel_id=str(message.channel.id),
                guild_id=guild_id,
                created_by=str(message.author.id),
                description=description,
                remind_at=remind_at,
                mention_user_ids=mention_str,
                recurring=recurring,
            )
            log.info(
                "reminder_created",
                reminder_id=reminder_id,
                description=description[:80],
                remind_at=remind_at_str,
                recurring=recurring,
            )
            if guild_id:
                mention_display = " ".join(f"<@{uid.strip()}>" for uid in mention_ids if uid) if mention_ids else ""
                await post_reminder_set(
                    bot,
                    memory,
                    guild_id,
                    description,
                    remind_at_str,
                    mention_display,
                    recurring,
                    reminder_id,
                )

        elif tool_call.name == "list_reminders":
            channel_id = tool_call.input.get("channel_id", str(message.channel.id))
            reminders = await memory.get_channel_reminders(channel_id)
            formatted = format_reminder_list(reminders)
            await message.channel.send(formatted)

        elif tool_call.name == "cancel_reminder":
            reminder_id = tool_call.input.get("reminder_id", 0)
            deleted = await memory.delete_reminder(reminder_id)
            if not deleted:
                log.warning("reminder_cancel_not_found", reminder_id=reminder_id)

    except Exception:
        log.exception("reminder_tool_call_failed", tool=tool_call.name)


async def execute_tool_calls(
    message: discord.Message,
    tool_calls: list,
    *,
    memory,
    llm,
    settings,
    spawn_task: Callable[..., None],
) -> None:
    """Execute channel creation / info / edit tool calls from Claude.

    When a channel is created, a nested background task inaugurates it
    with a philosophical opening message — spawned via `spawn_task` so it
    gets the same tracked-task treatment (name + duration log).
    """
    for tool_call in tool_calls:
        try:
            if tool_call.name == "create_channel" and message.guild:
                channel = await execute_create_channel(message.guild, tool_call, message.author)
                if channel:
                    await message.channel.send(f"Listo, ahí está: {channel.mention}")
                    spawn_task(
                        inaugurate_channel(
                            channel,
                            tool_call.input.get("name", ""),
                            message.author,
                            memory=memory,
                            llm=llm,
                            settings=settings,
                        ),
                        name=f"inaugurate:{channel.name}",
                    )
                else:
                    log.warning("tool_call_returned_none", tool=tool_call.name)

            elif tool_call.name == "get_channel_info" and isinstance(message.channel, discord.TextChannel):
                info = execute_get_channel_info(message.channel)
                topic_display = info["topic"] or "(sin descripción)"
                await message.channel.send(f"**#{info['name']}** — {topic_display}")

            elif tool_call.name == "edit_channel" and isinstance(message.channel, discord.TextChannel):
                success = await execute_edit_channel(message.channel, tool_call)
                if not success:
                    log.warning("tool_call_edit_failed", tool=tool_call.name)

            else:
                log.warning("tool_call_unknown", tool=tool_call.name)
        except Exception:
            log.exception("tool_call_execution_failed", tool=tool_call.name)


async def inaugurate_channel(
    channel: discord.abc.GuildChannel,
    channel_name: str,
    creator: discord.Member,
    *,
    memory,
    llm,
    settings,
) -> None:
    """Generate a philosophical opening message for a freshly created channel.

    Uses the creator's loaded user facts so the message feels personal.
    If the LLM call fails for any reason we just log — a missing opener
    is a far better failure mode than crashing the channel creation.
    """
    from insult.cogs.chat.context import load_facts
    from insult.core.character import _get_current_time_context

    time_ctx = _get_current_time_context()

    creator_facts = await load_facts(memory, str(creator.id))
    facts_str = ", ".join(f["fact"] for f in creator_facts) if creator_facts else "no los conozco todavia"

    inaugural_prompt = (
        f"{settings.system_prompt}\n\n"
        f"## Current Time\n{time_ctx}\n\n"
        "## Special Task: Channel Inauguration\n"
        f"You just created a new channel called #{channel_name}. "
        f"The person who asked for it is {creator.display_name}. "
        f"What you know about them: {facts_str}.\n\n"
        "Write an opening message for this channel. This is YOUR territory — make it count.\n\n"
        "Requirements:\n"
        "- Open with something philosophical, provocative, or deeply interesting about the channel's topic\n"
        "- Ask 2-3 questions that would make people WANT to participate — uncomfortable, interesting, real questions\n"
        "- Keep your personality: sharp, system-critical, anti-domination, curious, never bland\n"
        "- Reference the time of day, your mood, the creator — make it feel alive, not templated\n"
        "- If the topic relates to ethics, power, systems, animals, capitalism — go deeper\n"
        "- DO NOT use markdown headers, bullet points, or structured formatting. Talk like a person.\n"
        "- Length: medium to long. This is a manifesto for the channel, not a tweet.\n"
        "- You can use [SEND] to split into multiple messages for dramatic effect.\n"
        "- DO NOT call any tools. Just write the text directly.\n"
    )

    try:
        llm_response = await llm.chat(
            inaugural_prompt,
            [{"role": "user", "content": f"Inaugura el canal #{channel_name}"}],
        )
        text = llm_response.text
        if text:
            await send_response(channel, text)
            log.info("channel_inaugurated", channel=channel_name, length=len(text))
    except Exception:
        log.exception("channel_inauguration_failed", channel=channel_name)
