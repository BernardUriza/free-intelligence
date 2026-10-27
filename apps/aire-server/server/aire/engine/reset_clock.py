"""When a burned pool REOPENS, read off the notice itself. A flat cooldown
re-probes a slot that is still burned (session limits reset hours out) or
leaves a refilled pool idle while the card pays — the notice already says when
the pool reopens, so the slot cools exactly that long (#31). Only Claude's
notices carry a clock today; a Codex `turn.failed` carries none and falls to
the rotor's default cooldown."""

import re
from datetime import datetime, timedelta, timezone

RESET_MARGIN_S = 60.0
RESET_HORIZON_S = 8 * 86400.0
# "resets Aug 10, 8pm (UTC)" (weekly) and "resets 11:20pm (UTC)" (session).
RESET_AT = re.compile(
    r"resets\s+(?:(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2}),\s+)?"
    r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<ampm>am|pm)\s*\(UTC\)",
    re.IGNORECASE)


def reset_delay_s(text: str | None, now: datetime | None = None) -> float | None:
    """Seconds until the reset the notice CARRIES, or None when it carries none
    (or names a day past the horizon — a stale notice must not freeze a slot)."""
    match = RESET_AT.search(text or "")
    if not match:
        return None
    now = now or datetime.now(timezone.utc)
    hour = int(match["hour"]) % 12 + (12 if match["ampm"].lower() == "pm" else 0)
    minute = int(match["minute"] or 0)
    if match["mon"]:
        stamp = f"{match['mon']} {match['day']} {now.year}"
        try:
            day = datetime.strptime(stamp, "%b %d %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        if day.date() < (now - timedelta(days=1)).date():
            day = day.replace(year=now.year + 1)
    else:
        day = now
    at = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if at <= now:
        at += timedelta(days=1)
    delay = (at - now).total_seconds() + RESET_MARGIN_S
    return delay if delay <= RESET_HORIZON_S else None
