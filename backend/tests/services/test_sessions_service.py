"""Tests for SessionService.

Validates session creation, retrieval, update, and listing functionality.

Status: DEPRECATED - SessionService refactored to task-aggregation model
Created: Original
Updated: 2025-11-20
Card: Clean Architecture Refactor

NOTE: SessionService was refactored from CRUD-style (create/get/update/list)
to task-aggregation style (aggregate status from all TaskType tasks).

Old API (removed):
  - create_session(session_id, user_id)
  - get_session(session_id)
  - update_session_status(session_id, status, details)
  - list_sessions(user_id)

New API (current):
  - get_session_info(session_id) → aggregates all tasks

These tests need to be rewritten to test the new task-aggregation API,
or replaced with integration tests that verify task aggregation behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from backend.services.session_service import SessionService

# Skip all tests until rewritten for new API
pytestmark = pytest.mark.skip(reason="SessionService refactored to task-aggregation model - old CRUD API removed")


class TestSessionService:
    """Test suite for SessionService."""

    def test_create_session(self, session_service: SessionService, session_factory):
        """Test creating a new session."""
        session_data = session_factory(session_id="test_001", user_id="user_123")

        session = session_service.create_session(
            session_id=session_data["session_id"],
            user_id=session_data["user_id"],
        )

        assert session is not None
        assert session["session_id"] == "test_001"
        assert session["user_id"] == "user_123"
        assert session["status"] == "active"

    def test_get_session(self, session_service: SessionService, session_factory):
        """Test retrieving an existing session."""
        session_data = session_factory(session_id="test_002")

        # Create session first
        session_service.create_session(
            session_id=session_data["session_id"],
            user_id=session_data["user_id"],
        )

        # Retrieve it
        retrieved = session_service.get_session("test_002")

        assert retrieved is not None
        assert retrieved["session_id"] == "test_002"

    def test_get_nonexistent_session(self, session_service: SessionService):
        """Test retrieving a session that doesn't exist."""
        result = session_service.get_session("nonexistent_session")

        assert result is None

    def test_update_session(self, session_service: SessionService, session_factory):
        """Test updating an existing session."""
        session_data = session_factory(session_id="test_003")

        # Create session
        session_service.create_session(
            session_id=session_data["session_id"],
            user_id=session_data["user_id"],
        )

        # Update status using correct method name
        success = session_service.update_session_status(
            session_id="test_003",
            status="completed",
        )

        assert success is True

        # Verify update
        updated = session_service.get_session("test_003")
        assert updated is not None
        assert updated.get("metadata", {}).get("status") == "completed"

    def test_update_nonexistent_session(self, session_service: SessionService):
        """Test updating a session that doesn't exist."""
        success = session_service.update_session_status(
            session_id="nonexistent",
            status="completed",
        )

        assert success is False

    def test_list_sessions(self, session_service: SessionService, session_factory):
        """Test listing all sessions."""
        # Create multiple sessions
        for i in range(3):
            session_data = session_factory(session_id=f"test_{i:03d}", user_id="user_123")
            session_service.create_session(
                session_id=session_data["session_id"],
                user_id=session_data["user_id"],
            )

        # List sessions filtered by user_id
        sessions = session_service.list_sessions(user_id="user_123")

        assert len(sessions) >= 3  # At least 3 sessions created
        # User ID is stored in metadata by repository
        for s in sessions:
            assert s.get("session_id") is not None

    def test_list_sessions_filtered_by_user(self, session_service: SessionService, session_factory):
        """Test listing sessions filtered by user_id."""
        # Create sessions for different users (session_id must be >= 3 chars)
        session_service.create_session(session_id="session_a1", user_id="user_a")
        session_service.create_session(session_id="session_b1", user_id="user_b")
        session_service.create_session(session_id="session_a2", user_id="user_a")

        # List sessions for user_a
        sessions = session_service.list_sessions(user_id="user_a")

        # Should have at least 2 sessions for user_a
        assert len(sessions) >= 2
        # Verify all have session IDs
        session_ids = [s.get("session_id") for s in sessions]
        assert "session_a1" in session_ids
        assert "session_a2" in session_ids

    def test_update_interaction_count(self, session_service: SessionService, session_factory):
        """Test updating interaction count via status update."""
        session_data = session_factory(session_id="test_004")

        # Create session
        session_service.create_session(
            session_id=session_data["session_id"],
            user_id=session_data["user_id"],
        )

        # Update with interaction count in details
        success = session_service.update_session_status(
            session_id="test_004",
            status="active",
            details={"interaction_count": 5},
        )

        assert success is True

        # Verify update
        updated = session_service.get_session("test_004")
        assert updated is not None
        assert updated.get("metadata", {}).get("interaction_count") == 5
