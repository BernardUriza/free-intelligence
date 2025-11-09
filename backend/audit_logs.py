"""Compatibility wrapper - re-exports from backend.services.audit_service"""

from __future__ import annotations

from typing import Any, Optional

# Export AuditService class for backward compatibility
# pyright: reportUnusedImport=false
try:
    from backend.services.audit_service import AuditService
except ImportError:
    pass

__all__ = ["AuditService", "append_audit_log", "read_audit_logs"]


def append_audit_log(
    corpus_path: str,
    operation: str,
    user_id: str,
    outcome: str = "SUCCESS",
    metadata: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> None:
    """Append audit log entry.

    This is a compatibility shim for legacy code. New code should use AuditService.

    Args:
        corpus_path: Path to corpus (ignored in current implementation)
        operation: Operation performed (e.g., "TIMELINE_HASH_VERIFIED")
        user_id: User/resource identifier
        outcome: Result status (SUCCESS, FAILED, etc.)
        metadata: Additional context
        **kwargs: Additional fields (ignored)
    """
    # TODO: Implement proper audit logging via AuditService when needed
    # For now, this is a no-op to unblock router loading
    pass
