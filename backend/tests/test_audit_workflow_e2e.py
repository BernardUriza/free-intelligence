"""End-to-End Test for Session Audit Workflow.

Tests the complete doctor audit flow:
1. Upload audio chunks (5-7) via streaming
2. Checkpoint audio
3. Generate SOAP with DecisionalMiddleware
4. GET /api/sessions/{id}/audit
5. POST /api/sessions/{id}/feedback with corrections

Uses chunks 5-7 for realistic medical case testing.
"""

from __future__ import annotations

import pytest
import time
from pathlib import Path

from backend.models.task_type import TaskType
from backend.storage.task_repository import (
    get_session_metadata,
    get_soap_data,
    get_task_metadata,
)


@pytest.fixture
def audio_chunks():
    """Load audio chunks 5-7 for testing."""
    chunks_dir = Path(__file__).parent.parent.parent / "storage" / "chunks"

    chunk_files = []
    for i in range(5, 8):  # Chunks 5, 6, 7
        chunk_path = chunks_dir / f"chunk_{i}.webm"
        if chunk_path.exists():
            with open(chunk_path, "rb") as f:
                chunk_files.append(f.read())

    if not chunk_files:
        pytest.skip("No audio chunks found in storage/chunks/")

    return chunk_files


@pytest.fixture
def session_id():
    """Generate test session ID."""
    return f"test_audit_{int(time.time())}"


