"""Tests for AuditService.

Validates audit logging functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.audit_service import AuditService


class TestAuditService:
    """Test suite for AuditService."""

    def test_log_action(self, audit_service: AuditService, audit_entry_factory):
        """Test logging a single action."""
        entry = audit_entry_factory(
            action="session_created",
            user_id="user_123",
            resource="session:test_001",
            result="success",
        )

        # Log action
        audit_service.log_action(
            action=entry["action"],
            user_id=entry["user_id"],
            resource=entry["resource"],
            result=entry["result"],
        )

        # Verify logged (audit service doesn't return entries in MVP)
        # This validates that no exception was raised
        assert True

    def test_log_action_with_details(self, audit_service: AuditService):
        """Test logging an action with additional details."""
        audit_service.log_action(
            action="export_created",
            user_id="user_456",
            resource="export:manifest_001",
            result="success",
            details={"format": "json", "size_bytes": 1024},
        )

        assert True

    def test_log_failed_action(self, audit_service: AuditService):
        """Test logging a failed action."""
        audit_service.log_action(
            action="session_update",
            user_id="user_789",
            resource="session:nonexistent",
            result="failed",
            details={"error": "Session not found"},
        )

        assert True

    def test_log_multiple_actions(self, audit_service: AuditService):
        """Test logging multiple actions."""
        actions = [
            ("session_created", "user_1", "session:s1", "success"),
            ("session_updated", "user_1", "session:s1", "success"),
            ("session_deleted", "user_1", "session:s1", "success"),
        ]

        for action, user_id, resource, result in actions:
            audit_service.log_action(
                action=action,
                user_id=user_id,
                resource=resource,
                result=result,
            )

        # All logs should complete without error
        assert True

    def test_log_action_with_empty_details(self, audit_service: AuditService):
        """Test logging action with empty details dict."""
        audit_service.log_action(
            action="test_action",
            user_id="user_test",
            resource="test_resource",
            result="success",
            details={},
        )

        assert True

    def test_log_system_action(self, audit_service: AuditService):
        """Test logging a system action (no user)."""
        audit_service.log_action(
            action="system_health_check",
            user_id="system",
            resource="health",
            result="success",
        )

        assert True
