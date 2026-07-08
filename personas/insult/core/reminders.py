"""Reminder system — time resolution, intent detection, recurrence math.

Users ask for reminders in natural conversation; the persona emits a
`[REMIND: <when> | <what>]` marker (parsed by `cogs/chat/reminds.py`) that
persists via `memory.save_reminder`. Reminders are stored in Postgres and
delivered by the background loops in `tasks/reminders.py`. The old
create/list/cancel tool schemas died with the runner cutover — the agent
runner returns `tool_calls=[]`, so a tool definition could never fire.
"""

import re
from datetime import UTC, datetime

import structlog

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Ack timing constants — used by the bot's overdue-ack sweep
# ---------------------------------------------------------------------------

ACK_TIMEOUT_SECONDS: float = 1800.0
"""How long to wait for a ✅ reaction before re-firing a requires_ack reminder."""

ACK_MAX_RETRIES: int = 1
"""Maximum number of re-fires per reminder. 1 = original + one re-fire, then stop."""


# ---------------------------------------------------------------------------
# Intent detection — safety net for silent tool failures
# ---------------------------------------------------------------------------

# High-confidence patterns: the user explicitly asked for a reminder/agenda.
# Low-confidence phrases ("no se me olvide", "avísame") are intentionally
# excluded — the false-positive cost (nudging when the user didn't want
# formal scheduling) outweighs the benefit. The use case for this detector
# is to catch the v3.7.2-class bug: tool flow rejected by the API, fallback
# strips all tools, the bot replies in prose as if everything is fine, and
# the user has no signal that the reminder was eaten. The original prompt
# Bernard sent that surfaced the bug starts with "Recuérdame en un reminder
# hacer eso el lunes" — both `recuérdame` and `reminder` patterns hit it.
_REMINDER_INTENT_RE = re.compile(
    r"\b(?:"
    r"recu[eé]rda(?:me|nos)|recuerdame|recordame|"
    r"(?:p[oó]n|ag[eé]nda|m[eé]te)(?:me|nos)\s+(?:un|el|una)?\s*(?:reminder|recordatorio)|"
    r"(?:reminder|recordatorio)\s+(?:para|de|en)\s|"
    r"set\s+(?:an?\s+)?reminder"
    r")\b",
    re.IGNORECASE,
)


def detect_reminder_intent(text: str) -> bool:
    """Return True if the user's message clearly asks the bot to create a reminder.

    Used after an LLM turn to detect the case where the model failed to emit
    a `[REMIND:]` marker despite an obvious request. Without this detector
    that failure mode is silent: the bot replies as if everything is fine and
    the user only notices when the reminder never fires.
    """
    return bool(_REMINDER_INTENT_RE.search(text))


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def parse_remind_at(iso_str: str) -> float | None:
    """Parse an ISO 8601 datetime string to Unix timestamp.

    Returns None if the string is invalid or the time is in the past.
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        # If no timezone info, assume Mexico City (UTC-6)
        if dt.tzinfo is None:
            from zoneinfo import ZoneInfo

            dt = dt.replace(tzinfo=ZoneInfo("America/Mexico_City"))
        ts = dt.timestamp()
        # Reject times in the past (with 60s grace period for processing delay)
        import time

        if ts < time.time() - 60:
            log.warning("reminder_past_time", iso_str=iso_str, timestamp=ts)
            return None
        return ts
    except (ValueError, OverflowError) as e:
        log.warning("reminder_parse_failed", iso_str=iso_str, error=str(e))
        return None


def resolve_remind_at(iso_str: str | None, in_seconds: int | None) -> float | None:
    """Resolve `remind_at` from one of two inputs: an ISO 8601 string or a
    relative delta in seconds. Returns Unix timestamp or None if both inputs
    are absent/invalid.

    The relative path exists to sidestep a recurring LLM mistake: when the
    user says "en 2 horas" the model has to compute now+2h, format ISO,
    pick the right tz offset (DST-aware), and not fat-finger any of it.
    Passing a raw delta lets the model skip the formatting entirely and
    move the conversion responsibility into Python's `time.time() + delta`.
    """
    import time

    if iso_str:
        ts = parse_remind_at(iso_str)
        if ts is not None:
            return ts
    if in_seconds is not None and in_seconds > 0:
        return time.time() + in_seconds
    return None


def compute_next_occurrence(remind_at: float, recurring: str) -> float | None:
    """Compute the next fire time for a recurring reminder.

    Args:
        remind_at: Current fire time as Unix timestamp.
        recurring: One of 'daily', 'weekly', 'monthly', 'none'.

    Returns:
        Next fire time as Unix timestamp, or None if not recurring.
    """
    if recurring == "none":
        return None

    dt = datetime.fromtimestamp(remind_at, tz=UTC)

    if recurring == "daily":
        from datetime import timedelta

        next_dt = dt + timedelta(days=1)
    elif recurring == "weekly":
        from datetime import timedelta

        next_dt = dt + timedelta(weeks=1)
    elif recurring == "monthly":
        # Add one month (handle month overflow)
        month = dt.month + 1
        year = dt.year
        if month > 12:
            month = 1
            year += 1
        # Clamp day to max days in the target month
        import calendar

        max_day = calendar.monthrange(year, month)[1]
        day = min(dt.day, max_day)
        next_dt = dt.replace(year=year, month=month, day=day)
    else:
        return None

    return next_dt.timestamp()
