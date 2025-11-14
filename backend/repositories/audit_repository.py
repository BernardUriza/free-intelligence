"""Repository for audit log operations.

Handles append-only audit log storage for compliance and forensics.
Ensures immutability and efficient queries over audit trail.

Clean Code: Single Responsibility - only handles audit log persistence,
not business logic or policy enforcement.
"""

from __future__ import annotations

from backend.logger import get_logger
from backend.type_defs import AuditLogDict

from .base_repository import BaseRepository

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

logger = get_logger(__name__)


class AuditRepository(BaseRepository):
    """Repository for audit log management (append-only).

    Responsibilities:
    - Store audit events (create, read, delete operations)
    - Enforce immutability (no updates, only appends)
    - Query audit trail by date, user, action, resource
    - Maintain compliance with regulatory requirements
    """

    AUDIT_LOGS_GROUP = "audit_logs"

    def __init__(self, h5_file_path: str | Path) -> None:
        """Initialize audit repository."""
        super().__init__(h5_file_path)
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure required HDF5 structure exists."""
        try:
            with self._open_file("a") as f:
                f.require_group(self.AUDIT_LOGS_GROUP)  # type: ignore[attr-defined]
            logger.info("AUDIT_STRUCTURE_READY", file_path=str(self.h5_file_path))
        except OSError as e:
            logger.error("AUDIT_STRUCTURE_INIT_FAILED", error=str(e))
            raise

    def create(self, entity: AuditLogDict, **kwargs: Any) -> str:
        """Create audit log entry (append-only).

        Args:
            entity: Audit event data with action, user, resource, result

        Returns:
            Audit log ID (UUID)

        Raises:
            ValueError: If entity is invalid
            IOError: If HDF5 operation fails
        """
        # Validate required fields
        required_fields = {"action", "user_id", "resource", "result"}
        if not all(key in entity for key in required_fields):
            raise ValueError(f"Audit log missing required fields: {required_fields}")

        try:
            log_id = str(uuid4())

            with self._open_file("r+") as f:
                logs_group = f[self.AUDIT_LOGS_GROUP]
                log_group = logs_group.create_group(log_id)  # type: ignore[attr-defined]

                # Store log data - ensure timestamp is ISO string
                timestamp_raw = entity.get("timestamp", datetime.now(UTC))
                timestamp_str = (
                    timestamp_raw.isoformat()
                    if isinstance(timestamp_raw, datetime)
                    else timestamp_raw
                )
                log_group.attrs["timestamp"] = timestamp_str
                log_group.attrs["action"] = entity.get("action", "")
                log_group.attrs["user_id"] = entity.get("user_id", "")
                log_group.attrs["resource"] = entity.get("resource", "")
                log_group.attrs["result"] = entity.get("result", "")

                # Store additional details as JSON
                details = entity.get("details")
                if details:
                    log_group.attrs["details"] = json.dumps(details)

            self._log_operation("create", log_id)
            return log_id

        except Exception as e:
            self._log_operation("create", status="failed", error=str(e))
            raise

    def read(self, entity_id: str) -> dict[str, Any] | None:
        """Read audit log entry.

        Args:
            entity_id: Audit log ID

        Returns:
            Audit log data, or None if not found
        """
        try:
            with self._open_file("r") as f:
                if entity_id not in f[self.AUDIT_LOGS_GROUP]:  # type: ignore[operator]
                    return None

                log_group = f[self.AUDIT_LOGS_GROUP][entity_id]  # type: ignore[index]
                log_data: Dict[str, Any] = {
                    "log_id": entity_id,
                    "timestamp": log_group.attrs.get("timestamp", ""),  # type: ignore[attr-defined]
                    "action": log_group.attrs.get("action", ""),  # type: ignore[attr-defined]
                    "user_id": log_group.attrs.get("user_id", ""),  # type: ignore[attr-defined]
                    "resource": log_group.attrs.get("resource", ""),  # type: ignore[attr-defined]
                    "result": log_group.attrs.get("result", ""),  # type: ignore[attr-defined]
                }

                # Parse details if present
                if "details" in log_group.attrs:  # type: ignore[attr-defined]
                    try:
                        log_data["details"] = json.loads(log_group.attrs["details"])  # type: ignore[attr-defined]
                    except json.JSONDecodeError:
                        log_data["details"] = {}

                return log_data

        except Exception as e:
            logger.error("AUDIT_READ_FAILED", log_id=entity_id, error=str(e))
            return None

    def update(self, entity_id: str, entity: AuditLogDict) -> bool:
        """Update is not allowed on audit logs (append-only).

        Raises:
            NotImplementedError: Audit logs are immutable
        """
        raise NotImplementedError("Audit logs are append-only and cannot be updated")

    def delete(self, entity_id: str) -> bool:
        """Delete is not allowed on audit logs (append-only).

        Raises:
            NotImplementedError: Audit logs are immutable
        """
        raise NotImplementedError("Audit logs are append-only and cannot be deleted")

    def list_all(
        self,
        limit: Optional[int] = None,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List audit logs with optional filtering.

        Args:
            limit: Maximum logs to return
            action: Filter by action type
            user_id: Filter by user ID
            resource: Filter by resource

        Returns:
            List of audit logs
        """
        try:
            with self._open_file("r") as f:
                logs_group = f[self.AUDIT_LOGS_GROUP]
                log_ids = sorted(
                    logs_group.keys(), reverse=True
                )  # Most recent first [attr-defined]

                if limit:
                    log_ids = log_ids[:limit]

                results = []
                for log_id in log_ids:
                    log_data = self.read(log_id)
                    if log_data:
                        # Apply filters
                        if action and log_data.get("action") != action:
                            continue
                        if user_id and log_data.get("user_id") != user_id:
                            continue
                        if resource and log_data.get("resource") != resource:
                            continue

                        results.append(log_data)

                return results

        except Exception as e:
            logger.error("AUDIT_LIST_FAILED", error=str(e))
            return []

    def get_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Get audit logs within date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum logs to return

        Returns:
            List of audit logs in date range
        """
        try:
            with self._open_file("r") as f:
                logs_group = f[self.AUDIT_LOGS_GROUP]
                results = []

                for log_id in logs_group.keys():  # type: ignore[attr-defined]
                    log_data = self.read(log_id)
                    if not log_data:
                        continue

                    try:
                        timestamp_str = log_data.get("timestamp")
                        if not timestamp_str or not isinstance(timestamp_str, str):
                            continue
                        log_timestamp = datetime.fromisoformat(timestamp_str)
                        if start_date <= log_timestamp <= end_date:
                            results.append(log_data)
                    except (ValueError, KeyError):
                        continue

                    if limit and len(results) >= limit:
                        break

                return sorted(results, key=lambda x: x["timestamp"], reverse=True)

        except Exception as e:
            logger.error("AUDIT_DATE_RANGE_FAILED", error=str(e))
            return []
