"""
Integration test: Diarization upload → status retrieval (FI-BACKEND-FEAT-004)

Tests the complete flow:
1. Upload audio file via POST /api/diarization/upload
2. Immediately retrieve job status via GET /api/diarization/jobs/{job_id}
3. Verify no 404 error (regression test for issue)

Card: FI-BACKEND-FEAT-004 + FI-RELIABILITY-IMPL-004
"""

import io
import os
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Set up environment for low-priority worker + V2 pipeline
os.environ["DIARIZATION_LOWPRIO"] = "true"
os.environ["DIARIZATION_USE_V2"] = "true"


@pytest.fixture
def test_audio_file():
    """Create a minimal valid MP3 file for testing."""
    # Minimal MP3 header (ID3v2.4)
    mp3_content = (
        b"ID3\x04\x00\x00\x00\x00\x00\x00"  # ID3 header
        + b"TSSE\x00\x00\x00\x0f\x00\x00\x00\x00test\x00"  # Frame
        + b"\xff\xfb\x10\x00" + b"\x00" * 1024  # MPEG frame
    )
    return io.BytesIO(mp3_content)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from backend.fi_consult_service import app
    return TestClient(app)


def test_diarization_upload_and_status(client, test_audio_file):
    """
    Test: Upload audio and immediately retrieve job status.

    This is a regression test for the 404 error in the UI:
    "Failed to get job status: 404"

    The fix ensures that jobs are initialized in HDF5 immediately
    when created, not after they start processing.
    """
    session_id = str(uuid.uuid4())

    # Step 1: Upload audio file
    test_audio_file.seek(0)  # Reset file pointer

    upload_response = client.post(
        "/api/diarization/upload",
        files={"audio": ("test.mp3", test_audio_file, "audio/mp3")},
        headers={"X-Session-ID": session_id},
        params={"language": "es", "persist": "false"}
    )

    # Verify upload succeeded
    assert upload_response.status_code == 202, f"Upload failed: {upload_response.text}"
    upload_data = upload_response.json()
    job_id = upload_data["job_id"]

    assert job_id, "No job_id returned"
    assert upload_data["status"] == "pending"
    assert upload_data["session_id"] == session_id

    print(f"✓ Upload succeeded: job_id={job_id}")

    # Step 2: Immediately retrieve job status (this would return 404 before fix)
    status_response = client.get(f"/api/diarization/jobs/{job_id}")

    # Verify status retrieval succeeded (no 404)
    assert status_response.status_code == 200, f"Status retrieval failed: {status_response.text}"
    status_data = status_response.json()

    # Verify response structure
    assert status_data["job_id"] == job_id
    assert status_data["session_id"] == session_id
    assert status_data["status"] == "pending"
    assert status_data["progress_pct"] == 0
    assert status_data["chunks"] == []
    assert "created_at" in status_data
    assert "updated_at" in status_data

    print(f"✓ Status retrieval succeeded: status={status_data['status']}")
    print("✅ No 404 error - job is immediately queryable!")


def test_diarization_list_jobs(client, test_audio_file):
    """
    Test: List jobs returns newly created job.
    """
    session_id = str(uuid.uuid4())

    # Upload audio
    test_audio_file.seek(0)
    upload_response = client.post(
        "/api/diarization/upload",
        files={"audio": ("test.mp3", test_audio_file, "audio/mp3")},
        headers={"X-Session-ID": session_id}
    )

    assert upload_response.status_code == 202
    job_id = upload_response.json()["job_id"]

    # List all jobs
    list_response = client.get("/api/diarization/jobs")
    assert list_response.status_code == 200

    jobs = list_response.json()["jobs"]
    job_ids = [j["job_id"] for j in jobs]

    # New job should be in the list
    assert job_id in job_ids, f"Job {job_id} not found in list: {job_ids}"
    print(f"✓ Job {job_id} appears in list_jobs")


def test_diarization_list_jobs_filtered(client, test_audio_file):
    """
    Test: Filter jobs by session_id.
    """
    session_id = str(uuid.uuid4())

    # Upload multiple files to same session (if possible)
    test_audio_file.seek(0)
    upload_response = client.post(
        "/api/diarization/upload",
        files={"audio": ("test.mp3", test_audio_file, "audio/mp3")},
        headers={"X-Session-ID": session_id}
    )

    assert upload_response.status_code == 202
    job_id = upload_response.json()["job_id"]

    # Filter jobs by session_id
    list_response = client.get(
        "/api/diarization/jobs",
        params={"session_id": session_id}
    )

    assert list_response.status_code == 200
    jobs = list_response.json()["jobs"]

    # Should find our job
    matching_jobs = [j for j in jobs if j["job_id"] == job_id]
    assert len(matching_jobs) == 1, f"Job {job_id} not found in filtered results"

    # All jobs in list should match the session_id
    for job in jobs:
        assert job["session_id"] == session_id

    print(f"✓ Filter by session_id works: found {len(jobs)} job(s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
