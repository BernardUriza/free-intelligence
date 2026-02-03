"""Re-export AuditService from canonical location.

This module exists for backward compatibility.
The actual implementation is in backend.services.audit.services.audit_service.
"""

from backend.services.audit.services.audit_service import AuditService

__all__ = ["AuditService"]
