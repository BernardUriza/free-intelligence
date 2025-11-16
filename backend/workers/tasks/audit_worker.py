"""Audit worker - Event logging."""

from __future__ import annotations

from typing import Any

from backend.app.audit.sink import write_audit_event
from backend.logger import get_logger
from backend.workers.tasks.base_worker import WorkerResult

logger = get_logger(__name__)


def log_audit_event_worker(
    action: str,
    user_id: str,
    resource: str,
    result: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synchronous audit logging.

    Args:
        action: Action performed
        user_id: User identifier
        resource: Resource path
        result: Result status
        metadata: Additional context

    Returns:
        WorkerResult with event_id
    """
    try:
        event_id = write_audit_event(
            action=action,
            user_id=user_id,
            resource=resource,
            result=result,
            metadata=metadata or {},
        )

        logger.info("AUDIT_EVENT_LOGGED", event_id=event_id, action=action)

        return WorkerResult(result={"event_id": event_id}).to_dict()

    except Exception as e:
        logger.error("AUDIT_EVENT_FAILED", error=str(e), action=action)
        raise
