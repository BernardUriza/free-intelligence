"""DI Audit Service - Refactored with dependency injection.

Handles audit logging with injected dependencies for better testability
and decoupling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.repositories.audit_repository import AuditRepository
from backend.utils.common.types.type_defs import AuditLogDict
from backend.infrastructure.interfaces.ilogger import ILogger


class DIAuditService:
    """Audit service with dependency injection.

    Responsibilities:
    - Create immutable audit records
    - Query audit trail for compliance
    - Provide audit analytics
    """

    def __init__(self, logger: ILogger, repository: AuditRepository) -> None:
        """Initialize service with injected dependencies.

        Args:
            logger: Logger instance
            repository: AuditRepository instance
        """
        self.logger = logger
        self.repository = repository

    def log_action(
        self,
        action: str,
        user_id: str,
        resource: str,
        result: str,
        clinic_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Log an action to the audit trail with multi-tenancy support.

        Args:
            action: Action performed (create, read, update, delete, export, etc.)
            user_id: User performing the action
            resource: Resource affected (session_id, file_path, etc.)
            result: Result of action (success, failure, etc.)
            clinic_id: Clinic ID (multi-tenancy isolation)
            details: Additional context/details

        Returns:
            Audit log ID
        """
        # Create audit record with clinic_id
        audit_record: AuditLogDict = {
            "timestamp": datetime.now(timezone.utc),
            "action": action,
            "user_id": user_id,
            "clinic_id": clinic_id,
            "resource": resource,
            "result": result,
            "details": details or {},
        }

        # Store in repository
        audit_id = self.repository.create(audit_record)

        # Log the audit action itself (include clinic_id for forensics)
        self.logger.info(
            "AUDIT_LOG_CREATED",
            audit_id=audit_id,
            action=action,
            user_id=user_id,
            clinic_id=clinic_id,
            resource=resource,
            result=result,
        )

        return audit_id
