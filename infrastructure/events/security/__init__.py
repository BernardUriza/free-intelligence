"""Security module - PHI redaction and RBAC for Event Sourcing.

Provides:
- PHI detection and redaction
- RBAC for event stream access
- Audit logging

Usage:
    from infrastructure.events.security import redact_phi, check_event_access

    safe_payload = redact_phi(payload)
    if check_event_access(user, "session_index"):
        # Allow access
"""

from infrastructure.events.security.phi_redaction import (
    PHI_PATTERNS,
    detect_phi,
    redact_phi,
)
from infrastructure.events.security.rbac import (
    EventPermission,
    check_event_access,
    require_event_permission,
)

__all__ = [
    # PHI
    "redact_phi",
    "detect_phi",
    "PHI_PATTERNS",
    # RBAC
    "EventPermission",
    "check_event_access",
    "require_event_permission",
]
