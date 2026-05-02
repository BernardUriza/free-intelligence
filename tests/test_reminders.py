"""Tests for insult.core.reminders — tool schemas, parsing, and formatting."""

import time
from datetime import UTC

import pytest

from insult.core.reminders import (
    REMINDER_TOOLS,
    compute_next_occurrence,
    detect_reminder_intent,
    format_reminder_list,
    parse_remind_at,
)


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


class TestFormatReminderList:
    def test_empty_list(self):
        result = format_reminder_list([])
        assert "No hay recordatorios" in result

    def test_single_reminder(self):
        reminders = [
            {
                "id": 1,
                "description": "ir al doctor",
                "remind_at": 1700000000.0,
                "recurring": "none",
                "mention_user_ids": "",
            }
        ]
        result = format_reminder_list(reminders)
        assert "#1" in result
        assert "ir al doctor" in result

    def test_recurring_label(self):
        reminders = [
            {
                "id": 2,
                "description": "ejercicio",
                "remind_at": 1700000000.0,
                "recurring": "daily",
                "mention_user_ids": "",
            }
        ]
        result = format_reminder_list(reminders)
        assert "diario" in result

    def test_mention_user_ids(self):
        reminders = [
            {
                "id": 3,
                "description": "reunion",
                "remind_at": 1700000000.0,
                "recurring": "none",
                "mention_user_ids": "123,456",
            }
        ]
        result = format_reminder_list(reminders)
        assert "<@123>" in result
        assert "<@456>" in result

    def test_multiple_reminders(self):
        reminders = [
            {
                "id": 1,
                "description": "cosa 1",
                "remind_at": 1700000000.0,
                "recurring": "none",
                "mention_user_ids": "",
            },
            {
                "id": 2,
                "description": "cosa 2",
                "remind_at": 1700100000.0,
                "recurring": "weekly",
                "mention_user_ids": "789",
            },
        ]
        result = format_reminder_list(reminders)
        assert "#1" in result
        assert "#2" in result
        assert "cosa 1" in result
        assert "cosa 2" in result


class TestToolSchemas:
    def test_three_tools_defined(self):
        assert len(REMINDER_TOOLS) == 3

    def test_tool_names(self):
        names = {t["name"] for t in REMINDER_TOOLS}
        assert names == {"create_reminder", "list_reminders", "cancel_reminder"}

    def test_create_reminder_required_fields(self):
        create = next(t for t in REMINDER_TOOLS if t["name"] == "create_reminder")
        required = create["input_schema"]["required"]
        assert "description" in required
        assert "remind_at" in required

    def test_list_reminders_required_fields(self):
        list_tool = next(t for t in REMINDER_TOOLS if t["name"] == "list_reminders")
        assert "channel_id" in list_tool["input_schema"]["required"]

    def test_cancel_reminder_required_fields(self):
        cancel = next(t for t in REMINDER_TOOLS if t["name"] == "cancel_reminder")
        assert "reminder_id" in cancel["input_schema"]["required"]

    def test_all_tools_have_description(self):
        for tool in REMINDER_TOOLS:
            assert "description" in tool
            assert len(tool["description"]) > 10

    def test_recurring_enum_values(self):
        create = next(t for t in REMINDER_TOOLS if t["name"] == "create_reminder")
        recurring_prop = create["input_schema"]["properties"]["recurring"]
        assert set(recurring_prop["enum"]) == {"none", "daily", "weekly", "monthly"}
