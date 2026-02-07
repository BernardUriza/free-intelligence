"""Mock authentication fixtures for testing.

Provides Mock instances for auth dependencies (current_user, verify_token, etc.)
Use with FastAPI's app.dependency_overrides for testing authenticated endpoints.

Pattern:
    def test_authenticated_endpoint(client, mock_current_user):
        app.dependency_overrides[get_current_user] = lambda: mock_current_user
        response = client.get("/api/protected")
        assert response.status_code == 200

Author: Claude Code (P3-3 Testing Infrastructure)
Created: 2026-02-02
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest


@dataclass
class MockUser:
    """Mock user for testing authenticated endpoints.

    Mimics the structure of a real User entity.
    """

    id: str = "test_user_123"
    email: str = "test@example.com"
    name: str = "Test User"
    role: str = "doctor"
    clinic_id: str | None = "clinic_123"
    permissions: list[str] | None = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = ["read:sessions", "write:sessions", "read:patients"]


@pytest.fixture
def mock_current_user():
    """Mock current_user dependency for testing.

    Returns:
        MockUser instance with default test user data

    Example:
        >>> def test_create_session(client, mock_current_user):
        ...     from backend.api.dependencies import get_current_user
        ...     app.dependency_overrides[get_current_user] = lambda: mock_current_user
        ...     response = client.post("/api/sessions", json={...})
        ...     assert response.status_code == 201
    """
    return MockUser()


@pytest.fixture
def mock_admin_user():
    """Mock admin user for testing admin-only endpoints.

    Returns:
        MockUser with admin role and all permissions
    """
    return MockUser(
        id="admin_123",
        email="admin@example.com",
        name="Admin User",
        role="admin",
        permissions=["*"],  # All permissions
    )


@pytest.fixture
def mock_doctor_user():
    """Mock doctor user for testing doctor-scoped endpoints.

    Returns:
        MockUser with doctor role
    """
    return MockUser(
        id="doctor_123",
        email="doctor@clinic.com",
        name="Dr. Test",
        role="doctor",
        clinic_id="clinic_123",
        permissions=["read:sessions", "write:sessions", "read:patients", "write:soap"],
    )


@pytest.fixture
def mock_patient_user():
    """Mock patient user for testing patient-scoped endpoints.

    Returns:
        MockUser with patient role (limited permissions)
    """
    return MockUser(
        id="patient_123",
        email="patient@example.com",
        name="Patient Test",
        role="patient",
        clinic_id=None,
        permissions=["read:own_sessions"],
    )


@pytest.fixture
def mock_verify_token():
    """Mock verify_token dependency for testing.

    Returns:
        Callable that returns a mock decoded token

    Example:
        >>> app.dependency_overrides[verify_token] = mock_verify_token
    """

    def _verify_token(token: str | None = None) -> dict[str, Any]:
        return {
            "sub": "test_user_123",
            "email": "test@example.com",
            "permissions": ["read:sessions", "write:sessions"],
        }

    return _verify_token


@pytest.fixture
def mock_auth_header():
    """Mock authorization header for testing.

    Returns:
        Dict with Bearer token header

    Example:
        >>> response = client.get("/api/protected", headers=mock_auth_header)
    """
    return {"Authorization": "Bearer mock_test_token"}
