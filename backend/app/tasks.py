"""Celery tasks for async operations.

Background tasks for Free Intelligence.

File: backend/app/tasks.py
Card: AUR-PROMPT-3.1
Created: 2025-11-09
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict

from backend.app.audit.sink import write_audit_event
from backend.app.celery import celery_app
from backend.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="audit.log_event", bind=True)
def log_audit_event(
    self: Any,
    action: str,
    user_id: str,
    resource: str,
    result: str,
    metadata: Dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Log audit event asynchronously.

    Args:
        self: Task instance
        action: Action performed (e.g., TIMELINE_HASH_VERIFIED)
        user_id: User/resource identifier
        resource: Resource path
        result: Result status (SUCCESS, FAILED, etc.)
        metadata: Additional context

    Returns:
        dict with event_id and status
    """
    try:
        event_id = write_audit_event(
            action=action,
            user_id=user_id,
            resource=resource,
            result=result,
            metadata=metadata or {},
        )

        logger.info(
            "AUDIT_EVENT_LOGGED",
            event_id=event_id,
            action=action,
            task_id=self.request.id,
        )

        return {"event_id": event_id, "status": "SUCCESS", "task_id": self.request.id}

    except Exception as e:
        logger.error("AUDIT_EVENT_FAILED", error=str(e), action=action, task_id=self.request.id)
        raise


@celery_app.task(name="example.async_operation", bind=True)
def example_async_operation(self: Any, data: Dict[str, Any]) -> dict[str, Any]:
    """Example async task template.

    Args:
        self: Task instance
        data: Input data

    Returns:
        dict with result
    """
    logger.info("ASYNC_OPERATION_STARTED", task_id=self.request.id, data=data)

    # Placeholder for actual work
    result = {"processed_at": datetime.now(UTC).isoformat(), "status": "SUCCESS"}

    logger.info("ASYNC_OPERATION_COMPLETED", task_id=self.request.id, result=result)
    return result
