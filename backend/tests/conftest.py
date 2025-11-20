"""Pytest configuration and fixtures for Free Intelligence backend tests.

Provides reusable fixtures for testing with DI container, repositories, and services.
"""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from backend.compat import UTC
from pathlib import Path
from typing import TYPE_CHECKING, Union

import pytest

if TYPE_CHECKING:
    from packages.fi_common.infrastructure.container import DIContainer


@pytest.fixture
def temp_h5_file() -> Generator[Path, None, None]:
    """Create temporary HDF5 file for testing.

    Yields:
        Path to temporary HDF5 file that will be cleaned up after test
    """
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as f:
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def di_container(temp_h5_file: Path) -> Generator[DIContainer, None, None]:
    """Create DI container with temporary HDF5 database.

    Args:
        temp_h5_file: Temporary HDF5 file path from fixture

    Returns:
        DIContainer instance with isolated test database
    """
    # Initialize HDF5 with minimal schema
    import h5py

    from packages.fi_common.infrastructure.container import DIContainer

    with h5py.File(temp_h5_file, "w") as f:
        # Create minimal groups for testing
        f.create_group("sessions")
        f.create_group("audit_log")
        f.create_group("corpus")

    container = DIContainer(h5_file_path=temp_h5_file)
    yield container

    # Cleanup
    container.reset()


@pytest.fixture
def session_service(di_container: DIContainer):
    """Get SessionService from DI container.

    Args:
        di_container: DI container fixture

    Returns:
        SessionService instance
    """
    return di_container.get_session_service()


@pytest.fixture
def audit_service(di_container: DIContainer):
    """Get AuditService from DI container.

    Args:
        di_container: DI container fixture

    Returns:
        AuditService instance
    """
    return di_container.get_audit_service()


@pytest.fixture
def corpus_service(di_container: DIContainer):
    """Get CorpusService from DI container.

    Args:
        di_container: DI container fixture

    Returns:
        CorpusService instance
    """
    return di_container.get_corpus_service()


@pytest.fixture
def export_service(di_container: DIContainer):
    """Get ExportService from DI container.

    Args:
        di_container: DI container fixture

    Returns:
        ExportService instance
    """
    return di_container.get_export_service()


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
