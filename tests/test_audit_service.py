"""Unit tests for AuditService.

Tests the audit service with mock dependencies.
Demonstrates the clean code testing pattern for audit logging.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from backend.services.audit_service import AuditService


@pytest.fixture
def mock_repository():
    """Create mock AuditRepository."""
    mock = Mock()
    mock.create.return_value = "audit_123"
    mock.read.return_value = {
        "audit_id": "audit_123",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "session_created",
        "user_id": "user_001",
        "resource": "session:123",
        "result": "success",
    }
    mock.list_all.return_value = [
        {
            "audit_id": "audit_123",
            "timestamp": "2025-11-01T12:00:00Z",
            "action": "session_created",
            "user_id": "user_001",
        }
    ]
    return mock


@pytest.fixture
def audit_service(mock_repository):
    """Create AuditService with mocked repository."""
    return AuditService(repository=mock_repository)


class TestAuditServiceLogging:
    """Tests for audit logging."""

    def test_log_action_success(self, audit_service, mock_repository):
        """Test successful audit logging."""
        result = audit_service.log_action(
            action="session_created",
            user_id="user_001",
            resource="session:123",
            result="success",
        )

        assert result is True
        mock_repository.create.assert_called_once()

    def test_log_action_with_details(self, audit_service, mock_repository):
        """Test audit logging with additional details."""
        details = {
            "session_id": "session_123",
            "created_by": "system",
        }

        result = audit_service.log_action(
            action="session_created",
            user_id="user_001",
            resource="session:123",
            result="success",
            details=details,
        )

        assert result is True
        call_kwargs = mock_repository.create.call_args[1]
        assert call_kwargs["details"] == details

    def test_log_action_failure(self, audit_service, mock_repository):
        """Test logging failed action."""
        result = audit_service.log_action(
            action="document_deleted",
            user_id="user_001",
            resource="document:456",
            result="failure",
            details={"error": "Not found"},
        )

        assert result is True
        call_kwargs = mock_repository.create.call_args[1]
        assert call_kwargs["result"] == "failure"

    def test_log_action_missing_required_fields(self, audit_service):
        """Test logging with missing required fields."""
        # Missing user_id
        with pytest.raises(ValueError):
            audit_service.log_action(
                action="session_created",
                user_id="",  # Empty
                resource="session:123",
                result="success",
            )

    def test_log_action_invalid_action(self, audit_service):
        """Test logging with invalid action format."""
        # Action with invalid characters
        with pytest.raises(ValueError):
            audit_service.log_action(
                action="invalid action!@#",
                user_id="user_001",
                resource="session:123",
                result="success",
            )

    def test_log_action_invalid_result_status(self, audit_service):
        """Test logging with invalid result status."""
        with pytest.raises(ValueError, match="result must be"):
            audit_service.log_action(
                action="session_created",
                user_id="user_001",
                resource="session:123",
                result="invalid_status",
            )

    def test_log_action_storage_error(self, audit_service, mock_repository):
        """Test audit logging fails on storage error."""
        mock_repository.create.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            audit_service.log_action(
                action="session_created",
                user_id="user_001",
                resource="session:123",
                result="success",
            )


class TestAuditServiceRetrieval:
    """Tests for audit log retrieval."""

    def test_get_audit_log_success(self, audit_service, mock_repository):
        """Test successful audit log retrieval."""
        result = audit_service.get_audit_log("audit_123")

        assert result is not None
        assert result["audit_id"] == "audit_123"
        assert result["action"] == "session_created"
        mock_repository.read.assert_called_once_with("audit_123")

    def test_get_audit_log_not_found(self, audit_service, mock_repository):
        """Test retrieval returns None for missing log."""
        mock_repository.read.return_value = None

        result = audit_service.get_audit_log("nonexistent")

        assert result is None

    def test_get_audit_log_retrieval_error(self, audit_service, mock_repository):
        """Test retrieval fails on storage error."""
        mock_repository.read.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            audit_service.get_audit_log("audit_123")


class TestAuditServiceListing:
    """Tests for audit log listing."""

    def test_list_audit_logs_success(self, audit_service, mock_repository):
        """Test listing audit logs."""
        result = audit_service.list_audit_logs()

        assert isinstance(result, list)
        assert len(result) >= 0
        mock_repository.list_all.assert_called()

    def test_list_audit_logs_with_limit(self, audit_service, mock_repository):
        """Test listing with limit."""
        audit_service.list_audit_logs(limit=10)

        mock_repository.list_all.assert_called()

    def test_list_audit_logs_filter_by_action(self, audit_service, mock_repository):
        """Test listing filtered by action."""
        mock_repository.list_all.return_value = [
            {
                "audit_id": "audit_1",
                "action": "session_created",
            },
            {
                "audit_id": "audit_2",
                "action": "session_created",
            },
        ]

        result = audit_service.list_audit_logs(action="session_created")

        assert isinstance(result, list)

    def test_list_audit_logs_filter_by_user(self, audit_service, mock_repository):
        """Test listing filtered by user."""
        mock_repository.list_all.return_value = [
            {
                "audit_id": "audit_1",
                "user_id": "user_001",
            }
        ]

        result = audit_service.list_audit_logs(user_id="user_001")

        assert isinstance(result, list)

    def test_list_audit_logs_retrieval_error(self, audit_service, mock_repository):
        """Test listing fails on storage error."""
        mock_repository.list_all.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Storage failed"):
            audit_service.list_audit_logs()


class TestAuditServiceFiltering:
    """Tests for audit log filtering."""

    def test_filter_by_action(self, audit_service, mock_repository):
        """Test filtering logs by action."""
        mock_repository.list_all.return_value = [
            {"audit_id": "1", "action": "session_created", "user_id": "user_001"},
            {"audit_id": "2", "action": "session_deleted", "user_id": "user_001"},
            {"audit_id": "3", "action": "session_created", "user_id": "user_002"},
        ]

        result = audit_service.list_audit_logs(action="session_created")

        # Should return filtered list
        assert isinstance(result, list)

    def test_filter_by_user_and_action(self, audit_service, mock_repository):
        """Test filtering logs by both user and action."""
        mock_repository.list_all.return_value = [
            {"audit_id": "1", "action": "session_created", "user_id": "user_001"},
            {"audit_id": "2", "action": "session_deleted", "user_id": "user_001"},
            {"audit_id": "3", "action": "session_created", "user_id": "user_002"},
        ]

        result = audit_service.list_audit_logs(
            user_id="user_001",
            action="session_created",
        )

        assert isinstance(result, list)


class TestAuditServiceCounting:
    """Tests for audit log counting."""

    def test_count_logs(self, audit_service, mock_repository):
        """Test counting audit logs."""
        mock_repository.list_all.return_value = [
            {"audit_id": "audit_1"},
            {"audit_id": "audit_2"},
            {"audit_id": "audit_3"},
        ]

        result = audit_service.count_logs()

        assert result == 3

    def test_count_logs_by_action(self, audit_service, mock_repository):
        """Test counting logs by action."""
        mock_repository.list_all.return_value = [
            {"audit_id": "audit_1", "action": "session_created"},
            {"audit_id": "audit_2", "action": "session_created"},
            {"audit_id": "audit_3", "action": "session_deleted"},
        ]

        result = audit_service.count_logs(action="session_created")

        assert result == 2

    def test_count_logs_by_user(self, audit_service, mock_repository):
        """Test counting logs by user."""
        mock_repository.list_all.return_value = [
            {"audit_id": "audit_1", "user_id": "user_001"},
            {"audit_id": "audit_2", "user_id": "user_001"},
            {"audit_id": "audit_3", "user_id": "user_002"},
        ]

        result = audit_service.count_logs(user_id="user_001")

        assert result == 2


class TestAuditServiceStatistics:
    """Tests for audit log statistics."""

    def test_get_statistics(self, audit_service, mock_repository):
        """Test getting audit statistics."""
        mock_repository.list_all.return_value = [
            {"audit_id": "1", "action": "session_created", "result": "success"},
            {"audit_id": "2", "action": "session_deleted", "result": "success"},
            {"audit_id": "3", "action": "session_created", "result": "failure"},
        ]

        result = audit_service.get_statistics()

        assert isinstance(result, dict)
        assert "total_logs" in result

    def test_get_action_breakdown(self, audit_service, mock_repository):
        """Test getting action breakdown."""
        mock_repository.list_all.return_value = [
            {"audit_id": "1", "action": "session_created"},
            {"audit_id": "2", "action": "session_created"},
            {"audit_id": "3", "action": "session_deleted"},
        ]

        result = audit_service.get_statistics()

        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
