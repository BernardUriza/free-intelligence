#!/usr/bin/env python3
"""
Free Intelligence - Sessions Store Tests

Tests for JSONL sessions storage backend.

File: tests/test_sessions_store.py
Card: FI-API-FEAT-009
Created: 2025-10-29
"""

import shutil
import tempfile

import pytest

from backend.sessions_store import SessionsStore


@pytest.fixture
def temp_store():
    """Create temporary sessions store"""
    temp_dir = tempfile.mkdtemp()
    store = SessionsStore(data_dir=temp_dir)
    yield store
    shutil.rmtree(temp_dir)


def test_create_session(temp_store) -> None:
    """Test creating a new session"""
    session = temp_store.create(
        owner_hash="sha256:test123",
        status="new",
        thread_id="thread_abc",
    )

    assert session.id is not None
    assert len(session.id) > 0
    assert session.owner_hash == "sha256:test123"
    assert session.status == "new"
    assert session.thread_id == "thread_abc"
    assert session.interaction_count == 0
    assert session.is_persisted is True


def test_get_session(temp_store) -> None:
    """Test retrieving session by ID"""
    # Create session
    created = temp_store.create(owner_hash="sha256:test456")

    # Get session
    retrieved = temp_store.get(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.owner_hash == created.owner_hash
    assert retrieved.status == created.status


def test_get_nonexistent_session(temp_store) -> None:
    """Test getting session that doesn't exist"""
    session = temp_store.get("NONEXISTENT_ID")
    assert session is None


def test_list_sessions_empty(temp_store) -> None:
    """Test listing sessions when store is empty"""
    sessions = temp_store.list()
    assert sessions == []


def test_list_sessions_with_data(temp_store) -> None:
    """Test listing sessions with pagination"""
    # Create 5 sessions
    for i in range(5):
        temp_store.create(owner_hash=f"sha256:owner{i}")

    # List all
    sessions = temp_store.list(limit=10, offset=0)
    assert len(sessions) == 5

    # List with pagination
    sessions_page1 = temp_store.list(limit=2, offset=0)
    assert len(sessions_page1) == 2

    sessions_page2 = temp_store.list(limit=2, offset=2)
    assert len(sessions_page2) == 2


def test_list_sessions_by_owner(temp_store) -> None:
    """Test filtering sessions by owner_hash"""
    # Create sessions for different owners
    temp_store.create(owner_hash="sha256:alice")
    temp_store.create(owner_hash="sha256:alice")
    temp_store.create(owner_hash="sha256:bob")

    # Filter by alice
    alice_sessions = temp_store.list(owner_hash="sha256:alice")
    assert len(alice_sessions) == 2

    # Filter by bob
    bob_sessions = temp_store.list(owner_hash="sha256:bob")
    assert len(bob_sessions) == 1


def test_update_session(temp_store) -> None:
    """Test updating session"""
    # Create session
    session = temp_store.create(owner_hash="sha256:test")

    # Update status
    updated = temp_store.update(
        session_id=session.id,
        status="active",
        interaction_count=5,
    )

    assert updated is not None
    assert updated.id == session.id
    assert updated.status == "active"
    assert updated.interaction_count == 5
    assert updated.created_at == session.created_at  # unchanged
    assert updated.updated_at != session.updated_at  # changed


def test_update_nonexistent_session(temp_store) -> None:
    """Test updating session that doesn't exist"""
    updated = temp_store.update(
        session_id="NONEXISTENT",
        status="active",
    )
    assert updated is None


def test_count_sessions(temp_store) -> None:
    """Test counting total sessions"""
    # Initially empty
    assert temp_store.count() == 0

    # Create 3 sessions
    temp_store.create(owner_hash="sha256:owner1")
    temp_store.create(owner_hash="sha256:owner2")
    temp_store.create(owner_hash="sha256:owner3")

    assert temp_store.count() == 3


def test_count_sessions_by_owner(temp_store) -> None:
    """Test counting sessions filtered by owner"""
    temp_store.create(owner_hash="sha256:alice")
    temp_store.create(owner_hash="sha256:alice")
    temp_store.create(owner_hash="sha256:bob")

    assert temp_store.count(owner_hash="sha256:alice") == 2
    assert temp_store.count(owner_hash="sha256:bob") == 1


def test_atomicity_create(temp_store) -> None:
    """Test that create is atomic (index updated after manifest)"""
    session = temp_store.create(owner_hash="sha256:test")

    # Verify index points to correct offset
    index = temp_store._read_index()
    assert session.id in index

    # Verify manifest has entry
    retrieved = temp_store.get(session.id)
    assert retrieved is not None
    assert retrieved.id == session.id


def test_persistence_across_instances(temp_store) -> None:
    """Test that data persists across store instances"""
    # Create session
    session = temp_store.create(owner_hash="sha256:persist_test")

    # Create new store instance with same data_dir
    new_store = SessionsStore(data_dir=str(temp_store.data_dir))

    # Verify session exists
    retrieved = new_store.get(session.id)
    assert retrieved is not None
    assert retrieved.id == session.id
    assert retrieved.owner_hash == "sha256:persist_test"


def test_sessions_sorted_by_created_at(temp_store) -> None:
    """Test that sessions are sorted newest first"""
    import time

    # Create sessions with small delays
    session1 = temp_store.create(owner_hash="sha256:first")
    time.sleep(0.01)
    session2 = temp_store.create(owner_hash="sha256:second")
    time.sleep(0.01)
    session3 = temp_store.create(owner_hash="sha256:third")

    # List all
    sessions = temp_store.list()

    # Newest first
    assert sessions[0].id == session3.id
    assert sessions[1].id == session2.id
    assert sessions[2].id == session1.id
