"""Unit tests for clinic access validation utilities.

Tests horizontal privilege escalation prevention and SUPERADMIN bypass logic.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Multi-Tenancy Phase 2
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.infrastructure.auth.domain.entities.user import User, UserRole
from backend.infrastructure.auth.utils.clinic_access import (
    require_superadmin,
    validate_clinic_access,
)


class TestValidateClinicAccess:
    """Tests for validate_clinic_access() function."""

    def test_same_clinic_access_allowed(self):
        """Regular user can access their own clinic."""
        user = User(
            id="user-1",
            email="doctor@clinic.com",
            clinic_id="clinic-A",
            roles=[]
        )

        # Should NOT raise
        validate_clinic_access("clinic-A", user)

    def test_different_clinic_access_denied(self):
        """Regular user CANNOT access other clinic (horizontal privilege escalation blocked)."""
        user = User(
            id="user-1",
            email="doctor@clinic.com",
            clinic_id="clinic-A",
            roles=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_clinic_access("clinic-B", user)

        assert exc_info.value.status_code == 403
        assert "clinic-B" in exc_info.value.detail
        assert "clinic-A" in exc_info.value.detail  # Error shows user's clinic

    def test_superadmin_bypass_enabled(self):
        """SUPERADMIN can access any clinic (bypass logic works)."""
        user = User(
            id="admin-1",
            email="admin@aurity.io",
            clinic_id="clinic-A",
            roles=[UserRole.SUPERADMIN]
        )

        # Should NOT raise (different clinic OK for SUPERADMIN)
        validate_clinic_access("clinic-B", user)

    def test_no_clinic_assigned(self):
        """User without clinic_id cannot access any clinic."""
        user = User(
            id="user-1",
            email="doctor@clinic.com",
            clinic_id=None,  # No clinic assigned
            roles=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_clinic_access("clinic-A", user)

        assert exc_info.value.status_code == 403
        assert "no clinic assigned" in exc_info.value.detail.lower()

    def test_custom_action_message(self):
        """Custom action parameter appears in error message."""
        user = User(
            id="user-1",
            email="doctor@clinic.com",
            clinic_id="clinic-A",
            roles=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_clinic_access("clinic-B", user, action="delete clinic")

        assert "delete clinic" in exc_info.value.detail

    def test_superadmin_bypass_disabled(self):
        """SUPERADMIN bypass can be disabled (strict clinic access)."""
        user = User(
            id="admin-1",
            email="admin@aurity.io",
            clinic_id="clinic-A",
            roles=[UserRole.SUPERADMIN]
        )

        # Should RAISE even for SUPERADMIN (bypass disabled)
        with pytest.raises(HTTPException) as exc_info:
            validate_clinic_access("clinic-B", user, allow_superadmin=False)

        assert exc_info.value.status_code == 403


class TestRequireSuperadmin:
    """Tests for require_superadmin() function."""

    def test_superadmin_role_check_passes(self):
        """SUPERADMIN passes role check."""
        user = User(
            id="admin-1",
            email="admin@aurity.io",
            clinic_id=None,
            roles=[UserRole.SUPERADMIN]
        )

        # Should NOT raise
        require_superadmin(user)

    def test_regular_user_role_check_fails(self):
        """Regular user fails SUPERADMIN check."""
        user = User(
            id="user-1",
            email="doctor@clinic.com",
            clinic_id="clinic-A",
            roles=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            require_superadmin(user)

        assert exc_info.value.status_code == 403
        assert "SUPERADMIN role" in exc_info.value.detail

    def test_clinician_role_not_sufficient(self):
        """FI-clinician role is NOT sufficient (requires FI-superadmin)."""
        user = User(
            id="user-1",
            email="clinician@clinic.com",
            clinic_id="clinic-A",
            roles=[UserRole.CLINICIAN]  # FI-clinician, not FI-superadmin
        )

        with pytest.raises(HTTPException) as exc_info:
            require_superadmin(user)

        assert exc_info.value.status_code == 403
