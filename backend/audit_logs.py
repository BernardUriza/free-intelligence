"""Compatibility wrapper - re-exports from backend.services.audit_logs or backend.common.audit_logs"""

from __future__ import annotations

try:
    from backend.common.audit_logs import *  # noqa: F401, F403
except ImportError:
    try:
        from backend.services.audit_logs import *  # noqa: F401, F403
    except ImportError:
        # Provide stub for missing module
        def append_audit_log(*args, **kwargs):
            """Stub function for audit logging"""
            pass