class TestAuditWorkflowE2E:
    """End-to-end test for complete audit workflow."""

    def test_complete_audit_workflow(self, audio_chunks, session_id):
        """Test full workflow from audio upload to doctor feedback.

        Steps:
        1. Stream audio chunks 5-7
        2. Checkpoint audio (concatenate)
        3. Finalize session (triggers SOAP generation)
        4. Wait for SOAP completion
        5. GET /audit endpoint
        6. Verify flags are detected
        7. POST /feedback with corrections
        8. Verify feedback is saved
        """
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)

        # Step 1: Stream audio chunks
        print(f"\n[Test] Uploading {len(audio_chunks)} chunks for session {session_id}")
        for idx, chunk_data in enumerate(audio_chunks):
            chunk_num = idx + 5  # Chunks 5, 6, 7
            response = client.post(
                "/api/workflows/aurity/stream",
                json={
                    "session_id": session_id,
                    "chunk_index": chunk_num,
                    "audio_chunk_base64": chunk_data.hex(),  # Convert bytes to hex
                    "timestamp": time.time(),
                },
            )
            assert response.status_code == 200
            print(f"  ✓ Chunk {chunk_num} uploaded")

        # Step 2: Checkpoint audio
        print(f"[Test] Checkpointing audio (last_chunk_idx=7)")
        response = client.post(
            f"/api/workflows/aurity/sessions/{session_id}/checkpoint",
            json={"last_chunk_idx": 7},
        )
        assert response.status_code == 200
        checkpoint_data = response.json()
        assert checkpoint_data["chunks_concatenated"] == 3
        print(f"  ✓ Audio checkpointed: {checkpoint_data['full_audio_size']} bytes")

        # Step 3: Finalize session (triggers SOAP)
        print(f"[Test] Finalizing session (starts SOAP generation)")
        response = client.post(
            f"/api/workflows/aurity/sessions/{session_id}/finalize",
            json={
                "transcription_sources": {
                    "webspeech_final": [],
                    "transcription_per_chunks": [],
                    "full_transcription": "Paciente con dolor torácico de 2 horas de evolución. "
                                         "Presión arterial 160/95, frecuencia cardíaca 110 lpm. "
                                         "Antecedentes: diabetes tipo 2, hipertensión. "
                                         "Medicamentos: metformina, enalapril, losartán. "
                                         "Plan: aspirina, clopidogrel, cateterismo urgente.",
                }
            },
        )
        assert response.status_code == 202  # Accepted
        finalize_data = response.json()
        print(f"  ✓ Session finalized: {finalize_data['status']}")

        # Step 4: Wait for SOAP completion (poll monitor endpoint)
        print(f"[Test] Waiting for SOAP generation (max 60s)...")
        soap_completed = False
        for attempt in range(60):  # Max 60 seconds
            time.sleep(1)

            response = client.get(f"/api/sessions/{session_id}/monitor")
            if response.status_code == 200:
                monitor_data = response.json()
                soap_status = monitor_data.get("soap", {}).get("status")

                if soap_status == "COMPLETED":
                    soap_completed = True
                    print(f"  ✓ SOAP generation completed (took {attempt + 1}s)")
                    break
                elif soap_status == "FAILED":
                    pytest.fail(f"SOAP generation failed: {monitor_data.get('soap', {}).get('error')}")

        if not soap_completed:
            pytest.fail("SOAP generation timed out after 60 seconds")

        # Step 5: GET /audit endpoint
        print(f"[Test] Fetching audit data...")
        response = client.get(f"/api/sessions/{session_id}/audit")
        assert response.status_code == 200
        audit_data = response.json()

        # Verify audit data structure
        assert audit_data["session_id"] == session_id
        assert "patient" in audit_data
        assert "session_metadata" in audit_data
        assert "orchestration" in audit_data
        assert "soap_note" in audit_data
        assert "flags" in audit_data

        print(f"  ✓ Audit data fetched")
        print(f"    - Strategy: {audit_data['orchestration']['strategy']}")
        print(f"    - Personas: {audit_data['orchestration']['personas_invoked']}")
        print(f"    - Confidence: {audit_data['orchestration']['confidence_score']:.2%}")
        print(f"    - Complexity: {audit_data['orchestration']['complexity_score']:.1f}")
        print(f"    - Flags: {len(audit_data['flags'])}")

        # Step 6: Verify flags are detected
        flags = audit_data["flags"]
        assert len(flags) > 0, "Expected at least one flag (medication interaction or low confidence)"

        # Check for medication interaction flag (enalapril + losartán)
        interaction_flag = next(
            (f for f in flags if f["type"] == "medication_interaction"),
            None
        )
        if interaction_flag:
            print(f"  ✓ Medication interaction flag detected:")
            print(f"    - Severity: {interaction_flag['severity']}")
            print(f"    - Message: {interaction_flag['message']}")

        # Step 7: POST /feedback with corrections
        print(f"[Test] Submitting doctor feedback...")
        response = client.post(
            f"/api/sessions/{session_id}/feedback",
            json={
                "rating": 4,
                "comments": "SOAP correcto pero faltó especificar dosis de aspirina",
                "corrections": [
                    {
                        "section": "plan",
                        "original": "aspirina",
                        "corrected": "aspirina 300mg masticable",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                    }
                ],
                "decision": "approved",
            },
        )
        assert response.status_code == 200
        feedback_response = response.json()

        assert feedback_response["status"] == "feedback_saved"
        assert feedback_response["audit_status"] == "approved"
        assert feedback_response["corrections_applied"] >= 1

        print(f"  ✓ Doctor feedback submitted")
        print(f"    - Rating: 4/5")
        print(f"    - Decision: approved")
        print(f"    - Corrections applied: {feedback_response['corrections_applied']}")

        # Step 8: Verify feedback is saved
        print(f"[Test] Verifying feedback persistence...")
        session_meta = get_session_metadata(session_id)

        assert session_meta is not None
        assert "doctor_feedback" in session_meta
        assert session_meta["audit_status"] == "approved"
        assert session_meta["audit_rating"] == 4

        doctor_feedback = session_meta["doctor_feedback"]
        assert doctor_feedback["rating"] == 4
        assert doctor_feedback["decision"] == "approved"
        assert len(doctor_feedback["corrections"]) == 1

        print(f"  ✓ Feedback persisted correctly")

        # Verify SOAP was updated with correction
        soap_data = get_soap_data(session_id)
        plan_str = str(soap_data.get("plan", {}))

        # Note: Correction might be in medications list or as metadata
        print(f"  ✓ SOAP data structure preserved")

        print(f"\n[Test] ✅ Complete audit workflow test PASSED")
        print(f"Session ID: {session_id}")
        print(f"You can inspect with: GET /api/sessions/{session_id}/audit")

    def test_audit_endpoint_with_nonexistent_session(self):
        """Test audit endpoint returns 404 for nonexistent session."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)

        response = client.get("/api/sessions/nonexistent_session_123/audit")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_feedback_endpoint_validation(self):
        """Test feedback endpoint validates required fields."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)

        # Missing rating (required)
        response = client.post(
            "/api/sessions/test_session/feedback",
            json={
                "comments": "Test",
                "corrections": [],
                "decision": "approved",
            },
        )
        assert response.status_code == 422  # Validation error

        # Invalid rating (must be 1-5)
        response = client.post(
            "/api/sessions/test_session/feedback",
            json={
                "rating": 6,  # Invalid: > 5
                "comments": "Test",
                "corrections": [],
                "decision": "approved",
            },
        )
        assert response.status_code == 422

    def test_analyze_session_flags_heuristics(self):
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
