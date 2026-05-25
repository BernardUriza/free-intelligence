"""Channel-summarization background loop (cross-channel awareness).

Every ``summary_interval_minutes`` it summarizes channels with 10+ new
messages since the last summary, capped at 10 channels per tick, and upserts
each summary into the store. Runs through the runner's one-shot /v1/judge;
no-ops when the runner isn't wired.
"""

from __future__ import annotations

import time as _time

import structlog
from discord.ext import tasks

log = structlog.get_logger()


def build_summarize_channels_task(bot, container, memory) -> tasks.Loop:
    """Return the (unstarted) channel-summarization loop."""

    @tasks.loop(minutes=container.settings.summary_interval_minutes)
    async def _summarize_channels_task():
        from insult.core.summaries import summarize_channel

        if container.judge_client is None:
            return

        try:
            now_ts = _time.time()
            # Summarize channels with 10+ new messages since last summary
            channels_processed = 0
            max_per_tick = 10

            for guild in bot.guilds:
                guild_id = str(guild.id)
                # Get activity since 1 hour ago (fallback window for new channels)
                since_ts = now_ts - 3600
                activity = await memory.get_channel_activity_since(guild_id, since_ts)

                for item in activity:
                    if channels_processed >= max_per_tick:
                        break
                    if item["count"] < 10:
                        continue

                    ch_id = item["channel_id"]
                    # Find the Discord channel object for name + privacy info
                    channel = guild.get_channel(int(ch_id))
                    if channel is None:
                        continue

                    ch_name = channel.name
                    is_private = not channel.permissions_for(guild.default_role).read_messages

                    messages = await memory.get_recent_for_summary(ch_id, limit=50)
                    if not messages:
                        continue

                    summary = await summarize_channel(
                        container.judge_client,
                        container.settings.summary_model,
                        ch_name,
                        messages,
                    )
                    if summary:
                        last_ts = messages[-1]["timestamp"] if messages else now_ts
                        await memory.upsert_channel_summary(
                            guild_id, ch_id, ch_name, summary, item["count"], last_ts, is_private
                        )
                        channels_processed += 1

                if channels_processed >= max_per_tick:
                    break

            if channels_processed > 0:
                log.info("channel_summaries_updated", count=channels_processed)
        except Exception:
            log.exception("channel_summarization_task_failed")

    return _summarize_channels_task
