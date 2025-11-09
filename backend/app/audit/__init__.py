"""Audit sink module.

Parquet-based audit event persistence.
"""

from __future__ import annotations

from backend.app.audit.sink import write_audit_event

__all__ = ["write_audit_event"]
