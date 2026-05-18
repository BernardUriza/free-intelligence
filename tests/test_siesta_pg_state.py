"""Tests for the Siesta Postgres coordination (v3.9.46+).

Replaces the blob-metadata coordination tested in
`test_siesta_blob_metadata.py` (kept for the pure parser there).

These tests run against a live Postgres instance from the standard
`pytest-postgresql` fixture (matching how the memory repos are tested).
Tests are skipped when no PG is reachable so the suite stays green on
laptops without a local PG.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from insult.core.siesta.coordination import pg_state
from insult.core.siesta.state import AWAKE, SiestaPhase, SiestaSnapshot

# Tests are gated on POSTGRES_URL being set (CI provides it via the
# postgres service container). On dev laptops without PG these skip.
pytestmark = pytest.mark.skipif(
    not os.environ.get("POSTGRES_URL"),
    reason="POSTGRES_URL not configured — siesta_state tests need a live PG",
)


@pytest.fixture(autouse=True)
async def _clean_table():
    """Wipe siesta_state row between tests so each starts from AWAKE."""
    conn = await pg_state._connect()
    if conn is None:
        pytest.skip("PG unreachable from this test runner")
    try:
        await conn.execute("DELETE FROM siesta_state WHERE singleton = 'current'")
    finally:
        await conn.close()
    yield
    # Cleanup after
    conn = await pg_state._connect()
    if conn is None:
        return
    try:
        await conn.execute("DELETE FROM siesta_state WHERE singleton = 'current'")
    finally:
        await conn.close()


async def test_read_snapshot_when_empty_returns_awake():
    """No row in table = AWAKE. Default behavior preserves bot liveness."""
    snap = await pg_state.read_snapshot()
    assert snap == AWAKE
    assert snap.phase == SiestaPhase.AWAKE
    assert not snap.is_active


async def test_mark_started_creates_row():
    ok = await pg_state.mark_started(total_users=42, phase=SiestaPhase.LIGHT)
    assert ok is True
    snap = await pg_state.read_snapshot()
    assert snap.phase == SiestaPhase.LIGHT
    assert snap.total_users == 42
    assert snap.processed_users == 0
    assert snap.started_at is not None


async def test_mark_progress_updates_existing_row():
    """UPSERT semantics: second call updates instead of inserting."""
    await pg_state.mark_started(total_users=10, phase=SiestaPhase.LIGHT)
    started = (await pg_state.read_snapshot()).started_at
    assert started is not None

    ok = await pg_state.mark_progress(
        phase=SiestaPhase.DEEP,
        started_at=started,
        total_users=10,
        processed_users=3,
        current_user_id="alex123",
    )
    assert ok is True
    snap = await pg_state.read_snapshot()
    assert snap.phase == SiestaPhase.DEEP
    assert snap.processed_users == 3
    assert snap.current_user_id == "alex123"
    assert snap.total_users == 10  # unchanged
    assert snap.progress_pct == 30


async def test_mark_finished_returns_awake_on_next_read():
    """The bot must always wake — finished marker zeroes phase."""
    await pg_state.mark_started(total_users=5, phase=SiestaPhase.LIGHT)
    await pg_state.mark_finished()
    snap = await pg_state.read_snapshot()
    assert snap.phase == SiestaPhase.AWAKE
    assert snap == AWAKE


async def test_singleton_constraint_holds():
    """CHECK constraint prevents accidentally inserting a second row.

    Without the singleton constraint, two consolidators could insert
    competing rows. The constraint converts that bug into a clear PG
    error instead of silent data divergence.
    """
    import asyncpg

    conn = await pg_state._connect()
    assert conn is not None
    try:
        # Direct insert with invalid singleton must fail with the
        # specific PG CheckViolationError, not a generic Exception.
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute(
                "INSERT INTO siesta_state (singleton, phase) VALUES ($1, $2)",
                "not_current",
                "awake",
            )
    finally:
        await conn.close()


async def test_round_trip_preserves_timezone_aware_datetime():
    """Postgres TIMESTAMPTZ round-trip must keep UTC info — critical for
    the elapsed-seconds calculation the dashboard renders."""
    now = datetime.now(UTC)
    snap_in = SiestaSnapshot(
        phase=SiestaPhase.REM,
        started_at=now,
        total_users=100,
        processed_users=75,
        current_user_id="bernard",
    )
    await pg_state._upsert(snap_in)
    snap_out = await pg_state.read_snapshot()
    assert snap_out.started_at is not None
    assert snap_out.started_at.tzinfo is not None
    # Within 1 second of original — PG roundtrip may truncate microseconds
    delta = abs((snap_out.started_at - now).total_seconds())
    assert delta < 1.0
