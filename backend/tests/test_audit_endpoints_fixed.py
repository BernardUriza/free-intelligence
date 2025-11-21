"""Test Audit Endpoints with Existing Session Data."""

from __future__ import annotations

import pytest


def test_get_audit_endpoint_direct():
    """Test GET /api/sessions/{id}/audit endpoint directly."""
    from fastapi.testclient import TestClient
    from backend.app.main import app
    import h5py
    from backend.storage.task_repository import CORPUS_PATH

    client = TestClient(app)

    # Find a session with SOAP data
    with h5py.File(CORPUS_PATH, "r") as f:
        sessions = list(f["sessions"].keys())[:50]
        
        session_id = None
        for sid in sessions:
            tasks_path = f"/sessions/{sid}/tasks"
            if tasks_path not in f:
                continue
            tasks_group = f[tasks_path]
            if "SOAP_GENERATION" not in tasks_group:
                continue
            soap_group = tasks_group["SOAP_GENERATION"]
            if "soap_note" in soap_group or "soap_data" in soap_group:
                session_id = sid
                break
        
        if not session_id:
            pytest.skip("No sessions with SOAP data found")

    print(f"\n[Test] Testing audit endpoint with session: {session_id}")

    # GET /audit endpoint
    response = client.get(f"/api/workflows/aurity/sessions/{session_id}/audit")
    assert response.status_code == 200

    audit_data = response.json()

    # Verify structure
    assert audit_data["session_id"] == session_id
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
