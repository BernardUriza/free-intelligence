"""Unit tests for SessionService.

Tests the session service with mock dependencies.
Demonstrates the clean code testing pattern for session management.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from backend.services.session_service import SessionService


@pytest.fixture
def mock_repository():
    """Create mock SessionRepository."""
    mock = Mock()
    mock.create.return_value = {
        "session_id": "session_123",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "user_id": None,
    }
    mock.read.return_value = {
        "session_id": "session_123",
        "created_at": "2025-11-01T12:00:00Z",
        "updated_at": "2025-11-01T12:00:00Z",
        "status": "active",
        "user_id": "user_001",
    }
    mock.list_all.return_value = [
        {
            "session_id": "session_123",
            "status": "active",
            "user_id": "user_001",
        }
    ]
    mock.update.return_value = True
    mock.delete.return_value = True
    return mock


@pytest.fixture
def session_service(mock_repository):
    """Create SessionService with mocked repository."""
    return SessionService(repository=mock_repository)


class TestSessionServiceCreation:
    """Tests for session creation."""

    def test_create_session_success(self, session_service, mock_repository):
        """Test successful session creation."""
        result = session_service.create_session(user_id="user_001")

        assert result is not None
        assert result["session_id"] == "session_123"
        assert result["status"] == "active"
        mock_repository.create.assert_called_once()

    def test_create_session_with_metadata(self, session_service, mock_repository):
        """Test session creation with custom metadata."""
        metadata = {"source": "mobile", "version": "1.0"}
        result = session_service.create_session(user_id="user_001", metadata=metadata)

        assert result is not None
        call_kwargs = mock_repository.create.call_args[1]
        assert call_kwargs["user_id"] == "user_001"

    def test_create_session_validation_error(self, session_service, mock_repository):
        """Test session creation with validation error."""
        mock_repository.create.side_effect = ValueError("Invalid user_id")

        with pytest.raises(ValueError, match="Invalid"):
            session_service.create_session(user_id="")

    def test_create_session_storage_error(self, session_service, mock_repository):
        """Test session creation fails on storage error."""
        mock_repository.create.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            session_service.create_session(user_id="user_001")


class TestSessionServiceRetrieval:
    """Tests for session retrieval."""

    def test_get_session_success(self, session_service, mock_repository):
        """Test successful session retrieval."""
        result = session_service.get_session("session_123")

        assert result is not None
        assert result["session_id"] == "session_123"
        assert result["status"] == "active"
        mock_repository.read.assert_called_once_with("session_123")

    def test_get_session_not_found(self, session_service, mock_repository):
        """Test retrieval returns None for missing session."""
        mock_repository.read.return_value = None

        result = session_service.get_session("nonexistent")

        assert result is None

    def test_get_session_retrieval_error(self, session_service, mock_repository):
        """Test retrieval fails on storage error."""
        mock_repository.read.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            session_service.get_session("session_123")


class TestSessionServiceUpdate:
    """Tests for session updates."""

    def test_update_session_status(self, session_service, mock_repository):
        """Test updating session status."""
        result = session_service.update_session(
            session_id="session_123",
            status="complete",
        )

        assert result is True
        mock_repository.update.assert_called_once()
        call_kwargs = mock_repository.update.call_args[1]
        assert call_kwargs["status"] == "complete"

    def test_update_session_interaction_count(self, session_service, mock_repository):
        """Test updating interaction count."""
        result = session_service.update_session(
            session_id="session_123",
            interaction_count=5,
        )

        assert result is True
        call_kwargs = mock_repository.update.call_args[1]
        assert call_kwargs["interaction_count"] == 5

    def test_update_session_invalid_status(self, session_service):
        """Test update fails with invalid status."""
        with pytest.raises(ValueError, match="Invalid status"):
            session_service.update_session(
                session_id="session_123",
                status="invalid_status",
            )

    def test_update_session_negative_interaction_count(self, session_service):
        """Test update fails with negative interaction count."""
        with pytest.raises(ValueError, match="interaction_count must be"):
            session_service.update_session(
                session_id="session_123",
                interaction_count=-1,
            )

    def test_update_session_not_found(self, session_service, mock_repository):
        """Test updating non-existent session."""
        mock_repository.update.return_value = False

        result = session_service.update_session(
            session_id="nonexistent",
            status="complete",
        )

        assert result is False

    def test_update_session_storage_error(self, session_service, mock_repository):
        """Test update fails on storage error."""
        mock_repository.update.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            session_service.update_session(
                session_id="session_123",
                status="complete",
            )


class TestSessionServiceListing:
    """Tests for session listing."""

    def test_list_sessions_success(self, session_service, mock_repository):
        """Test listing sessions."""
        result = session_service.list_sessions()

        assert isinstance(result, list)
        assert len(result) >= 0
        mock_repository.list_all.assert_called_once()

    def test_list_sessions_with_limit(self, session_service, mock_repository):
        """Test listing with limit."""
        session_service.list_sessions(limit=5)

        mock_repository.list_all.assert_called()

    def test_list_sessions_with_user_filter(self, session_service, mock_repository):
        """Test listing filtered by user."""
        mock_repository.list_all.return_value = [
            {
                "session_id": "session_123",
                "status": "active",
                "user_id": "user_001",
            }
        ]

        result = session_service.list_sessions(user_id="user_001")

        assert isinstance(result, list)

    def test_list_sessions_retrieval_error(self, session_service, mock_repository):
        """Test listing fails on storage error."""
        mock_repository.list_all.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            session_service.list_sessions()


class TestSessionServiceDeletion:
    """Tests for session deletion."""

    def test_delete_session_success(self, session_service, mock_repository):
        """Test successful session deletion."""
        result = session_service.delete_session("session_123")

        assert result is True
        mock_repository.delete.assert_called_once_with("session_123")

    def test_delete_session_not_found(self, session_service, mock_repository):
        """Test deletion of non-existent session."""
        mock_repository.delete.return_value = False

        result = session_service.delete_session("nonexistent")

        assert result is False

    def test_delete_session_storage_error(self, session_service, mock_repository):
        """Test deletion fails on storage error."""
        mock_repository.delete.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            session_service.delete_session("session_123")


class TestSessionServiceValidation:
    """Tests for session validation."""

    def test_is_session_active_true(self, session_service, mock_repository):
        """Test checking if session is active."""
        mock_repository.read.return_value = {
            "session_id": "session_123",
            "status": "active",
        }

        result = session_service.is_session_active("session_123")

        assert result is True

    def test_is_session_active_false(self, session_service, mock_repository):
        """Test session not active."""
        mock_repository.read.return_value = {
            "session_id": "session_123",
            "status": "complete",
        }

        result = session_service.is_session_active("session_123")

        assert result is False

    def test_is_session_active_not_found(self, session_service, mock_repository):
        """Test checking non-existent session."""
        mock_repository.read.return_value = None

        result = session_service.is_session_active("nonexistent")

        assert result is False


class TestSessionServiceCounts:
    """Tests for session counting."""

    def test_count_sessions(self, session_service, mock_repository):
        """Test counting sessions."""
        mock_repository.list_all.return_value = [
            {"session_id": "session_1"},
            {"session_id": "session_2"},
            {"session_id": "session_3"},
        ]

        result = session_service.count_sessions()

        assert result == 3

    def test_count_user_sessions(self, session_service, mock_repository):
        """Test counting sessions for user."""
        mock_repository.list_all.return_value = [
            {"session_id": "session_1", "user_id": "user_001"},
            {"session_id": "session_2", "user_id": "user_001"},
        ]

        result = session_service.count_sessions(user_id="user_001")

        assert result == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
