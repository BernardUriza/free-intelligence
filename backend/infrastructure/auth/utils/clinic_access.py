"""Clinic access validation utilities for multi-tenancy.

Prevents horizontal privilege escalation by validating that users can only
access clinics they belong to. SUPERADMIN users bypass these checks.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Multi-Tenancy Phase 2
"""

from __future__ import annotations

from fastapi import HTTPException

from backend.infrastructure.auth.domain.entities.user import User, UserRole


def validate_clinic_access(
    clinic_id: str,
    current_user: User,
    *,
    allow_superadmin: bool = True,
    action: str = "access clinic"
) -> None:
    """
    Validate user can access clinic.

    Prevents horizontal privilege escalation (Doctor A accessing Clinic B's data).

    Args:
        clinic_id: Clinic ID to validate access for
        current_user: Authenticated user from Auth0
        allow_superadmin: If True, SUPERADMIN can bypass (default: True)
        action: Action description for error message (e.g., "upload media")

    Raises:
        HTTPException: 403 if user cannot access clinic

    Examples:
        # Standard validation (SUPERADMIN bypass enabled)
        validate_clinic_access(clinic_id, current_user)

        # Custom error message
        validate_clinic_access(clinic_id, current_user, action="delete clinic")

        # No SUPERADMIN bypass (enforce strict clinic access)
        validate_clinic_access(clinic_id, current_user, allow_superadmin=False)
    """
    # SUPERADMIN bypass (if allowed)
    if allow_superadmin and UserRole.SUPERADMIN in current_user.roles:
        return  # SUPERADMIN can access any clinic

    # Regular user: Must have clinic_id assigned
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=403,
            detail=f"User has no clinic assigned. Contact admin or create a clinic to {action}."
        )

    # Regular user: Must match clinic_id
    if clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to clinic '{clinic_id}'. You can only {action} for clinic '{current_user.clinic_id}'."
        )


def require_superadmin(current_user: User) -> None:
    """
    Validate user has SUPERADMIN role.

    Args:
        current_user: Authenticated user from Auth0

    Raises:
        HTTPException: 403 if user is not SUPERADMIN

    Example:
        # Admin-only endpoint
        @router.get("/admin/stats")
        def admin_stats(current_user: User = Depends(get_current_user)):
            require_superadmin(current_user)
            # ... admin logic
    """
    if UserRole.SUPERADMIN not in current_user.roles:
        raise HTTPException(
            status_code=403,
            detail="This operation requires SUPERADMIN role"
        )


__all__ = ["validate_clinic_access", "require_superadmin"]
