"""`[REMIND:]` marker — parse, strip, resolve, fire, and truncation rescue.

The runner path cannot emit structured tool calls (`AgentRunnerClient` returns
`tool_calls=[]`), so reminder CREATION rides an in-band marker mirroring
`[REACT:]`/`[REMEMBER:]`/`[INVITE:]`. The old `create_reminder` tool schema was
dead theater and got deleted. Mutator rule (robustness.md): positive cases +
resistance cases for every parser.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from personas.insult.cogs.chat import reminds
from personas.insult.cogs.chat.reminds import (
    RemindRequest,
    fire_remind,
    parse_remind,
    resolve_remind_when,
    strip_reminds,
)
from personas.insult.core.character.formatting import enforce_length_variation


class TestParseRemind:
    def test_extracts_when_and_description(self):
        text = "Va. En 2 minutos te grito. [REMIND: +2m | revisar el horno]"
        parsed = parse_remind(text)
        assert parsed == RemindRequest(when_raw="+2m", description="revisar el horno")

    def test_case_insensitive(self):
        parsed = parse_remind("[remind: +1h | sacar la ropa]")
        assert parsed is not None
        assert parsed.description == "sacar la ropa"

    def test_iso_when_segment(self):
        parsed = parse_remind("Agendado. [REMIND: 2099-07-08T09:00:00-06:00 | junta de las 9]")
        assert parsed is not None
        assert parsed.when_raw == "2099-07-08T09:00:00-06:00"

    def test_recurring_third_segment(self):
        parsed = parse_remind("[REMIND: +1d | tomar la quetiapina | daily]")
        assert parsed is not None
        assert parsed.recurring == "daily"

    def test_recurring_spanish_alias(self):
        parsed = parse_remind("[REMIND: +1d | ejercicio | diario]")
        assert parsed is not None
        assert parsed.recurring == "daily"

    def test_unknown_recurring_falls_back_to_none(self):
        """RESISTANCE: a hallucinated recurrence must not corrupt storage."""
        parsed = parse_remind("[REMIND: +1d | ejercicio | cada rato]")
        assert parsed is not None
        assert parsed.recurring == "none"

    def test_no_marker_returns_none(self):
        assert parse_remind("Ya. Te aviso.") is None

    def test_missing_pipe_is_invalid(self):
        """RESISTANCE: a marker without the when|what split must not fire."""
        assert parse_remind("[REMIND: revisar el horno en 2 minutos]") is None

    def test_empty_segments_are_invalid(self):
        assert parse_remind("[REMIND: | revisar]") is None
        assert parse_remind("[REMIND: +2m | ]") is None
        assert parse_remind("[REMIND:]") is None

    def test_multiple_markers_only_first_fires(self):
        """RESISTANCE: two markers are a model stutter, not two reminders."""
        text = "[REMIND: +2m | primero] y [REMIND: +5m | segundo]"
        parsed = parse_remind(text)
        assert parsed is not None
        assert parsed.description == "primero"

    def test_long_description_truncated(self):
        parsed = parse_remind(f"[REMIND: +2m | {'x' * 500}]")
        assert parsed is not None
        assert len(parsed.description) <= reminds.MAX_DESCRIPTION_LEN + 1


class TestStripReminds:
    def test_removes_marker_preserves_text(self):
        text = "Va. En 2 minutos te grito. [REMIND: +2m | revisar el horno] No lo quemes."
        assert strip_reminds(text) == "Va. En 2 minutos te grito. No lo quemes."

    def test_marker_only_response_becomes_empty(self):
        assert strip_reminds("[REMIND: +2m | horno]") == ""

    def test_no_marker_untouched(self):
        assert strip_reminds("sin marcador aquí") == "sin marcador aquí"

    def test_strips_malformed_marker_too(self):
        """Even an unparseable marker must never leak to the channel."""
        assert strip_reminds("ok [REMIND: sin pipe] listo") == "ok listo"

    @pytest.mark.asyncio
    async def test_mutation_port_strips_remind_markers(self):
        from personas.insult.composition import default_output_mutation_port

        port = default_output_mutation_port()
        out = await port.mutate(
            "Ya quedó. [REMIND: +2m | revisar el horno]",
            user_text="recuérdame en 2 minutos el horno",
            recent_response_lengths=[],
            recent_openers=[],
        )
        assert "[REMIND:" not in out
        assert "Ya quedó." in out


class TestResolveRemindWhen:
    def test_relative_minutes(self):
        before = time.time()
        ts = resolve_remind_when("+2m")
        assert ts is not None
        assert before + 119 <= ts <= before + 122

    def test_relative_hours_and_days(self):
        before = time.time()
        assert resolve_remind_when("+2h") == pytest.approx(before + 7200, abs=3)
        assert resolve_remind_when("+1d") == pytest.approx(before + 86400, abs=3)

    def test_bare_number_is_seconds(self):
        before = time.time()
        ts = resolve_remind_when("+7200")
        assert ts == pytest.approx(before + 7200, abs=3)

    def test_iso_absolute(self):
        ts = resolve_remind_when("2099-07-08T09:00:00-06:00")
        assert ts is not None
        assert ts > time.time() + 86400

    def test_past_iso_rejected(self):
        assert resolve_remind_when("2020-01-01T09:00:00-06:00") is None

    def test_garbage_rejected(self):
        """RESISTANCE: natural language the parser doesn't cover → None,
        never a silently-wrong timestamp."""
        assert resolve_remind_when("mañana en la tarde") is None
        assert resolve_remind_when("") is None
        assert resolve_remind_when("+0m") is None


def _mk_channel() -> MagicMock:
    channel = MagicMock()
    channel.id = 1489180895264116736
    channel.send = AsyncMock(return_value=None)
    return channel


class TestFireRemind:
    @pytest.mark.asyncio
    async def test_saves_via_existing_storage_and_mentions_author(self, monkeypatch):
        memory = MagicMock()
        memory.save_reminder = AsyncMock(return_value=7)
        post = AsyncMock()
        monkeypatch.setattr("personas.insult.core.guild_setup.post_reminder_set", post)

        reminder_id = await fire_remind(
            RemindRequest(when_raw="+2m", description="revisar el horno"),
            memory=memory,
            bot=MagicMock(),
            channel=_mk_channel(),
            guild_id="1488419218302042223",
            created_by="907264175246569543",
        )

        assert reminder_id == 7
        memory.save_reminder.assert_awaited_once()
        kwargs = memory.save_reminder.call_args.kwargs
        assert kwargs["description"] == "revisar el horno"
        assert kwargs["mention_user_ids"] == "907264175246569543"
        assert kwargs["recurring"] == "none"
        assert kwargs["remind_at"] == pytest.approx(time.time() + 120, abs=5)
        post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_time_saves_nothing_and_corrects_in_channel(self):
        """RESISTANCE: the visible turn already promised the reminder — an
        unparseable time must produce an honest correction, never silence."""
        memory = MagicMock()
        memory.save_reminder = AsyncMock()
        channel = _mk_channel()

        reminder_id = await fire_remind(
            RemindRequest(when_raw="cuando puedas", description="algo"),
            memory=memory,
            bot=MagicMock(),
            channel=channel,
            guild_id=None,
            created_by="1",
        )

        assert reminder_id is None
        memory.save_reminder.assert_not_awaited()
        channel.send.assert_awaited_once_with(reminds.FAILED_SCHEDULE_NOTICE)

    @pytest.mark.asyncio
    async def test_storage_failure_is_swallowed_and_corrected(self):
        """RESISTANCE: a dead data plane must never blow up the delivered turn."""
        memory = MagicMock()
        memory.save_reminder = AsyncMock(side_effect=RuntimeError("pg down"))
        channel = _mk_channel()

        reminder_id = await fire_remind(
            RemindRequest(when_raw="+2m", description="algo"),
            memory=memory,
            bot=MagicMock(),
            channel=channel,
            guild_id=None,
            created_by="1",
        )

        assert reminder_id is None
        channel.send.assert_awaited_once_with(reminds.FAILED_SCHEDULE_NOTICE)

    @pytest.mark.asyncio
    async def test_no_guild_skips_sidechannel_post(self, monkeypatch):
        memory = MagicMock()
        memory.save_reminder = AsyncMock(return_value=3)
        post = AsyncMock()
        monkeypatch.setattr("personas.insult.core.guild_setup.post_reminder_set", post)

        reminder_id = await fire_remind(
            RemindRequest(when_raw="+30m", description="dm reminder"),
            memory=memory,
            bot=MagicMock(),
            channel=_mk_channel(),
            guild_id=None,
            created_by="1",
        )

        assert reminder_id == 3
        post.assert_not_awaited()


def test_truncation_rescues_remind_marker_in_tail():
    """The length enforcer must rescue [REMIND:] like REMEMBER/REACT/INVITE —
    a reminder the model promised must not vanish because of a formatting
    heuristic (robustness.md marker-rescue rule)."""
    text = (
        "First sentence. Second sentence. Third sentence. Fourth sentence. "
        "Fifth sentence with [REMIND: +2m | revisar el horno] inside. Sixth sentence."
    )
    result = enforce_length_variation(text, [120, 140, 130])
    assert "[REMIND: +2m | revisar el horno]" in result
