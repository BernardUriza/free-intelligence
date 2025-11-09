"""Tests for Parquet audit sink.

TDD tests for audit event persistence.

File: backend/tests/test_audit_sink.py
Card: AUR-PROMPT-3.1
Created: 2025-11-09
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.app.audit.sink import read_audit_events, write_audit_event


@pytest.fixture
def audit_root(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Temporary audit root for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "audit"
        audit_path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("AUDIT_ROOT", str(audit_path))
        # Reload module to pick up new env
        import importlib

        from backend.app.audit import sink

        importlib.reload(sink)
        yield audit_path


def test_write_audit_event_creates_partition(audit_root: Path) -> None:
    """Test that write_audit_event creates date partition."""
    event_id = write_audit_event(
        action="TIMELINE_HASH_VERIFIED",
        user_id="session_20251109_120000",
        resource="/api/timeline/verify-hash",
        result="SUCCESS",
        metadata={"hash": "abc123"},
    )

    # Check event_id is UUID
    assert len(event_id) == 36
    assert event_id.count("-") == 4

    # Check partition directory exists
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    partition_dir = audit_root / f"date={today}"
    assert partition_dir.exists()

    # Check parquet file exists
    parquet_files = list(partition_dir.glob("*.parquet"))
    assert len(parquet_files) >= 1


def test_write_and_read_audit_event(audit_root: Path) -> None:
    """Test round-trip write and read."""
    metadata = {"hash": "abc123", "session_count": 5}

    event_id = write_audit_event(
        action="TIMELINE_HASH_VERIFIED",
        user_id="session_20251109_120000",
        resource="/api/timeline/verify-hash",
        result="SUCCESS",
        metadata=metadata,
    )

    # Read back
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events = read_audit_events(start_date=today, end_date=today)

    assert len(events) >= 1
    event = next(e for e in events if e["event_id"] == event_id)

    assert event["action"] == "TIMELINE_HASH_VERIFIED"
    assert event["user_id"] == "session_20251109_120000"
    assert event["resource"] == "/api/timeline/verify-hash"
    assert event["result"] == "SUCCESS"
    assert event["metadata"] == metadata


def test_read_audit_events_filters_by_action(audit_root: Path) -> None:
    """Test filtering by action."""
    write_audit_event(
        action="TIMELINE_HASH_VERIFIED",
        user_id="user1",
        resource="/api/timeline",
        result="SUCCESS",
    )

    write_audit_event(
        action="SESSION_CREATED", user_id="user2", resource="/api/session", result="SUCCESS"
    )

    # Filter by action
    events = read_audit_events(action="TIMELINE_HASH_VERIFIED")

    assert len(events) >= 1
    assert all(e["action"] == "TIMELINE_HASH_VERIFIED" for e in events)


def test_read_audit_events_empty_if_no_events(audit_root: Path) -> None:
    """Test reading from empty audit root."""
    events = read_audit_events(start_date="2025-01-01", end_date="2025-01-01")
    assert events == []


def test_write_audit_event_handles_empty_metadata(audit_root: Path) -> None:
    """Test writing event without metadata."""
    event_id = write_audit_event(
        action="SESSION_CREATED",
        user_id="user1",
        resource="/api/session",
        result="SUCCESS",
        metadata=None,
    )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events = read_audit_events(start_date=today)

    event = next(e for e in events if e["event_id"] == event_id)
    assert event["metadata"] == {}
