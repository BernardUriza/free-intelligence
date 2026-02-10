"""Pytest configuration and fixtures for Free Intelligence backend tests.

Provides reusable fixtures for testing with DI container, repositories, and services.
"""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from datetime import UTC
from typing import Union

import h5py
import pytest
from pathlib import Path


@pytest.fixture
def temp_h5_file() -> Generator[Path]:
    """Create temporary HDF5 file for testing.

    Yields:
        Path to temporary HDF5 file that will be cleaned up after test
    """
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        temp_path = Path(f.name)

    # Initialize HDF5 with minimal schema for tests
    with h5py.File(temp_path, "w") as f:
        f.create_group("sessions")
        f.create_group("audit_log")
        f.create_group("corpus")

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def audit_service(temp_h5_file: Path):
    """Get AuditService with direct instantiation.

    Returns:
        AuditService instance with AuditRepository
    """
    from backend.repositories.audit_repository import AuditRepository
    from backend.services.audit.services.audit_service import AuditService

    return AuditService(repository=AuditRepository(temp_h5_file))


# Factory fixtures for test data


@pytest.fixture
def session_factory():
    """Factory for creating test session data.

    Returns:
        Callable that generates session dictionaries
    """

    def _create_session(
        session_id: str = "test_session_001", user_id: str = "test_user", status: str = "active"
    ) -> dict[str, str]:
        return {
            "session_id": session_id,
            "user_id": user_id,
            "status": status,
        }

    return _create_session


@pytest.fixture
def athlete_factory():
    """Factory for creating test athlete data.

    Returns:
        Callable that generates athlete dictionaries
    """

    def _create_athlete(
        athlete_id: str = "athlete_001",
        name: str = "Test Athlete",
        coach_id: str = "coach_001",
    ) -> dict[str, Union[str, int]]:
        return {
            "id": athlete_id,
            "name": name,
            "coachId": coach_id,
            "sessionsCompleted": 0,
            "sessionsTotal": 10,
            "completionRate": 0,
            "fitnessLevel": "beginner",
            "goal": "improve_cardio",
        }

    return _create_athlete


@pytest.fixture
def audit_entry_factory():
    """Factory for creating test audit log entries.

    Returns:
        Callable that generates audit entry dictionaries
    """
    from datetime import datetime

    def _create_audit_entry(
        action: str = "test_action",
        user_id: str = "test_user",
        resource: str = "test_resource",
        result: str = "success",
    ) -> dict[str, str]:
        return {
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "result": result,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return _create_audit_entry


# ============================================================================
# FastAPI Testing Infrastructure (P3-3)
# ============================================================================

# Import fixtures from fixtures/ directory
pytest_plugins = [
    "backend.tests.fixtures.services",
    "backend.tests.fixtures.repositories",
    "backend.tests.fixtures.auth",
]


@pytest.fixture
def app():
    """FastAPI application instance for testing.

    Returns:
        FastAPI app instance with all routes registered

    Example:
        >>> def test_endpoint(app, client):
        ...     # Override dependencies
        ...     app.dependency_overrides[get_current_user] = lambda: mock_user
        ...     response = client.get("/api/protected")
        ...     app.dependency_overrides.clear()
    """
    from backend.app.main import app as fastapi_app

    yield fastapi_app

    # Cleanup: Clear any dependency overrides after test
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """FastAPI TestClient for making HTTP requests.

    Uses context manager to activate lifespan (required for repository init).

    Args:
        app: FastAPI app fixture

    Yields:
        TestClient instance

    Example:
        >>> def test_get_session(client):
        ...     response = client.get("/api/sessions/123")
        ...     assert response.status_code == 200
    """
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture
def override_dependencies(app):
    """Helper fixture for overriding FastAPI dependencies.

    Automatically clears overrides after test completion.

    Args:
        app: FastAPI app fixture

    Yields:
        App instance (for chaining)

    Example:
        >>> def test_with_mocks(app, override_dependencies, mock_audit_service):
        ...     from backend.api.audit.dependencies import get_audit_service
        ...     app.dependency_overrides[get_audit_service] = lambda: mock_audit_service
        ...     # Test code here
        ...     # Overrides automatically cleared after test
    """
    yield app
    app.dependency_overrides.clear()
