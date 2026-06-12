"""Pure-function tests for blob metadata round-trip + tolerant parsing.

The Azure I/O is mocked away — we only test ``_build_metadata`` /
``parse_metadata`` because everything else in :mod:`blob_metadata` is a
thin SDK wrapper.
"""

from __future__ import annotations

from datetime import UTC, datetime

from personas.insult.core.siesta.coordination.blob_metadata import (
    _build_metadata,
    parse_metadata,
)
from personas.insult.core.siesta.state import AWAKE, SiestaPhase, SiestaSnapshot


def test_roundtrip_active_snapshot_preserves_all_fields():
    started = datetime(2026, 4, 27, 18, 0, 0, tzinfo=UTC)
    original = SiestaSnapshot(
        phase=SiestaPhase.DEEP,
        started_at=started,
        total_users=4,
        processed_users=2,
        current_user_id="1431300030823927999",
    )
    metadata = _build_metadata(original)
    parsed = parse_metadata(metadata)
    assert parsed.phase is SiestaPhase.DEEP
    assert parsed.started_at == started
    assert parsed.total_users == 4
    assert parsed.processed_users == 2
    assert parsed.current_user_id == "1431300030823927999"


def test_roundtrip_awake_returns_singleton_equivalent():
    metadata = _build_metadata(AWAKE)
    parsed = parse_metadata(metadata)
    assert parsed.phase is SiestaPhase.AWAKE
    assert not parsed.is_active


def test_parse_returns_awake_for_empty_metadata():
    assert parse_metadata({}).phase is SiestaPhase.AWAKE
    assert parse_metadata(None).phase is SiestaPhase.AWAKE


def test_parse_tolerant_to_invalid_phase():
    # An operator could attach a typo via az CLI; we must not crash.
    assert parse_metadata({"siesta_phase": "snoozing"}).phase is SiestaPhase.AWAKE


def test_parse_tolerant_to_invalid_started_at():
    parsed = parse_metadata({"siesta_phase": "light", "siesta_started_at": "not-a-date"})
    assert parsed.phase is SiestaPhase.LIGHT
    # started_at parsing failed, but we still get the active phase.
    assert parsed.started_at is None


def test_parse_tolerant_to_non_int_counts():
    parsed = parse_metadata({"siesta_phase": "light", "siesta_total_users": "many", "siesta_processed_users": "1"})
    assert parsed.total_users == 0
    assert parsed.processed_users == 1


def test_parse_treats_empty_current_user_as_none():
    parsed = parse_metadata({"siesta_phase": "light", "siesta_current_user_id": ""})
    assert parsed.current_user_id is None
