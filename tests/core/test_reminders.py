"""Tests for insult.core.reminders — time resolution, intent detection, recurrence."""

import time
from datetime import UTC

import pytest

from personas.insult.core.reminders import (
    ACK_MAX_RETRIES,
    ACK_TIMEOUT_SECONDS,
    compute_next_occurrence,
    detect_reminder_intent,
    parse_remind_at,
    resolve_remind_at,
)


class TestAckConstants:
    def test_timeout_is_positive(self):
        assert ACK_TIMEOUT_SECONDS > 0

    def test_max_retries_is_positive(self):
        # 1 means "fire once more after the original" — bumping this above 2
        # turns reminders into spam. Pin at 1 unless the policy changes.
        assert ACK_MAX_RETRIES >= 1
        assert ACK_MAX_RETRIES <= 2


class TestResolveRemindAt:
    def test_iso_path_takes_priority(self):
        ts = resolve_remind_at("2099-06-15T10:00:00-06:00", 60)
        assert ts is not None
        assert ts > time.time() + 86400  # far future, not now+60s

    def test_falls_back_to_in_seconds_when_iso_invalid(self):
        before = time.time()
        ts = resolve_remind_at("not-a-date", 120)
        assert ts is not None
        assert before + 119 <= ts <= before + 122

    def test_in_seconds_alone(self):
        before = time.time()
        ts = resolve_remind_at(None, 600)
        assert ts is not None
        assert before + 599 <= ts <= before + 602

    def test_both_none_returns_none(self):
        assert resolve_remind_at(None, None) is None

    def test_iso_past_falls_through_to_in_seconds(self):
        before = time.time()
        ts = resolve_remind_at("2000-01-01T00:00:00-06:00", 30)
        assert ts is not None
        assert before + 29 <= ts <= before + 32

    def test_zero_or_negative_in_seconds_rejected(self):
        assert resolve_remind_at(None, 0) is None
        assert resolve_remind_at(None, -10) is None


class TestDetectReminderIntent:
    @pytest.mark.parametrize(
        "text",
        [
            "Recuérdame mañana ir a comprar sertralina",
            "recuerdame en un reminder hacer eso el lunes",
            "Recordame eso por favor",
            "Ponme un reminder para mañana",
            "ponme un recordatorio de la junta",
            "Agéndame un reminder",
            "agendame el recordatorio de la dentista",
            "set a reminder for tomorrow",
            "set reminder to call mom",
            "Reminder para el lunes a las 9",
            "recordatorio de la junta de mañana",
        ],
    )
    def test_matches_clear_intents(self, text):
        assert detect_reminder_intent(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "Ya está, gracias",
            "que no se me olvide la junta",
            "te recuerdo a tu primo",
            "yo recuerdo cuando éramos chicos",
            "el reminder #4 ya está duplicado",
            "cancela el recordatorio 5",
            "avísame cuando llegues",
        ],
    )
    def test_skips_low_confidence_or_unrelated(self, text):
        assert detect_reminder_intent(text) is False


class TestParseRemindAt:
    def test_valid_iso_with_timezone(self):
        """Parses a valid ISO 8601 string with timezone offset."""
        # Use a far-future date to avoid "past time" rejection
        ts = parse_remind_at("2099-06-15T10:00:00-06:00")
        assert ts is not None
        assert isinstance(ts, float)
        assert ts > time.time()

    def test_valid_iso_utc(self):
        ts = parse_remind_at("2099-12-31T23:59:59+00:00")
        assert ts is not None

    def test_rejects_past_time(self):
        """Times in the past should return None."""
        ts = parse_remind_at("2020-01-01T00:00:00-06:00")
        assert ts is None

    def test_rejects_invalid_string(self):
        ts = parse_remind_at("not-a-date")
        assert ts is None

    def test_rejects_empty_string(self):
        ts = parse_remind_at("")
        assert ts is None

    def test_naive_datetime_gets_timezone(self):
        """Naive datetimes (no TZ) should still parse with assumed Mexico City TZ."""
        ts = parse_remind_at("2099-06-15T10:00:00")
        assert ts is not None


class TestComputeNextOccurrence:
    def test_daily(self):
        base = 1700000000.0  # Some arbitrary timestamp
        next_ts = compute_next_occurrence(base, "daily")
        assert next_ts is not None
        assert next_ts == pytest.approx(base + 86400, abs=1)

    def test_weekly(self):
        base = 1700000000.0
        next_ts = compute_next_occurrence(base, "weekly")
        assert next_ts is not None
        assert next_ts == pytest.approx(base + 7 * 86400, abs=1)

    def test_monthly(self):
        base = 1700000000.0  # 2023-11-14 roughly
        next_ts = compute_next_occurrence(base, "monthly")
        assert next_ts is not None
        assert next_ts > base
        # Should be roughly 30 days later
        assert next_ts - base > 25 * 86400
        assert next_ts - base < 35 * 86400

    def test_monthly_handles_month_overflow(self):
        """December -> January should wrap to next year."""
        from datetime import datetime

        # Dec 15, 2025
        dt = datetime(2025, 12, 15, 12, 0, 0, tzinfo=UTC)
        base = dt.timestamp()
        next_ts = compute_next_occurrence(base, "monthly")
        assert next_ts is not None
        next_dt = datetime.fromtimestamp(next_ts, tz=UTC)
        assert next_dt.month == 1
        assert next_dt.year == 2026

    def test_monthly_clamps_day(self):
        """Jan 31 -> Feb should clamp to Feb 28/29."""
        from datetime import datetime

        dt = datetime(2025, 1, 31, 12, 0, 0, tzinfo=UTC)
        base = dt.timestamp()
        next_ts = compute_next_occurrence(base, "monthly")
        assert next_ts is not None
        next_dt = datetime.fromtimestamp(next_ts, tz=UTC)
        assert next_dt.month == 2
        assert next_dt.day == 28

    def test_none_returns_none(self):
        assert compute_next_occurrence(1700000000.0, "none") is None

    def test_invalid_recurring_returns_none(self):
        assert compute_next_occurrence(1700000000.0, "invalid") is None
