"""Shared helper: find the most recently active text channel.

Background tasks that message the server unprompted need "the channel whose
newest stored message is the most recent across all guilds". Centralized here
so each consumer only differs in its debug skip-event name.
"""

from __future__ import annotations

import structlog

log = structlog.get_logger()


async def find_most_active_channel(bot, memory, *, skip_event: str = "channel_skip"):
    """Return the text channel with the newest stored message, or None.

    Scans every text channel in every guild and keeps the one whose latest
    message timestamp is greatest. Per-channel read failures are swallowed
    (logged at debug under ``skip_event``) so one bad channel never aborts
    the whole scan — same fail-soft posture the inline copies had.
    """
    target_channel = None
    latest_msg_ts: float = 0
    for guild in bot.guilds:
        for ch in guild.text_channels:
            try:
                recent = await memory.get_recent(str(ch.id), limit=1)
                if recent and recent[0]["timestamp"] > latest_msg_ts:
                    latest_msg_ts = recent[0]["timestamp"]
                    target_channel = ch
            except Exception:
                log.debug(skip_event, channel=ch.name)
    return target_channel
