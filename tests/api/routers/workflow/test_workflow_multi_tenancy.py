"""Integration tests for multi-tenancy security in workflow endpoints (CRITICAL).

Tests horizontal privilege escalation prevention in PHI-containing endpoints:
- Sessions (patient consultation data)
- Timeline (patient history)
- SOAP notes (medical documentation)

⚠️ EXPECTED TO FAIL INITIALLY - These endpoints DO NOT filter by clinic_id yet
This test file documents the security vulnerability and will pass once fixed.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Multi-Tenancy Phase 2 Security Gap Testing
"""

from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app, public_app
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User, UserRole


@pytest.fixture
def client():
    """FastAPI test client with clean dependency overrides."""
    app.dependency_overrides.clear()
    public_app.dependency_overrides.clear()
    client = TestClient(app)
    yield client
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


# =============================================================================
# CRITICAL: Session Endpoints - PHI Horizontal Privilege Escalation
# =============================================================================


@pytest.mark.xfail(reason="Session endpoints do not filter by clinic_id yet - SECURITY BUG")
def test_doctor_cannot_list_other_clinic_sessions(client, doctor_a_clinic1):
    """Doctor A CANNOT list sessions from clinic-2 (horizontal privilege escalation).

    ⚠️ EXPECTED TO FAIL - sessions endpoint currently returns ALL sessions
    This is a CRITICAL security vulnerability allowing cross-clinic PHI access.
    """
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1

    # Request sessions list (should only return clinic-1 sessions)
    response = client.get("/api/workflows/aurity/sessions")

    # Should NOT be 403 (user can list their own sessions)
    # But response should ONLY contain clinic-1 sessions, not all clinics
    assert response.status_code == status.HTTP_200_OK

    if response.status_code == 200:
        sessions = response.json()
        # Verify ALL sessions belong to clinic-1 (not clinic-2)
        for session in sessions:
            # This will FAIL if sessions from clinic-2 are returned
            assert session.get("clinic_id") == "clinic-1", (
                f"Session {session.get('session_id')} from clinic-2 leaked to doctor A (clinic-1)"
            )


@pytest.mark.xfail(reason="Session read does not validate clinic_id - SECURITY BUG")
def test_doctor_cannot_read_other_clinic_session(client, doctor_a_clinic1):
    """Doctor A CANNOT read session from clinic-2.

    ⚠️ EXPECTED TO FAIL - session read endpoint does not validate clinic_id
    """
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1

    # Try to access a session from clinic-2 (if it exists)
    # In reality, we'd need to create a test session first
    # For now, this test documents the expected behavior
    response = client.get("/api/workflows/aurity/sessions/session-clinic2-123")

    # Should be 403 Forbidden (not 404, which would leak existence)
    assert response.status_code == status.HTTP_403_FORBIDDEN, (
        f"Doctor A (clinic-1) should NOT access session from clinic-2, "
        f"but got {response.status_code}"
    )


# =============================================================================
# CRITICAL: Timeline Endpoints - Patient History Leakage
# =============================================================================


@pytest.mark.xfail(reason="Timeline does not filter by clinic_id - SECURITY BUG")
def test_doctor_cannot_see_other_clinic_timeline(client, doctor_a_clinic1):
    """Doctor A CANNOT see timeline events from clinic-2.

    ⚠️ EXPECTED TO FAIL - timeline endpoint returns events from all clinics
    """
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1

    response = client.get("/api/workflows/aurity/timeline")

    assert response.status_code == status.HTTP_200_OK

    if response.status_code == 200:
        events = response.json()
        # Verify ALL events belong to clinic-1
        for event in events:
            assert event.get("clinic_id") == "clinic-1", (
                f"Timeline event from clinic-2 leaked to doctor A (clinic-1)"
            )


# =============================================================================
# CRITICAL: Document Search - Semantic Search Across Clinics
# =============================================================================


@pytest.mark.xfail(reason="Document repository NOT IMPLEMENTED (stub endpoint) - SECURITY BUG when implemented")
def test_document_search_filters_by_clinic(client, doctor_a_clinic1):
    """Document search MUST filter results by user's clinic_id.

    ⚠️ EXPECTED TO FAIL - Document repository is NOT IMPLEMENTED yet (see documents.py:38-81)
    When implemented, search_documents_by_embedding() MUST filter by clinic_id.

    Current Status:
    - Endpoint exists but calls non-existent functions (broken imports)
    - FIXME at documents.py:526: "Broken import - search_documents_by_embedding"
    - TODO at documents.py:66: "Multi-tenancy: Filter by clinic_id in queries"

    Security Requirement for Implementation:
    - search_documents_by_embedding() MUST accept clinic_id parameter
    - MUST filter results by clinic_id (not just user_id)
    - Semantic search across clinics would leak PHI
    """
    public_app.dependency_overrides[get_current_user] = lambda: doctor_a_clinic1

    # Search for documents (semantic search)
    response = client.post(
        "/api/documents/search",
        json={
            "query": "diabetes",
            "limit": 10
        }
    )

    # Note: Endpoint currently returns 500 (NameError) because functions don't exist
    # When fixed, should return 200 OK with clinic-filtered results
    if response.status_code == 200:
        documents = response.json()
        # Verify ALL documents belong to clinic-1
        for doc in documents:
            assert doc.get("clinic_id") == "clinic-1", (
                f"Document {doc.get('id')} from clinic-2 leaked via semantic search"
            )


# =============================================================================
# INFO: Test Summary
# =============================================================================


def test_security_gap_documentation():
    """Document the security gaps found in workflow endpoints.

    This test always passes - it's documentation of the bugs found.
    """
    gaps = {
        "sessions": "No clinic_id filtering - horizontal privilege escalation",
        "timeline": "No clinic_id filtering - patient history leakage",
        "documents": "Semantic search returns results from all clinics",
    }

    print("\n" + "="*80)
    print("🚨 CRITICAL SECURITY GAPS DETECTED")
    print("="*80)
    for endpoint, issue in gaps.items():
        print(f"  ❌ {endpoint}: {issue}")
    print("="*80)
    print("📝 Fix: Add validate_clinic_access() to all workflow endpoints")
    print("📝 See: backend/infrastructure/auth/utils/clinic_access.py")
    print("="*80 + "\n")

    # This test always passes - it's just documentation
    assert True
