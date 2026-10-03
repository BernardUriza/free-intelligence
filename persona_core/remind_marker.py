"""Reminder-creation marker parser — `[REMIND:]` extraction, stripping, persist.

Shared text util (like `persona_core/reactions.py` / `research_marker.py`):
BOTH the plumbing and the gateway parse this marker off a runner response, so it
lives in `persona_core` — never in a persona package the gateway may not
import.

The persona emits `[REMIND: <when> | <what>]` (optional third segment:
`daily`/`weekly`/`monthly`) when the user asks to be reminded of something. This
module:

- `parse_remind(text)`: extract the reminder request (one per turn)
- `strip_reminds(text)`: remove the markers before sending to Discord
- `resolve_remind_when(when_raw)`: resolve the `<when>` segment to a Unix ts
- `persist_remind(memory, request, ...)`: persist the row via
  `memory.save_reminder` — best-effort, never raises
- `compute_next_occurrence(remind_at, recurring)`: recurrence math for the
  gateway's drain loop (daily/weekly/monthly), skipping missed occurrences

The temporal `<when>` parse is fully self-contained here (relative deltas +
absolute ISO 8601, `datetime`/`zoneinfo` only) — it depends on NO dead module,
so it is resurrected rather than degraded to a raw `when_raw`.

Delivery lives in `persona_gateway.gateway.PersonaClient._reminder_drain`: the
persona that scheduled the row (persona_id) is the one that fires it.
"""

from __future__ import annotations

import calendar
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import structlog

log = structlog.get_logger()

REMIND_PATTERN = re.compile(r"\[REMIND:([^\]]*)\]", re.IGNORECASE)
MAX_DESCRIPTION_LEN = 300

# How many periods a recurring reminder may skip forward to catch up with `now`
# before we give up and stop it. ~3 years of dailies; a gap that big means the
# row is abandoned, not late.
_MAX_RECURRENCE_CATCHUP = 1200

_MEXICO_CITY = ZoneInfo("America/Mexico_City")

_RELATIVE_WHEN_RE = re.compile(
    r"^\+?(\d+)\s*(s|sec|seg|segundos?|m|min|minutos?|h|hr|horas?|d|d[ií]as?|days?)?$",
    re.IGNORECASE,
)

_UNIT_SECONDS = {
    "": 1,
    "s": 1,
    "sec": 1,
    "seg": 1,
    "segundo": 1,
    "segundos": 1,
    "m": 60,
    "min": 60,
    "minuto": 60,
    "minutos": 60,
    "h": 3600,
    "hr": 3600,
    "hora": 3600,
    "horas": 3600,
    "d": 86400,
    "dia": 86400,
    "dias": 86400,
    "día": 86400,
    "días": 86400,
    "day": 86400,
    "days": 86400,
}

_RECURRING_ALIASES = {
    "daily": "daily",
    "diario": "daily",
    "diaria": "daily",
    "weekly": "weekly",
    "semanal": "weekly",
    "monthly": "monthly",
    "mensual": "monthly",
}

_RECURRING_DELTAS = {"daily": 1, "weekly": 7}

__all__ = [
    "MAX_DESCRIPTION_LEN",
    "REMIND_PATTERN",
    "RemindRequest",
    "compute_next_occurrence",
    "parse_remind",
    "persist_remind",
    "resolve_remind_when",
    "strip_reminds",
]


@dataclass(frozen=True)
class RemindRequest:
    when_raw: str
    description: str
    recurring: str = "none"


def parse_remind(response: str) -> RemindRequest | None:
    """Extract the reminder from the FIRST valid `[REMIND: when | what]` marker.

    One reminder per turn: a second marker in the same response is a model
    stutter, not two reminders — parsing them all would double-schedule.
    Returns None when no marker is present or every marker is malformed
    (missing the `|` separator, empty when/what).
    """
    if not response or "[REMIND:" not in response.upper():
        return None
    for match in REMIND_PATTERN.finditer(response):
        body = (match.group(1) or "").strip()
        if "|" not in body:
            continue
        segments = [s.strip() for s in body.split("|")]
        when_raw, description = segments[0], segments[1] if len(segments) > 1 else ""
        if not when_raw or not description:
            continue
        if len(description) > MAX_DESCRIPTION_LEN:
            description = description[:MAX_DESCRIPTION_LEN].rstrip() + "…"
        recurring = "none"
        if len(segments) > 2 and segments[2]:
            recurring = _RECURRING_ALIASES.get(segments[2].lower(), "")
            if not recurring:
                log.warning("remind_marker_unknown_recurring", value=segments[2][:40])
                recurring = "none"
        return RemindRequest(when_raw=when_raw, description=description, recurring=recurring)
    return None


