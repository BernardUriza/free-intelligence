"""Tests for the process-wide health state singleton (PR 1)."""

from __future__ import annotations

import math
import time
from unittest.mock import MagicMock

import pytest

from insult.core.health_state import HealthState, _reset_for_tests, get_state


@pytest.fixture(autouse=True)
def _isolate_singleton():
    """Reset the module-level singleton between tests so state from one
    case doesn't leak into the next. Without this the ``turns_total``
    accumulator and ``last_turn_at`` survive across tests in the same
    process and assertions become order-dependent."""
    _reset_for_tests()
    yield
    _reset_for_tests()


class TestHealthStateBasics:
    def test_fresh_state_has_no_turns(self):
        s = HealthState()
        assert s.last_turn_age_s() is None
        assert s.last_turn_within(15 * 60) is False
        assert s.last_turn_outcome() is None
        assert s.turns_total() == 0

    def test_uptime_s_is_non_negative(self):
        s = HealthState()
        assert s.uptime_s() >= 0

    def test_record_turn_end_advances_counter(self):
        s = HealthState()
        s.record_turn_end("ok")
        s.record_turn_end("trivial_skipped")
        s.record_turn_end("llm_failed")
        assert s.turns_total() == 3

    def test_record_turn_end_remembers_last_outcome(self):
        s = HealthState()
        s.record_turn_end("ok")
        s.record_turn_end("llm_failed")
        assert s.last_turn_outcome() == "llm_failed"


class TestLastTurnAge:
    def test_zero_immediately_after_record(self):
        s = HealthState()
        s.record_turn_end("ok")
        age = s.last_turn_age_s()
        assert age is not None
        assert age < 0.5  # well under a second

    def test_within_window_after_recent_turn(self):
        s = HealthState()
        s.record_turn_end("ok")
        assert s.last_turn_within(15 * 60) is True
        assert s.last_turn_within(60) is True

    def test_outside_window_for_old_turn(self):
        s = HealthState()
        # Simulate an old turn by writing the internal field directly.
        s._last_turn_at = time.monotonic() - (16 * 60)
        s._turns_total = 1
        assert s.last_turn_within(15 * 60) is False

    def test_within_window_false_when_no_turns_yet(self):
        s = HealthState()
        # Cold start, no turn ever — must NOT report "within window" as a
        # truthy default. False covers both "never" and "stale".
        assert s.last_turn_within(15 * 60) is False
        assert s.last_turn_within(0.0) is False


class TestBotIntegration:
    def test_bot_ref_unset_returns_none(self):
        s = HealthState()
        assert s.is_bot_ready() is None
        assert s.gateway_latency_ms() is None

    def test_bot_ready_propagates(self):
        s = HealthState()
        bot = MagicMock()
        bot.is_ready = MagicMock(return_value=True)
        s.set_bot(bot)
        assert s.is_bot_ready() is True
        bot.is_ready.return_value = False
        assert s.is_bot_ready() is False

    def test_gateway_latency_converts_seconds_to_ms(self):
        s = HealthState()
        bot = MagicMock()
        bot.latency = 0.0184  # 18.4 ms
        s.set_bot(bot)
        assert s.gateway_latency_ms() == 18.4

    def test_gateway_latency_nan_returns_none(self):
        """discord.py uses float('nan') before the first heartbeat."""
        s = HealthState()
        bot = MagicMock()
        bot.latency = math.nan
        s.set_bot(bot)
        assert s.gateway_latency_ms() is None

    def test_gateway_latency_non_numeric_returns_none(self):
        s = HealthState()
        bot = MagicMock()
        bot.latency = "not a number"
        s.set_bot(bot)
        assert s.gateway_latency_ms() is None


class TestSingleton:
    def test_get_state_returns_same_instance(self):
        a = get_state()
        b = get_state()
        assert a is b

    def test_reset_replaces_singleton(self):
        before = get_state()
        before.record_turn_end("ok")
        assert before.turns_total() == 1
        _reset_for_tests()
        after = get_state()
        assert after.turns_total() == 0
        # The new instance has a fresh started_at — older `before` ref
        # is now orphaned and should not affect new state.
        before.record_turn_end("ok")
        assert get_state().turns_total() == 0
