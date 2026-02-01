"""Authentication utilities for multi-tenancy and access control."""

from __future__ import annotations

from .clinic_access import require_superadmin, validate_clinic_access

__all__ = ["validate_clinic_access", "require_superadmin"]
