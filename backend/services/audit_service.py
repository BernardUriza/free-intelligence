"""Service layer for audit logging.

Handles creation and querying of audit logs for compliance,
forensics, and security monitoring.

Clean Code: All audit logic centralized here, making it easy to enforce
audit policies across the entire application.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from backend.logger import get_logger
from backend.repositories import AuditRepository
from backend.type_defs import AuditLogDict

logger = get_logger(__name__)


class AuditService:
    """Service for audit log management.

    Responsibilities:
    - Create immutable audit records
    - Query audit trail for compliance
    - Provide audit analytics
    """

    def __init__(self, repository: AuditRepository) -> None:
        """Initialize service with repository dependency.

        Args:
            repository: AuditRepository instance for data access
        """
        self.repository = repository

    def log_action(
        self,
        action: str,
        user_id: str,
        resource: str,
        result: str,
        details: dict[str, Optional[Any]] = None,
    ) -> str:
        """Log an action to the audit trail.

        Args:
            action: Action performed (create, read, update, delete, export, etc.)
            user_id: User who performed the action
            resource: Resource affected (e.g., "document:doc_123")
            result: Result status (success, failed, denied)
            details: Additional context (affected fields, old values, etc.)

        Returns:
            Audit log ID

        Raises:
            ValueError: If required fields are invalid
            IOError: If storage fails
        """
        # Validate inputs
        if not action or len(action.strip()) == 0:
            raise ValueError("action cannot be empty")

        if not user_id or len(user_id.strip()) == 0:
            raise ValueError("user_id cannot be empty")

        if not resource or len(resource.strip()) == 0:
            raise ValueError("resource cannot be empty")

        if result not in {"success", "failed", "denied"}:
            raise ValueError("result must be 'success', 'failed', or 'denied'")

        try:
            audit_log: AuditLogDict = {
                "timestamp": datetime.now(UTC),
                "action": action,
                "user_id": user_id,
                "resource": resource,
                "result": result,
            }

            if details:
                audit_log["details"] = details

            log_id = self.repository.create(audit_log)

            logger.info(
                "AUDIT_LOGGED",
                log_id=log_id,
                action=action,
                user_id=user_id,
                resource=resource,
                result=result,
            )

            return log_id

        except ValueError as e:
            logger.warning("AUDIT_VALIDATION_FAILED", error=str(e))
            raise
        except OSError as e:
            logger.error("AUDIT_LOGGING_FAILED", error=str(e))
            raise

    def get_log(self, log_id: str) -> dict[str, Any] | None:
        """Retrieve audit log entry.

        Args:
            log_id: Audit log ID

        Returns:
            Audit log data or None if not found
        """
        try:
            return self.repository.read(log_id)
        except OSError as e:
            logger.error("AUDIT_READ_FAILED", log_id=log_id, error=str(e))
            raise

    def get_logs(
        self,
        limit: Optional[int] = None,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Query audit logs with filtering.

        Args:
            limit: Maximum logs to return
            action: Filter by action type
            user_id: Filter by user
            resource: Filter by resource

        Returns:
            List of audit logs
        """
        try:
            return self.repository.list_all(
                limit=limit,
                action=action,
                user_id=user_id,
                resource=resource,
            )
        except OSError as e:
            logger.error("AUDIT_LIST_FAILED", error=str(e))
            raise

    def get_logs_by_date(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Get audit logs within date range.

        Args:
            start_date: Start of range (inclusive)
            end_date: End of range (inclusive)
            limit: Maximum logs to return

        Returns:
            List of audit logs in date range
        """
        try:
            return self.repository.get_logs_by_date_range(start_date, end_date, limit)
        except OSError as e:
            logger.error("AUDIT_DATE_RANGE_FAILED", error=str(e))
            raise

    def get_user_activity(
        self,
        user_id: str,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Get all audit logs for a specific user.

        Useful for user activity monitoring and compliance reporting.

        Args:
            user_id: User identifier
            limit: Maximum logs to return

        Returns:
            List of audit logs for user
        """
        try:
            return self.repository.list_all(
                limit=limit,
                user_id=user_id,
            )
        except OSError as e:
            logger.error("USER_ACTIVITY_FAILED", user_id=user_id, error=str(e))
            raise

    def get_resource_activity(
        self,
        resource: str,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Get all audit logs for a specific resource.

        Useful for understanding all changes to a resource.

        Args:
            resource: Resource identifier
            limit: Maximum logs to return

        Returns:
            List of audit logs for resource
        """
        try:
            return self.repository.list_all(
                limit=limit,
                resource=resource,
            )
        except OSError as e:
            logger.error(
                "RESOURCE_ACTIVITY_FAILED",
                resource=resource,
                error=str(e),
            )
            raise

    def log_document_created(
        self,
        user_id: str,
        document_id: str,
        size_bytes: int,
        details: dict[str, Optional[Any]] = None,
    ) -> str:
        """Log document creation event.

        Args:
            user_id: User who created document
            document_id: Document identifier
            size_bytes: Document size
            details: Additional metadata

        Returns:
            Audit log ID
        """
        log_details = {
            "document_id": document_id,
            "size_bytes": size_bytes,
        }
        if details:
            log_details.update(details)

        return self.log_action(
            action="document_created",
            user_id=user_id,
            resource=f"document:{document_id}",
            result="success",
            details=log_details,
        )

    def log_document_deleted(
        self,
        user_id: str,
        document_id: str,
        reason: Optional[str] = None,
    ) -> str:
        """Log document deletion event.

        Args:
            user_id: User who deleted document
            document_id: Document identifier
            reason: Reason for deletion

        Returns:
            Audit log ID
        """
        log_details = {"document_id": document_id}
        if reason:
            log_details["reason"] = reason

        return self.log_action(
            action="document_deleted",
            user_id=user_id,
            resource=f"document:{document_id}",
            result="success",
            details=log_details,
        )

    def log_export(
        self,
        user_id: str,
        resource_id: str,
        export_format: str,
        record_count: int,
    ) -> str:
        """Log data export event (for compliance).

        Args:
            user_id: User performing export
            resource_id: Resource being exported
            export_format: Export format (JSON, CSV, etc.)
            record_count: Number of records exported

        Returns:
            Audit log ID
        """
        return self.log_action(
            action="export",
            user_id=user_id,
            resource=f"export:{resource_id}",
            result="success",
            details={
                "resource_id": resource_id,
                "format": export_format,
                "record_count": record_count,
            },
        )
