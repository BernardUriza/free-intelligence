"""Reminder-creation marker parser — `[REMIND:]` extraction, stripping, firing.

Mirrors the `[INVITE:]` pipeline in `invites.py`. The persona emits
`[REMIND: <when> | <what>]` (optional third segment: `daily`/`weekly`/`monthly`)
when the user asks to be reminded of something. This module:

- `parse_remind(text)`: extract the reminder request (one per turn)
- `strip_reminds(text)`: remove the markers before sending to Discord
- `fire_remind(request, ...)`: persist via the existing reminders storage
  (`memory.save_reminder`) so the delivery loop in `tasks/reminders.py`
  fires it — best-effort in the background

Why a marker and not a structured tool call: every Insult turn runs on the
persona-runner and `AgentRunnerClient` returns `tool_calls=[]`, so the old
`create_reminder` tool schema could never fire from a runner turn. Markers
are the canonical in-band channel for runner→plumbing intents (`[REACT:]`,
`[REMEMBER:]`, `[INVITE:]`); this extends the same contract to reminders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

from personas.insult.core.reminders import resolve_remind_at

log = structlog.get_logger()

REMIND_PATTERN = re.compile(r"\[REMIND:([^\]]*)\]", re.IGNORECASE)
MAX_DESCRIPTION_LEN = 300

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

FAILED_SCHEDULE_NOTICE = "*(no agendé ese recordatorio — la hora no me cuadró. Dame día y hora exactos.)*"


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

    Same conservative cleanup as `strip_invites`: removes the marker and
    collapses the multi-space / multi-newline holes the removal leaves.
    """
    if not response:
        return response
    cleaned = REMIND_PATTERN.sub("", response)
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def resolve_remind_when(when_raw: str) -> float | None:
    """Resolve the marker's `<when>` segment to a Unix timestamp.

    Two accepted shapes, reusing `resolve_remind_at` from the reminders core:
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
        return resolve_remind_at(None, amount * multiplier)
    return resolve_remind_at(when, None)


async def fire_remind(
    request: RemindRequest,
    *,
    memory,
    bot,
    channel,
    guild_id: str | None,
    created_by: str,
) -> int | None:
    """Persist the reminder so the existing 30s delivery loop fires it.

    Mentions the requesting user when it fires. Best-effort: an unparseable
    time or a storage failure sends a short in-character correction to the
    channel (the visible turn already promised the reminder — staying silent
    would be a fake-green) and returns None; nothing here ever raises.
    """
    channel_id = str(channel.id)
    remind_at = resolve_remind_when(request.when_raw)
    if remind_at is None:
        log.warning(
            "remind_marker_invalid_time",
            channel_id=channel_id,
            when_raw=request.when_raw[:80],
            description_preview=request.description[:80],
        )
        await _notify_schedule_failure(channel)
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
        )
    except Exception:
        log.exception(
            "remind_marker_save_failed",
            channel_id=channel_id,
            description_preview=request.description[:80],
        )
        await _notify_schedule_failure(channel)
        return None

    log.info(
        "remind_marker_fired",
        reminder_id=reminder_id,
        channel_id=channel_id,
        remind_at=remind_at,
        recurring=request.recurring,
        description_preview=request.description[:80],
    )

    if guild_id:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from personas.insult.core.guild_setup import post_reminder_set

        remind_at_str = datetime.fromtimestamp(remind_at, tz=ZoneInfo("America/Mexico_City")).isoformat()
        try:
            await post_reminder_set(
                bot,
                memory,
                guild_id,
                request.description,
                remind_at_str,
                f"<@{created_by}>",
                request.recurring,
                reminder_id,
            )
        except Exception:
            log.exception("remind_marker_sidechannel_post_failed", reminder_id=reminder_id)

    return reminder_id


async def _notify_schedule_failure(channel) -> None:
    try:
        await channel.send(FAILED_SCHEDULE_NOTICE)
    except Exception:
        log.warning("remind_marker_failure_notice_failed", channel_id=getattr(channel, "id", None))
