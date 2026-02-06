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
        current_user: Authenticated user from JWT
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
        current_user: Authenticated user from JWT

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


def validate_doctor_access(
    doctor_id: str,
    current_user: User,
    *,
    allow_superadmin: bool = True,
    action: str = "access doctor data",
) -> None:
    """
    Validate user can access doctor-scoped data.

    Prevents horizontal privilege escalation (Doctor A accessing Doctor B's history).
    Use for endpoints that accept doctor_id as parameter.

    Args:
        doctor_id: Doctor ID to validate access for
        current_user: Authenticated user from JWT
        allow_superadmin: If True, SUPERADMIN can access any doctor's data
        action: Action description for error message

    Raises:
        HTTPException: 403 if user cannot access doctor's data

    Examples:
        # In endpoint with doctor_id query param
        @router.get("/history")
        async def get_history(
            doctor_id: str = Query(...),
            current_user: User = Depends(get_current_user),
        ):
            validate_doctor_access(doctor_id, current_user)
            # ... fetch history

        # In endpoint with doctor_id in request body
        @router.post("/search")
        async def search(
            request: SearchRequest,
            current_user: User = Depends(get_current_user),
        ):
            validate_doctor_access(request.doctor_id, current_user)
            # ... do search
    """
    if allow_superadmin and UserRole.SUPERADMIN in current_user.roles:
        return  # SUPERADMIN can access any doctor's data

    if doctor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot {action} for another doctor. You can only access your own data.",
        )


def validate_session_access(
    session_id: str,
    current_user: User,
    *,
    allow_superadmin: bool = True,
    action: str = "access session",
) -> None:
    """
    Validate user can access a session by checking clinic_id in HDF5.

    Reads the session's clinic_id attribute from the HDF5 corpus file
    and validates it matches the user's clinic.

    Args:
        session_id: Session ID to validate access for
        current_user: Authenticated user from JWT
        allow_superadmin: If True, SUPERADMIN can access any session
        action: Action description for error message

    Raises:
        HTTPException: 403 if user cannot access session
        HTTPException: 404 if session doesn't exist

    Example:
        @router.get("/sessions/{session_id}/data")
        async def get_session_data(
            session_id: str,
            current_user: User = Depends(get_current_user),
        ):
            validate_session_access(session_id, current_user)
            # ... fetch session data
    """
    from pathlib import Path

    # SUPERADMIN bypass
    if allow_superadmin and UserRole.SUPERADMIN in current_user.roles:
        return

    # Load session clinic_id from HDF5
    corpus_path = Path("corpus/hdf5/conversations.h5")
    session_clinic_id: str | None = None

    if corpus_path.exists():
        try:
            import h5py

            with h5py.File(corpus_path, "r") as f:
                if "sessions" in f and session_id in f["sessions"]:
                    session_group = f["sessions"][session_id]
                    if hasattr(session_group, "attrs"):
                        session_clinic_id = session_group.attrs.get("clinic_id")
        except Exception:
            pass  # If HDF5 read fails, proceed with None

    if session_clinic_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found",
        )

    if session_clinic_id != current_user.clinic_id:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to session '{session_id}'. Cannot {action} for another clinic.",
        )


__all__ = ["validate_clinic_access", "require_superadmin", "validate_doctor_access", "validate_session_access"]
