"""Reminder snooze: map a reaction emoji to a re-fire delta.

When a reminder is delivered to a channel, the bot tags the message with
three reaction emoji (⏰ 10min, ⏭️ 1h, 📅 24h). If the recipient reacts to
the delivered message with one of those, we recreate the reminder for
later instead of marking it permanently done. This file owns ONLY the
emoji→delta mapping; the I/O lives in `bot.py` where the listener and
the Discord message handles already exist.
"""

from __future__ import annotations

# Emoji choices are deliberately distinct in shape so they don't collide
# with reactions a user might add for other reasons. ✅ is reserved for
# the ack flow (#5) so it stays out of this map.
SNOOZE_DELTAS_SECONDS: dict[str, int] = {
    "⏰": 600,  # ⏰  10 minutes
    "⏭️": 3600,  # ⏭️  1 hour
    "\U0001f4c5": 86400,  # 📅  24 hours
}

# Some Discord clients drop the variation selector (FE0F) — accept both forms.
SNOOZE_DELTAS_SECONDS["⏭"] = SNOOZE_DELTAS_SECONDS["⏭️"]


def snooze_delta_for_emoji(emoji: str) -> int | None:
    """Return the re-fire delta in seconds for a snooze emoji, or None."""
    return SNOOZE_DELTAS_SECONDS.get(emoji)


SNOOZE_EMOJIS: tuple[str, str, str] = ("⏰", "⏭️", "\U0001f4c5")
"""Emojis the bot adds to a delivered reminder, in display order."""
