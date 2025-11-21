"""Test Audit Endpoints with Existing Session Data.

Tests the audit and feedback endpoints using existing sessions from HDF5.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def existing_session_id():
    """Get a session ID that has SOAP data."""
    import h5py
    from backend.storage.task_repository import CORPUS_PATH

    with h5py.File(CORPUS_PATH, "r") as f:
        sessions = list(f["sessions"].keys())

        # Find a session with SOAP data
        # Find session with complete SOAP data
    for session_id in sessions:
        tasks_path = f"/sessions/{session_id}/tasks"
        if tasks_path not in f:
            continue
        tasks_group = f[tasks_path]
        if "SOAP_GENERATION" not in tasks_group:
            continue
        soap_group = tasks_group["SOAP_GENERATION"]
        if "soap_note" in soap_group or "soap_data" in soap_group:
            return session_id

    # Fallback: use hardcoded test session if it exists
    if "session_complete_test" in f["sessions"]:
        return "session_complete_test"

    for session_id in ["session_complete_test"]:
            session_path = f"/sessions/{session_id}/tasks/SOAP_GENERATION"
            if session_path in f:
                return session_id

    pytest.skip("No sessions with SOAP data found")


class TestAuditEndpoints:
    """Test audit and feedback endpoints."""

    def test_get_audit_endpoint(self, existing_session_id):
        """Test GET /api/workflows/aurity/sessions/{id}/audit endpoint."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)

        print(f"\n[Test] Testing audit endpoint with session: {existing_session_id}")

        # GET /audit endpoint
        response = client.get(f"/api/workflows/aurity/sessions/{existing_session_id}/audit")
        assert response.status_code == 200

        audit_data = response.json()

        # Verify structure
        assert audit_data["session_id"] == existing_session_id
        assert "patient" in audit_data
        assert "session_metadata" in audit_data
        assert "orchestration" in audit_data
        assert "soap_note" in audit_data
        assert "flags" in audit_data

        print(f"  ✓ Audit data fetched successfully")
        print(f"    - Orchestration strategy: {audit_data['orchestration'].get('strategy', 'N/A')}")
        print(f"    - Confidence: {audit_data['orchestration'].get('confidence_score', 0):.2%}")
        print(f"    - Flags detected: {len(audit_data['flags'])}")

        # Verify SOAP structure
        soap = audit_data["soap_note"]
        assert isinstance(soap, dict)
        print(f"    - SOAP sections: {list(soap.keys())}")

    def test_submit_feedback_endpoint(self, existing_session_id):
        """Test POST /api/workflows/aurity/sessions/{id}/feedback endpoint."""
        from fastapi.testclient import TestClient
        from backend.app.main import app
        import time

        client = TestClient(app)

        print(f"\n[Test] Testing feedback endpoint with session: {existing_session_id}")

        # Submit feedback
        feedback_payload = {
            "rating": 4,
            "comments": "SOAP note looks good but could use more detail in plan section",
            "corrections": [
                {
                    "section": "plan",
                    "original": "seguimiento",
                    "corrected": "seguimiento en 2 semanas con laboratorios",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                }
            ],
            "decision": "approved",
        }

        response = client.post(
            f"/api/workflows/aurity/sessions/{existing_session_id}/feedback",
            json=feedback_payload,
        )
        assert response.status_code == 200

        feedback_response = response.json()

        assert feedback_response["status"] == "feedback_saved"
        assert feedback_response["audit_status"] == "approved"
        assert feedback_response["corrections_applied"] >= 0

        print(f"  ✓ Feedback submitted successfully")
        print(f"    - Rating: {feedback_payload['rating']}/5")
        print(f"    - Decision: {feedback_payload['decision']}")
        print(f"    - Corrections applied: {feedback_response['corrections_applied']}")

        # Verify feedback was saved (GET audit again)
        response = client.get(f"/api/workflows/aurity/sessions/{existing_session_id}/audit")
        assert response.status_code == 200

        audit_data = response.json()
        assert "doctor_feedback" in audit_data
        assert audit_data["doctor_feedback"] is not None
        assert audit_data["doctor_feedback"]["rating"] == 4
        assert audit_data["session_metadata"]["status"] == "approved"

        print(f"  ✓ Feedback persisted correctly")

    def test_audit_endpoint_404(self):
        """Test audit endpoint returns 404 for nonexistent session."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)

        response = client.get("/api/workflows/aurity/sessions/nonexistent_session_123/audit")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_feedback_validation(self):
        """Test feedback endpoint validates required fields."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)

        # Missing rating (required)
        response = client.post(
            "/api/workflows/aurity/sessions/test_session/feedback",
            json={
                "comments": "Test",
                "corrections": [],
                "decision": "approved",
            },
        )
        assert response.status_code == 422  # Validation error

        # Invalid rating (must be 1-5)
        response = client.post(
            "/api/workflows/aurity/sessions/test_session/feedback",
            json={
                "rating": 6,  # Invalid: > 5
                "comments": "Test",
                "corrections": [],
                "decision": "approved",
            },
        )
        assert response.status_code == 422

    def test_analyze_session_flags(self):
        """Test flag detection heuristics."""
        from backend.api.public.workflows.sessions import _analyze_session_flags

        # Test low confidence flag
        flags = _analyze_session_flags(
            soap_data={"subjective": "Test", "objective": "Test"},
            orchestration={"confidence_score": 0.85, "complexity_score": 30}
        )
        assert any(f["type"] == "low_confidence" for f in flags)

        # Test medication interaction flag
        flags = _analyze_session_flags(
            soap_data={
                "subjective": "Test",
                "objective": "Test",
                "plan": {
                    "medications": [
                        {"name": "Enalapril 10mg"},
                        {"name": "Losartán 50mg"},
                    ]
                }
            },
            orchestration={"confidence_score": 0.95, "complexity_score": 40}
        )
        assert any(f["type"] == "medication_interaction" for f in flags)
        assert any(f["severity"] == "critical" for f in flags)

        # Test missing objective data flag
        flags = _analyze_session_flags(
            soap_data={
                "subjective": "Test",
                "objective": "",  # Empty
            },
            orchestration={"confidence_score": 0.95, "complexity_score": 40}
        )
        assert any(f["type"] == "missing_objective_data" for f in flags)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
