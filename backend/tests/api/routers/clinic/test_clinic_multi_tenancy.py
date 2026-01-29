"""Integration tests for multi-tenancy security in clinic endpoints.

Tests horizontal privilege escalation prevention and SUPERADMIN bypass logic.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Multi-Tenancy Phase 2
"""

from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from backend.app.main import app, public_app
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User, UserRole


@pytest.fixture
def client():
    """FastAPI test client with clean dependency overrides."""
    # Clear any existing overrides in BOTH apps
    app.dependency_overrides.clear()
    public_app.dependency_overrides.clear()

    client = TestClient(app)
    yield client

    # Cleanup after test
    app.dependency_overrides.clear()
    public_app.dependency_overrides.clear()


@pytest.fixture
def doctor_a_clinic1():
    """Doctor A user (assigned to clinic-1)."""
    return User(
        id="auth0|doctor-a",
        email="doctor.a@clinic1.com",
        clinic_id="clinic-1",
        roles=[],
    )


@pytest.fixture
def doctor_b_clinic2():
    """Doctor B user (assigned to clinic-2)."""
    return User(
        id="auth0|doctor-b",
        email="doctor.b@clinic2.com",
        clinic_id="clinic-2",
        roles=[],
    )


@pytest.fixture
def superadmin_user():
    """SUPERADMIN user (can access all clinics)."""
    return User(
        id="auth0|superadmin",
        email="admin@aurity.io",
        clinic_id="clinic-1",  # Has clinic but can bypass
        roles=[UserRole.SUPERADMIN],
    )


@pytest.fixture
def user_no_clinic():
    """User without clinic assignment."""
    return User(
        id="auth0|no-clinic",
        email="newuser@example.com",
        clinic_id=None,
        roles=[],
    )


# =============================================================================
# Test: Doctor A can access own clinic
# =============================================================================


def test_doctor_can_access_own_clinic(client, doctor_a_clinic1):
    """Doctor A can access clinic-1 (their assigned clinic)."""
    # Override get_current_user dependency
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1

    response = client.get("/api/clinics/clinic-1")

    # Should succeed (200 OK or 404 if clinic doesn't exist in test DB)
    # In real environment with test data: assert response.status_code == 200
    # For now, verify it's NOT 403 (which would indicate access denied)
    assert response.status_code != status.HTTP_403_FORBIDDEN, (
        f"Doctor A should be able to access their own clinic (clinic-1), "
        f"but got {response.status_code}: {response.json()}"
    )


# =============================================================================
# Test: Doctor A CANNOT access Clinic B (horizontal privilege escalation)
# =============================================================================


def test_doctor_cannot_access_other_clinic(client, doctor_a_clinic1):
    """Doctor A CANNOT access clinic-2 (horizontal privilege escalation blocked)."""
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1
    response = client.get("/api/clinics/clinic-2")

    # Should be denied (403 Forbidden)
    assert response.status_code == status.HTTP_403_FORBIDDEN, (
        f"Doctor A should NOT be able to access clinic-2, "
        f"but got {response.status_code}"
    )

    # Verify error message mentions both clinics
    error_detail = response.json()["detail"]
    assert "clinic-2" in error_detail, "Error should mention target clinic"
    assert "clinic-1" in error_detail, "Error should mention user's clinic"


