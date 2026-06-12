"""Pure-data tests for the siesta state types."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from personas.insult.core.siesta.state import AWAKE, SiestaPhase, SiestaSnapshot


def test_awake_singleton_is_inactive():
    assert AWAKE.phase is SiestaPhase.AWAKE
    assert AWAKE.is_active is False
    assert AWAKE.progress_pct == 0


def test_active_phase_reports_active():
    snap = SiestaSnapshot(phase=SiestaPhase.LIGHT, total_users=4, processed_users=1)
    assert snap.is_active
    assert snap.progress_pct == 25


def test_progress_pct_clamps_at_100():
    # Defensive: a buggy writer reporting processed > total shouldn't break the UI.
    snap = SiestaSnapshot(phase=SiestaPhase.DEEP, total_users=5, processed_users=99)
    assert snap.progress_pct == 100


def test_progress_pct_zero_when_total_unknown():
    snap = SiestaSnapshot(phase=SiestaPhase.LIGHT, total_users=0, processed_users=0)
    assert snap.progress_pct == 0


def test_elapsed_seconds_zero_without_started_at():
    assert SiestaSnapshot(phase=SiestaPhase.LIGHT).elapsed_seconds == 0


def test_elapsed_seconds_grows_with_age():
    started = datetime.now(UTC) - timedelta(seconds=42)
    snap = SiestaSnapshot(phase=SiestaPhase.LIGHT, started_at=started)
    # Allow 1s tolerance for clock skew during the test.
    assert 41 <= snap.elapsed_seconds <= 43


def test_phase_enum_values_match_metadata_strings():
    # blob_metadata serializes the enum value; if the value drifts, the
    # bot and consolidator will silently disagree.
    assert SiestaPhase.AWAKE.value == "awake"
    assert SiestaPhase.LIGHT.value == "light"
    assert SiestaPhase.DEEP.value == "deep"
    assert SiestaPhase.REM.value == "rem"