def strip_reminds(response: str) -> str:
    """Remove all `[REMIND:...]` markers from the response text.

    Same conservative cleanup as `strip_reactions`: removes the marker and
    collapses the multi-space / multi-newline holes the removal leaves.
    """
    if not response:
        return response
    cleaned = REMIND_PATTERN.sub("", response)
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _parse_absolute(iso_str: str) -> float | None:
    """Parse an ISO 8601 string to a Unix ts; naive → America/Mexico_City.

    Rejects times in the past (60s grace for processing delay).
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_MEXICO_CITY)
        ts = dt.timestamp()
    except (ValueError, OverflowError) as e:
        log.warning("remind_marker_parse_failed", iso_str=iso_str[:80], error=str(e))
        return None
    if ts < time.time() - 60:
        log.warning("remind_marker_past_time", iso_str=iso_str[:80], timestamp=ts)
        return None
    return ts


def resolve_remind_when(when_raw: str) -> float | None:
    """Resolve the marker's `<when>` segment to a Unix timestamp.

    Two accepted shapes:
    - relative delta: `+7200` (seconds), `+30m`, `+2h`, `+1d` — sidesteps
      timezone/DST math, the shape the persona is told to prefer
    - absolute ISO 8601: `2026-07-08T09:00:00-06:00` (naive → CDMX)

    Returns None when the segment parses to nothing or lands in the past.
    """
    when = (when_raw or "").strip()
    if not when:
        return None
    relative = _RELATIVE_WHEN_RE.match(when)
    if relative:
        amount = int(relative.group(1))
        unit = (relative.group(2) or "").lower()
        multiplier = _UNIT_SECONDS.get(unit)
        if multiplier is None or amount <= 0:
            return None
        return time.time() + amount * multiplier
    return _parse_absolute(when)


def compute_next_occurrence(remind_at: float, recurring: str, *, now: float | None = None) -> float | None:
    """Next fire time for a recurring reminder, or None when it doesn't recur.

    Advances PAST `now` instead of returning the single next slot: a bot that
    was down for three days must not re-fire a daily reminder three times in
    three consecutive ticks (each tick would find it still overdue). One
    delivery, then the schedule resumes in the future.
    """
    if recurring not in _RECURRING_DELTAS and recurring != "monthly":
        return None
    reference = time.time() if now is None else now
    dt = datetime.fromtimestamp(remind_at, tz=_MEXICO_CITY)
    for _ in range(_MAX_RECURRENCE_CATCHUP):
        dt = _advance_one_period(dt, recurring)
        if dt.timestamp() > reference:
            return dt.timestamp()
    log.warning("remind_recurrence_catchup_exhausted", remind_at=remind_at, recurring=recurring)
    return None


def _advance_one_period(dt: datetime, recurring: str) -> datetime:
    days = _RECURRING_DELTAS.get(recurring)
    if days is not None:
        return dt + timedelta(days=days)
    month = dt.month + 1
    year = dt.year
    if month > 12:
        month = 1
        year += 1
    max_day = calendar.monthrange(year, month)[1]
    return dt.replace(year=year, month=month, day=min(dt.day, max_day))


async def persist_remind(
    request: RemindRequest,
    *,
    memory,
    channel_id: str,
    guild_id: str | None,
    created_by: str,
    persona_id: str | None = None,
) -> int | None:
    """Persist the reminder row via `memory.save_reminder`. Best-effort.

    Resolves `<when>` to a timestamp; an unparseable time is logged and skipped
    (returns None) — the visible turn already carried the persona's ack. A
    storage failure is logged and swallowed; nothing here ever raises. Returns
    the reminder id on success, else None.

    `persona_id` stamps ownership: only that persona's gateway loop will deliver
    the row. Omitting it leaves the reminder unowned — no one drains it.
    """
    remind_at = resolve_remind_when(request.when_raw)
    if remind_at is None:
        log.warning(
            "remind_marker_invalid_time",
            channel_id=channel_id,
            when_raw=request.when_raw[:80],
            description_preview=request.description[:80],
        )
        return None
    try:
        reminder_id = await memory.save_reminder(
            channel_id=channel_id,
            guild_id=guild_id,
            created_by=created_by,
            description=request.description,
            remind_at=remind_at,
            mention_user_ids=created_by,
            recurring=request.recurring,
            persona_id=persona_id,
        )
    except Exception:
        log.exception(
            "remind_marker_save_failed",
            channel_id=channel_id,
            description_preview=request.description[:80],
        )
        return None
    log.info(
        "remind_marker_fired",
        reminder_id=reminder_id,
        channel_id=channel_id,
        remind_at=remind_at,
        recurring=request.recurring,
        description_preview=request.description[:80],
    )
    return reminder_id