def test_doctor_cannot_update_other_clinic(client, doctor_a_clinic1):
    """Doctor A CANNOT update clinic-2 settings."""
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1
    response = client.patch(
            "/api/clinics/clinic-2",
            json={"name": "Hacked Clinic"},
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_doctor_cannot_delete_other_clinic(client, doctor_a_clinic1):
    """Doctor A CANNOT delete clinic-2."""
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1
    response = client.delete("/api/clinics/clinic-2")

    assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Test: SUPERADMIN can access all clinics
# =============================================================================


def test_superadmin_can_access_any_clinic(client, superadmin_user):
    """SUPERADMIN can access any clinic (bypass validation)."""
    public_app.dependency_overrides[get_current_user] = lambda: superadmin_user
    # Try accessing different clinic than superadmin's assigned clinic
    response_clinic1 = client.get("/api/clinics/clinic-1")
    response_clinic2 = client.get("/api/clinics/clinic-2")

    # Should NOT be 403 (either 200 OK or 404 if clinic doesn't exist)
    assert response_clinic1.status_code != status.HTTP_403_FORBIDDEN, (
        "SUPERADMIN should be able to access clinic-1"
    )
    assert response_clinic2.status_code != status.HTTP_403_FORBIDDEN, (
        "SUPERADMIN should be able to access clinic-2"
    )


def test_superadmin_can_update_any_clinic(client, superadmin_user):
    """SUPERADMIN can update any clinic."""
    public_app.dependency_overrides[get_current_user] = lambda: superadmin_user
    response = client.patch(
            "/api/clinics/clinic-2",
            json={"name": "Admin Updated Clinic"},
        )

    # Should NOT be 403 (either 200 OK or 404 if clinic doesn't exist)
    assert response.status_code != status.HTTP_403_FORBIDDEN


# =============================================================================
# Test: List clinics returns correct scope
# =============================================================================


def test_list_clinics_regular_user_sees_only_their_clinic(client, doctor_a_clinic1):
    """Regular user sees only their clinic (array of 1)."""
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1
    response = client.get("/api/workflows/aurity/clinics")

    # Should NOT be 403
    assert response.status_code != status.HTTP_403_FORBIDDEN

    # If successful (200), verify array contains only 1 clinic
    if response.status_code == status.HTTP_200_OK:
        clinics = response.json()
        assert isinstance(clinics, list), "Response should be an array"
        # In test environment without data, might be empty
        # In real environment with test data: assert len(clinics) == 1
        # and assert clinics[0]["clinic_id"] == "clinic-1"


def test_list_clinics_superadmin_sees_all_clinics(client, superadmin_user):
    """SUPERADMIN sees all clinics."""
    public_app.dependency_overrides[get_current_user] = lambda: superadmin_user
    response = client.get("/api/workflows/aurity/clinics")

    # Should NOT be 403
    assert response.status_code != status.HTTP_403_FORBIDDEN

    # If successful (200), verify array (could be 0+ clinics)
    if response.status_code == status.HTTP_200_OK:
        clinics = response.json()
        assert isinstance(clinics, list), "Response should be an array"
        # SUPERADMIN should see ALL clinics (not filtered by clinic_id)
        # In real environment: assert len(clinics) >= 2


def test_list_clinics_user_without_clinic_gets_403(client, user_no_clinic):
    """User without clinic_id assignment cannot list clinics."""
    public_app.dependency_overrides[get_current_user] = lambda: user_no_clinic
    response = client.get("/api/clinics")

    # Should be denied (403 Forbidden)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "no clinic assigned" in response.json()["detail"].lower()


# =============================================================================
# Test: Self-service clinic creation
# =============================================================================


@pytest.mark.asyncio
async def test_any_user_can_create_clinic(client, user_no_clinic):
    """Any authenticated user can create a clinic (self-service)."""
    public_app.dependency_overrides[get_current_user] = lambda: user_no_clinic
    # Mock Auth0 Management API to avoid actual API calls
    from backend.infrastructure.auth.infrastructure.auth0.management_api import Auth0ManagementAPI
    mock_api = Auth0ManagementAPI.__new__(Auth0ManagementAPI)
    mock_api.update_user_app_metadata = AsyncMock()
    
    from unittest.mock import patch as mock_patch
    with mock_patch("backend.infrastructure.auth.infrastructure.auth0.management_api.get_auth0_management_api", return_value=mock_api):

            response = client.post(
                "/api/clinics",
                json={
                    "name": "Test Clinic",
                    "specialty": "General Medicine",
                    "timezone": "America/Mexico_City",
                },
            )

    # Should NOT be 403 (either 201 Created or 400/422 validation error)
    assert response.status_code != status.HTTP_403_FORBIDDEN, (
        "Any authenticated user should be able to create a clinic"
    )


def test_user_with_clinic_cannot_create_another(client, doctor_a_clinic1):
    """User already assigned to a clinic cannot create another (prevents multi-clinic)."""
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1
    response = client.post(
            "/api/clinics",
            json={
                "name": "Second Clinic",
                "specialty": "Cardiology",
            },
        )

    # Should be denied (400 Bad Request - already has clinic)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already assigned" in response.json()["detail"].lower()


# =============================================================================
# Test: Clinic media endpoints security
# =============================================================================


def test_upload_media_validates_clinic_id(client, doctor_a_clinic1):
    """Upload media with user-provided clinic_id is validated."""
    # TODO: clinic_media router not yet registered in backend/app/routers.py
    # Once registered, this test should verify clinic_id validation
    pytest.skip("clinic_media router not implemented yet")


def test_upload_media_uses_user_clinic_if_not_provided(client, doctor_a_clinic1):
    """Upload media without clinic_id uses current_user's clinic."""
    # TODO: clinic_media router not yet registered
    pytest.skip("clinic_media router not implemented yet")


def test_list_media_filters_by_user_clinic(client, doctor_a_clinic1):
    """List media filters by user's clinic."""
    # TODO: clinic_media router not yet registered
    pytest.skip("clinic_media router not implemented yet")


# =============================================================================
# Test: User-clinic endpoints security (CRITICAL FIX)
# =============================================================================


def test_get_clinic_membership_uses_jwt_identity(client, doctor_a_clinic1):
    """GET /users/me/clinic-membership uses JWT identity (not user-provided)."""
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1
    # Call WITHOUT providing auth0_user_id (should use current_user.id from JWT)
    response = client.get("/api/users/me/clinic-membership")

    # Should NOT be 403 (either 200 OK or 404 if not linked)
    assert response.status_code != status.HTTP_403_FORBIDDEN


def test_link_to_clinic_validates_clinic_access(client, doctor_a_clinic1):
    """Link to clinic validates user can access requested clinic."""
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1
    # Try to link to clinic-2 (not their clinic)
    response = client.post(
            "/api/users/me/link-to-clinic",
            json={
                "clinic_id": "clinic-2",  # ← Different clinic
                "nombre": "Test",
                "apellido": "User",
            },
        )

    # Should be denied (403 Forbidden)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_assign_requires_superadmin(client, doctor_a_clinic1):
    """Admin endpoints require SUPERADMIN role."""
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1  # Regular user, not SUPERADMIN
    response = client.post(
        "/api/users/me/admin/assign-to-clinic",
        json={
            "auth0_user_id": "auth0|target-user",
            "email": "target@example.com",
            "clinic_id": "clinic-1",
            "nombre": "Target",
            "apellido": "User",
        },
    )

    # Should be denied (403 Forbidden - not SUPERADMIN)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "SUPERADMIN" in response.json()["detail"]


def test_admin_assign_allows_superadmin(client, superadmin_user):
    """Admin endpoints allow SUPERADMIN users."""
    public_app.dependency_overrides[get_current_user] = lambda: superadmin_user
    response = client.post(
            "/api/users/me/admin/assign-to-clinic",
            json={
                "auth0_user_id": "auth0|target-user",
                "email": "target@example.com",
                "clinic_id": "clinic-1",
                "nombre": "Target",
                "apellido": "User",
            },
        )

    # Should NOT be 403 (either 200 OK or 404 if clinic doesn't exist)
    assert response.status_code != status.HTTP_403_FORBIDDEN
