"""Reminder system — tool schemas, parsing, and formatting.

Users ask for reminders in natural conversation, Claude detects the intent
and calls create_reminder / list_reminders / cancel_reminder tools.
Reminders are stored in SQLite and delivered by a background task in bot.py.
"""

import re
from datetime import UTC, datetime

import structlog

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Tool definitions for Claude API
# ---------------------------------------------------------------------------

REMINDER_TOOLS = [
    {
        "name": "create_reminder",
        "description": (
            "Set a reminder for the group or a specific user. Use this when someone asks to be reminded "
            "of something. You MUST provide remind_at as an ISO 8601 datetime string with timezone offset "
            "for Mexico City (-06:00 or -05:00 depending on DST). The current time is provided in the system prompt. "
            "Examples: '2026-04-09T09:00:00-06:00', '2026-04-03T14:30:00-06:00'. "
            "Always confirm the reminder in your response so the user knows when they'll be reminded."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "What to remind about (e.g. 'ir al gastroenterologo', 'entregar el proyecto')",
                },
                "remind_at": {
                    "type": "string",
                    "description": (
                        "ISO 8601 datetime with timezone offset for when to send the reminder "
                        "(e.g. '2026-04-09T09:00:00-06:00')"
                    ),
                },
                "mention_user_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Discord user IDs to mention when reminder fires. Empty = remind the whole channel.",
                },
                "recurring": {
                    "type": "string",
                    "enum": ["none", "daily", "weekly", "monthly"],
                    "description": "Recurrence pattern. Default is 'none' (one-time).",
                },
            },
            "required": ["description", "remind_at"],
        },
    },
    {
        "name": "list_reminders",
        "description": (
            "List all pending reminders for this channel. Use when someone asks 'que recordatorios hay?' or similar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "The channel ID to list reminders for (use the current channel)",
                },
            },
            "required": ["channel_id"],
        },
    },
    {
        "name": "cancel_reminder",
        "description": (
            "Cancel a pending reminder by its ID. Use when someone says "
            "'cancela el recordatorio del doctor' or similar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reminder_id": {
                    "type": "integer",
                    "description": "The ID of the reminder to cancel",
                },
            },
            "required": ["reminder_id"],
        },
    },
]


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

    Used after an LLM turn to detect the case where the model failed to call
    `create_reminder` despite an obvious request — typically because the API
    rejected the tool schema and the BadRequest fallback stripped all tools.
    Without this detector that failure mode is silent: the bot replies as if
    everything is fine and the user only notices when the reminder never fires.
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


def format_reminder_list(reminders: list[dict]) -> str:
    """Format a list of reminders for display in Discord.

    Returns a human-readable string listing all reminders.
    """
    if not reminders:
        return "No hay recordatorios pendientes."

    lines = []
    for r in reminders:
        dt = datetime.fromtimestamp(r["remind_at"], tz=UTC)
        # Convert to Mexico City time for display
        from zoneinfo import ZoneInfo

        dt_mx = dt.astimezone(ZoneInfo("America/Mexico_City"))
        time_str = dt_mx.strftime("%d/%m/%Y %H:%M")

        recurring_label = ""
        if r.get("recurring", "none") != "none":
            labels = {"daily": "diario", "weekly": "semanal", "monthly": "mensual"}
            recurring_label = f" ({labels.get(r['recurring'], r['recurring'])})"

        mentions = ""
        if r.get("mention_user_ids"):
            user_ids = r["mention_user_ids"].split(",")
            mentions = " → " + ", ".join(f"<@{uid.strip()}>" for uid in user_ids if uid.strip())

        lines.append(f"**#{r['id']}** — {r['description']} — {time_str}{recurring_label}{mentions}")

    return "\n".join(lines)
