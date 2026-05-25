"""Tests for fi_core.retry — retry-after parsing + Full Jitter backoff."""

from __future__ import annotations

from fi_core.retry import (
    BACKOFF_CAP_429,
    MAX_HONORED_RETRY_AFTER,
    full_jitter_backoff,
    parse_retry_after,
)


def test_parse_prefers_retry_after_ms():
    assert parse_retry_after({"retry-after-ms": "1500"}) == 1.5


def test_parse_falls_back_to_seconds():
    assert parse_retry_after({"retry-after": "3"}) == 3.0


def test_parse_ms_takes_precedence_over_seconds():
    assert parse_retry_after({"retry-after-ms": "500", "retry-after": "30"}) == 0.5


def test_parse_none_headers():
    assert parse_retry_after(None) is None


def test_parse_object_without_get():
    assert parse_retry_after(object()) is None


def test_parse_missing_header():
    assert parse_retry_after({}) is None


def test_parse_unparseable():
    assert parse_retry_after({"retry-after": "soon"}) is None


def test_parse_non_positive_rejected():
    assert parse_retry_after({"retry-after": "0"}) is None
    assert parse_retry_after({"retry-after": "-5"}) is None


def test_parse_over_cap_rejected():
    """A retry-after larger than the honored cap → None (jitter our own)."""
    assert parse_retry_after({"retry-after": str(MAX_HONORED_RETRY_AFTER + 1)}) is None


def test_parse_at_cap_accepted():
    assert parse_retry_after({"retry-after": str(MAX_HONORED_RETRY_AFTER)}) == MAX_HONORED_RETRY_AFTER


def test_full_jitter_within_bounds():
    for attempt in range(1, 8):
        for _ in range(50):
            wait = full_jitter_backoff(attempt, BACKOFF_CAP_429)
            assert 0.0 <= wait <= min(2.0**attempt, BACKOFF_CAP_429)


def test_full_jitter_respects_cap():
    for _ in range(100):
        assert full_jitter_backoff(10, cap=5.0) <= 5.0


def test_full_jitter_clamps_low_attempt():
    # attempt < 1 is clamped to 1 → ceiling 2.0, never raises.
    for _ in range(50):
        assert 0.0 <= full_jitter_backoff(0, cap=60.0) <= 2.0
