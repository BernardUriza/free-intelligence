"""`[REMIND:]` marker contract — parse, strip, temporal resolve, persist.

Mutator rule (.claude/rules/robustness.md): every parser lands with the positive
case it exists for AND the resistance case it must survive (a malformed marker, a
past time, a storage failure — none of which may take the turn down).
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

from khimeras_shared.remind_marker import (
    RemindRequest,
    parse_remind,
    persist_remind,
    resolve_remind_when,
    strip_reminds,
)

# --------------------------------------------------------------------------
# parse_remind
# --------------------------------------------------------------------------


def test_parse_extracts_when_and_what():
    req = parse_remind("Va. [REMIND: +2h | sacar la ropa de la lavadora]")
    assert req == RemindRequest(when_raw="+2h", description="sacar la ropa de la lavadora", recurring="none")


def test_parse_extracts_recurring_segment():
    req = parse_remind("[REMIND: 2026-08-01T09:00:00 | tomar el ARV | diario]")
    assert req is not None
    assert req.recurring == "daily"


def test_parse_unknown_recurring_degrades_to_none():
    """RESISTANCE: a recurrence word we don't know must not drop the reminder."""
    req = parse_remind("[REMIND: +1d | algo | cada luna llena]")
    assert req is not None
    assert req.recurring == "none"


def test_parse_returns_none_without_marker():
    assert parse_remind("Nada que agendar aquí.") is None


def test_parse_skips_marker_without_separator():
    """RESISTANCE: a marker with no `|` is malformed — never a half reminder."""
    assert parse_remind("[REMIND: mañana temprano]") is None


def test_parse_skips_empty_segments():
    assert parse_remind("[REMIND: | ]") is None
    assert parse_remind("[REMIND: +2h | ]") is None


def test_parse_takes_only_the_first_valid_marker():
    """One reminder per turn — a second marker is a model stutter, not two rows."""
    req = parse_remind("[REMIND: +1h | uno] y [REMIND: +2h | dos]")
    assert req is not None
    assert req.description == "uno"


def test_parse_truncates_an_overlong_description():
    req = parse_remind(f"[REMIND: +1h | {'x' * 400}]")
    assert req is not None
    assert len(req.description) <= 301
    assert req.description.endswith("…")


# --------------------------------------------------------------------------
# strip_reminds
# --------------------------------------------------------------------------


def test_strip_removes_marker_and_collapses_hole():
    assert strip_reminds("Ok. [REMIND: +2h | algo] listo.") == "Ok. listo."


def test_strip_without_marker_is_untouched():
    """RESISTANCE: text with no marker survives byte-for-byte (modulo strip)."""
    assert strip_reminds("Texto normal sin marcadores.") == "Texto normal sin marcadores."


def test_strip_empty_is_safe():
    assert strip_reminds("") == ""


# --------------------------------------------------------------------------
# resolve_remind_when
# --------------------------------------------------------------------------


def test_resolve_relative_seconds():
    ts = resolve_remind_when("+7200")
    assert ts is not None
    assert abs(ts - (time.time() + 7200)) < 5


def test_resolve_relative_units():
    now = time.time()
    for raw, expected in (("+30m", 1800), ("+2h", 7200), ("+1d", 86400), ("3 dias", 259200)):
        ts = resolve_remind_when(raw)
        assert ts is not None, raw
        assert abs(ts - (now + expected)) < 5, raw


def test_resolve_absolute_iso_in_the_future():
    future = datetime_iso_in_days(30)
    ts = resolve_remind_when(future)
    assert ts is not None
    assert ts > time.time()


def test_resolve_rejects_a_past_absolute_time():
    """RESISTANCE: a reminder in the past is never schedulable — reject, don't fire."""
    assert resolve_remind_when("2020-01-01T09:00:00") is None


def test_resolve_rejects_garbage_and_empty():
    assert resolve_remind_when("mañana tempranito") is None
    assert resolve_remind_when("") is None
    assert resolve_remind_when("+0h") is None


def datetime_iso_in_days(days: int) -> str:
    from datetime import datetime, timedelta

    return (datetime.now() + timedelta(days=days)).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------
# persist_remind
# --------------------------------------------------------------------------


async def test_persist_saves_the_row_with_resolved_time():
    memory = MagicMock()
    memory.save_reminder = AsyncMock(return_value=77)
    req = RemindRequest(when_raw="+2h", description="sacar la ropa", recurring="none")

    reminder_id = await persist_remind(req, memory=memory, channel_id="C1", guild_id="G1", created_by="U1")

    assert reminder_id == 77
    kwargs = memory.save_reminder.await_args.kwargs
    assert kwargs["channel_id"] == "C1"
    assert kwargs["created_by"] == "U1"
    assert kwargs["description"] == "sacar la ropa"
    assert kwargs["mention_user_ids"] == "U1"
    assert abs(kwargs["remind_at"] - (time.time() + 7200)) < 5


async def test_persist_skips_save_on_an_unresolvable_time():
    """RESISTANCE: an unparseable `<when>` never writes a garbage row."""
    memory = MagicMock()
    memory.save_reminder = AsyncMock()
    req = RemindRequest(when_raw="cuando salga la luna", description="algo")

    assert await persist_remind(req, memory=memory, channel_id="C1", guild_id=None, created_by="U1") is None
    memory.save_reminder.assert_not_awaited()


async def test_persist_swallows_a_storage_failure():
    """RESISTANCE: a dead DB must never raise into the turn — log and degrade."""
    memory = MagicMock()
    memory.save_reminder = AsyncMock(side_effect=RuntimeError("pg down"))
    req = RemindRequest(when_raw="+1h", description="algo")

    assert await persist_remind(req, memory=memory, channel_id="C1", guild_id=None, created_by="U1") is None
