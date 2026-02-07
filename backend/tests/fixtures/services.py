"""Mock services fixtures for FastAPI dependency injection testing.

Provides Mock instances of services with proper spec for type checking.
Use with FastAPI's app.dependency_overrides for testing endpoints.

Pattern:
    def test_endpoint(client, mock_audit_service):
        app.dependency_overrides[get_audit_service] = lambda: mock_audit_service
        response = client.post("/api/endpoint", json={...})
        assert response.status_code == 201
        mock_audit_service.log_action.assert_called_once()

Author: Claude Code (P3-3 Testing Infrastructure)
Created: 2026-02-02
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_audit_service():
    """Mock DIAuditService for testing.

    Provides a Mock with spec=DIAuditService.
    Pre-configured with log_action method.

    Returns:
        Mock instance of DIAuditService

    Example:
        >>> def test_create_session(client, mock_audit_service):
        ...     app.dependency_overrides[get_audit_service] = lambda: mock_audit_service
        ...     response = client.post("/api/sessions", json={...})
        ...     mock_audit_service.log_action.assert_called_once_with(
        ...         action="session_created",
        ...         user_id="test_user",
        ...         resource="session_123",
        ...         result="success"
        ...     )
    """
    from backend.api.audit.dependencies import DIAuditService

    service = Mock(spec=DIAuditService)
    service.log_action = Mock(return_value=None)
    return service


@pytest.fixture
def mock_session_service():
    """Mock SessionService for testing.

    Returns:
        Mock instance of SessionService with common methods
    """
    from backend.domain.session.services.session_service import SessionService

    service = Mock(spec=SessionService)
    service.create = Mock()
    service.get = Mock()
    service.update = Mock()
    service.delete = Mock()
    return service


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing chat endpoints.

    Returns:
        Mock instance with chat() and structured_extract() methods

    Example:
        >>> mock_llm_client.chat.return_value = {
        ...     "response": "Test response",
        ...     "tokens_used": 100
        ... }
    """
    client = Mock()
    client.chat = Mock(return_value={"response": "Mock response", "tokens_used": 0})
    client.structured_extract = Mock(return_value={"data": {}, "tokens_used": 0})
    return client


@pytest.fixture
def mock_task_repository():
    """Mock ITaskRepository for testing.

    Returns:
        Mock instance with task-related methods
    """
    from backend.repositories.interfaces.itask_repository import ITaskRepository

    repo = Mock(spec=ITaskRepository)
    repo.get_soap_data = Mock()
    repo.save_soap_data = Mock()
    repo.get_orders = Mock(return_value=[])
    repo.create_order = Mock()
    return repo


@pytest.fixture
def mock_export_service():
    """Mock ExportService for testing.

    Returns:
        Mock instance with export methods
    """
    service = Mock()
    service.export_session = Mock()
    service.export_soap = Mock()
    return service


@pytest.fixture
def mock_notification_service():
    """Mock NotificationService for testing.

    Returns:
        Mock instance with send methods
    """
    service = Mock()
    service.send_sms = Mock()
    service.send_email = Mock()
    return service
