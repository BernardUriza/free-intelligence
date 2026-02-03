"""Mock repository fixtures for testing.

Provides Mock instances of repositories with proper spec for type checking.
Use for unit testing services that depend on repositories.

Pattern:
    def test_service_create(mock_session_repository):
        mock_session_repository.save.return_value = "session_123"
        service = SessionService(repository=mock_session_repository)
        result = service.create(session_data)
        assert result == "session_123"
        mock_session_repository.save.assert_called_once()

Author: Claude Code (P3-3 Testing Infrastructure)
Created: 2026-02-02
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_session_repository():
    """Mock ISessionRepository for testing.

    Returns:
        Mock instance with CRUD methods

    Example:
        >>> mock_session_repository.find_by_id.return_value = Session(
        ...     session_id="123",
        ...     status=SessionStatus.ACTIVE,
        ...     created_at="2026-01-01T00:00:00Z",
        ...     updated_at="2026-01-01T00:00:00Z"
        ... )
    """
    from backend.domain.interfaces.isession_repository import ISessionRepository

    repo = Mock(spec=ISessionRepository)
    repo.save = Mock()
    repo.find_by_id = Mock()
    repo.find_all = Mock(return_value=[])
    repo.update = Mock()
    repo.delete = Mock()
    repo.exists = Mock()
    repo.count = Mock(return_value=0)
    return repo


@pytest.fixture
def mock_soap_repository():
    """Mock ISOAPRepository for testing.

    Returns:
        Mock instance with SOAP CRUD methods
    """
    from backend.domain.interfaces.isoap_repository import ISOAPRepository

    repo = Mock(spec=ISOAPRepository)
    repo.save = Mock()
    repo.find_by_id = Mock()
    repo.find_by_session = Mock(return_value=[])
    repo.find_by_status = Mock(return_value=[])
    repo.update = Mock()
    repo.delete = Mock()
    repo.exists = Mock()
    repo.count = Mock(return_value=0)
    return repo


@pytest.fixture
def mock_patient_repository():
    """Mock IPatientRepository for testing.

    Returns:
        Mock instance with Patient CRUD methods
    """
    from backend.domain.interfaces.ipatient_repository import IPatientRepository

    repo = Mock(spec=IPatientRepository)
    repo.save = Mock()
    repo.find_by_id = Mock()
    repo.find_by_curp = Mock()
    repo.find_all = Mock(return_value=[])
    repo.update = Mock()
    repo.delete = Mock()
    repo.exists = Mock()
    repo.count = Mock(return_value=0)
    return repo


@pytest.fixture
def mock_order_repository():
    """Mock IOrderRepository for testing.

    Returns:
        Mock instance with Order CRUD methods
    """
    from backend.domain.interfaces.iorder_repository import IOrderRepository

    repo = Mock(spec=IOrderRepository)
    repo.save = Mock()
    repo.find_by_id = Mock()
    repo.find_by_session = Mock(return_value=[])
    repo.find_by_status = Mock(return_value=[])
    repo.update = Mock()
    repo.delete = Mock()
    repo.exists = Mock()
    repo.count = Mock(return_value=0)
    return repo


@pytest.fixture
def mock_audit_repository():
    """Mock audit repository for testing.

    Returns:
        Mock instance with audit logging methods
    """
    repo = Mock()
    repo.log_event = Mock()
    repo.get_events = Mock(return_value=[])
    repo.count_events = Mock(return_value=0)
    return repo
