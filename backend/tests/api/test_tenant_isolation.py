"""
Tenant Isolation Security Tests

CRITICAL: These tests validate that multi-tenant isolation works correctly.
Failure of ANY test indicates a SECURITY VULNERABILITY.

Tests validate:
1. Users can ONLY list their own sessions
2. Users can ONLY read their own sessions (403 on others)
3. Users can ONLY update their own sessions (403 on others)
4. Users can ONLY create sessions for themselves

Author: Bernard Uriza Orozco
Created: 2026-01-27
Context: Security hardening before pilot launch
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from pydantic import BaseModel, Field

# Import router functions directly (avoid circular import)
import sys
import importlib.util

# Load router module without triggering full app bootstrap
spec = importlib.util.spec_from_file_location(
    "sessions_router",
    "backend/api/routers/session/internal/sessions/router.py"
)
sessions_router = importlib.util.module_from_spec(spec)
sys.modules["sessions_router"] = sessions_router
spec.loader.exec_module(sessions_router)

list_sessions = sessions_router.list_sessions
get_session = sessions_router.get_session
update_session = sessions_router.update_session
create_session = sessions_router.create_session
CreateSessionRequest = sessions_router.CreateSessionRequest
UpdateSessionRequest = sessions_router.UpdateSessionRequest

# Import auth domain (safe, no circular deps)
from backend.infrastructure.auth.domain import User, UserRole


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def doctor_a():
    """Doctor A (tenant A)"""
    return User(
        id="auth0|doctor_a",
        email="doctor.a@clinic-a.com",
        roles=[UserRole.CLINICIAN],
        tenant_id="clinic_a",
        name="Dr. Alice",
    )


@pytest.fixture
def doctor_b():
    """Doctor B (tenant B)"""
    return User(
        id="auth0|doctor_b",
        email="doctor.b@clinic-b.com",
        roles=[UserRole.CLINICIAN],
        tenant_id="clinic_b",
        name="Dr. Bob",
    )


@pytest.fixture
def mock_container():
    """Mock DI container"""
    container = MagicMock()

    # Mock SessionService
    session_service = MagicMock()
    container.get_session_service.return_value = session_service

    # Mock AuditService
    audit_service = MagicMock()
    container.get_audit_service.return_value = audit_service

    return container


# ============================================================================
# TEST: LIST SESSIONS (Tenant Isolation)
# ============================================================================


@pytest.mark.asyncio
async def test_list_sessions_only_returns_own_sessions(doctor_a, mock_container):
    """Users should ONLY see their own sessions"""

    # Setup: Doctor A has 2 sessions
    sessions = [
        {"id": "session_1", "owner_hash": "auth0|doctor_a"},
        {"id": "session_2", "owner_hash": "auth0|doctor_a"},
    ]

    mock_container.get_session_service().list_sessions.return_value = sessions

    with patch("backend.core.domain.session.api.internal.sessions.router.get_container", return_value=mock_container):
        response = await list_sessions(
            limit=50,
            offset=0,
            current_user=doctor_a,
        )

    # Verify: Service was called with doctor_a's ID (tenant filtering)
    mock_container.get_session_service().list_sessions.assert_called_once_with(
        user_id="auth0|doctor_a"
    )

    # Verify: Response contains doctor_a's sessions
    assert len(response.items) == 2
    assert all(s.owner_hash == "auth0|doctor_a" for s in response.items)


@pytest.mark.asyncio
async def test_list_sessions_without_user_id_raises_error(mock_container):
    """Calling list_sessions() without user_id should raise ValueError"""

    from backend.domain.session.services.session_service import SessionService

    service = SessionService()

    # Should raise ValueError (tenant isolation violation)
    with pytest.raises(ValueError) as exc_info:
        service.list_sessions(user_id=None)

    assert "REQUIRED for tenant isolation" in str(exc_info.value)
    assert "HIPAA/GDPR" in str(exc_info.value)


# ============================================================================
# TEST: GET SESSION (Ownership Validation)
# ============================================================================


@pytest.mark.asyncio
async def test_get_session_owner_can_read(doctor_a, mock_container):
    """Session owner should be able to read their own session"""

    session = {
        "session_id": "session_1",
        "owner_hash": "auth0|doctor_a",
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
    }

    mock_container.get_session_service().get_session_info = AsyncMock(return_value=session)

    with patch("backend.core.domain.session.api.internal.sessions.router.get_container", return_value=mock_container):
        response = await get_session(
            session_id="session_1",
            current_user=doctor_a,
        )

    # Should succeed
    assert response.id == "session_1"
    assert response.owner_hash == "auth0|doctor_a"


@pytest.mark.asyncio
async def test_get_session_non_owner_gets_403(doctor_a, doctor_b, mock_container):
    """Non-owner trying to read session should get 403 Forbidden"""

    # Doctor A's session
    session = {
        "session_id": "session_1",
        "owner_hash": "auth0|doctor_a",
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
    }

    mock_container.get_session_service().get_session_info = AsyncMock(return_value=session)

    with patch("backend.core.domain.session.api.internal.sessions.router.get_container", return_value=mock_container):
        # Doctor B tries to read Doctor A's session
        with pytest.raises(HTTPException) as exc_info:
            await get_session(
                session_id="session_1",
                current_user=doctor_b,
            )

    # Should be 403 Forbidden (not 404)
    assert exc_info.value.status_code == 403
    assert "Access denied" in exc_info.value.detail
    assert "do not own" in exc_info.value.detail


# ============================================================================
# TEST: UPDATE SESSION (Ownership Validation)
# ============================================================================


@pytest.mark.asyncio
async def test_update_session_owner_can_update(doctor_a, mock_container):
    """Session owner should be able to update their own session"""

    session = {
        "session_id": "session_1",
        "owner_hash": "auth0|doctor_a",
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
    }

    mock_container.get_session_service().get_session_info = AsyncMock(return_value=session)
    mock_container.get_session_service().update_session.return_value = True

    request = UpdateSessionRequest(status="completed")

    with patch("backend.core.domain.session.api.internal.sessions.router.get_container", return_value=mock_container):
        response = await update_session(
            session_id="session_1",
            request=request,
            current_user=doctor_a,
        )

    # Should succeed
    assert response.id == "session_1"


@pytest.mark.asyncio
async def test_update_session_non_owner_gets_403(doctor_a, doctor_b, mock_container):
    """Non-owner trying to update session should get 403 Forbidden"""

    # Doctor A's session
    session = {
        "session_id": "session_1",
        "owner_hash": "auth0|doctor_a",
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
    }

    mock_container.get_session_service().get_session_info = AsyncMock(return_value=session)

    request = UpdateSessionRequest(status="completed")

    with patch("backend.core.domain.session.api.internal.sessions.router.get_container", return_value=mock_container):
        # Doctor B tries to update Doctor A's session
        with pytest.raises(HTTPException) as exc_info:
            await update_session(
                session_id="session_1",
                request=request,
                current_user=doctor_b,
            )

    # Should be 403 Forbidden
    assert exc_info.value.status_code == 403
    assert "Access denied" in exc_info.value.detail


# ============================================================================
# TEST: CREATE SESSION (Auto-set Owner)
# ============================================================================


@pytest.mark.asyncio
async def test_create_session_owner_auto_set(doctor_a, mock_container):
    """Session owner should be automatically set from current_user"""

    mock_container.get_session_service().create_session.return_value = {
        "session_id": "session_new",
        "status": "new",
    }

    request = CreateSessionRequest(status="new")

    with patch("backend.core.domain.session.api.internal.sessions.router.get_container", return_value=mock_container):
        response = await create_session(
            request=request,
            current_user=doctor_a,
        )

    # Verify: owner_hash is set to current_user.id
    assert response.owner_hash == "auth0|doctor_a"

    # Verify: Service was called with current_user.id (not client input)
    mock_container.get_session_service().create_session.assert_called_once()
    call_kwargs = mock_container.get_session_service().create_session.call_args[1]
    assert call_kwargs["user_id"] == "auth0|doctor_a"


# ============================================================================
# TEST: Security Audit Logs
# ============================================================================


@pytest.mark.asyncio
async def test_unauthorized_access_logged_to_audit(doctor_a, doctor_b, mock_container):
    """Unauthorized access attempts should be logged for security auditing"""

    session = {
        "session_id": "session_1",
        "owner_hash": "auth0|doctor_a",
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
    }

    mock_container.get_session_service().get_session_info = AsyncMock(return_value=session)

    with patch("backend.core.domain.session.api.internal.sessions.router.get_container", return_value=mock_container):
        # Doctor B tries to read Doctor A's session
        with pytest.raises(HTTPException):
            await get_session(
                session_id="session_1",
                current_user=doctor_b,
            )

    # Verify: Security incident was logged to audit service
    mock_container.get_audit_service().log_action.assert_called_once()
    audit_call = mock_container.get_audit_service().log_action.call_args[1]

    assert audit_call["action"] == "session_access_denied"
    assert audit_call["user_id"] == "auth0|doctor_b"
    assert audit_call["result"] == "denied"
    assert audit_call["details"]["reason"] == "ownership_mismatch"


# ============================================================================
# REGRESSION TESTS (Prevent Future Breaks)
# ============================================================================


def test_create_session_request_no_owner_hash_field():
    """CreateSessionRequest should NOT have owner_hash field (security)"""

    # Verify: owner_hash is NOT in the request schema
    request = CreateSessionRequest(status="new")

    assert not hasattr(request, "owner_hash")

    # Should only have status and thread_id
    assert hasattr(request, "status")
    assert hasattr(request, "thread_id")


@pytest.mark.asyncio
async def test_list_sessions_requires_auth():
    """list_sessions endpoint MUST require authentication"""

    # This test verifies that the endpoint signature includes Depends(get_current_user)
    # If someone removes the auth dependency, this test will fail

    import inspect
    sig = inspect.signature(list_sessions)

    # Verify: current_user parameter exists
    assert "current_user" in sig.parameters

    # Verify: current_user has a default (Depends)
    param = sig.parameters["current_user"]
    assert param.default is not inspect.Parameter.empty
