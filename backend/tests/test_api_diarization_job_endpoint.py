"""API integration tests for /internal/diarization/jobs/{job_id} endpoint.

Tests the full stack: FastAPI endpoint → DI container → DiarizationJobService → HDF5.
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import pytest
from fastapi.testclient import TestClient


def _write_job(h5_path: str, job_id: str, payload: dict) -> None:
    """Helper to write job to HDF5."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    with h5py.File(h5_path, "a") as f:
        path = f"/jobs/{job_id}"
        if path in f:
            del f[path]
        f.create_dataset(path, data=data)


@pytest.fixture
def test_h5_path(tmp_path: Path) -> str:
    """Create temporary HDF5 file for testing."""
    h5 = tmp_path / "diarization_test.h5"
    with h5py.File(h5, "w") as f:
        f.create_group("jobs")
    return h5.as_posix()


@pytest.fixture
def client(test_h5_path: str, monkeypatch) -> TestClient:
    """Create FastAPI test client with test HDF5."""
    # Set environment variable to use test HDF5
    monkeypatch.setenv("AURITY_DIARIZATION_HDF5", test_h5_path)
    monkeypatch.setenv("AURITY_DIARIZATION_PERSIST_RESOLVED_STATUS", "false")

    # Force container reset to pick up new env vars
    from packages.fi_common.infrastructure.container import reset_container

    reset_container()

    # Import app after setting env vars
    from backend.app.main import create_app

    app = create_app()
    return TestClient(app)


def test_endpoint_returns_200_completed_with_errors(client: TestClient, test_h5_path: str) -> None:
    """Test that endpoint returns 200 with completed_with_errors for SOAP failure."""
    job_id = "job-completed-soap-fail"

    payload = {
        "job_id": job_id,
        "session_id": "session-1",
        "status": "completed",
        "progress_percent": 100,
        "created_at": "2025-11-09T22:20:49.567807Z",
        "completed_at": "2025-11-09T22:21:11.411440Z",
        "result_data": {
            "transcription": {"text": "Sample transcription"},
            "diarization": {"segments": []},
            "soap_status": "failed",
            "soap_error": "SOAP generation timeout (60s) - Ollama may be overloaded",
        },
    }
    _write_job(test_h5_path, job_id, payload)

    response = client.get(f"/internal/diarization/jobs/{job_id}")

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["job_id"] == job_id
    assert body["status"] == "completed_with_errors"
    assert body["progress_pct"] == 100
    # Errors field may not be in JobStatusResponse model, so we check the resolved status


def test_endpoint_returns_404_for_missing_job(client: TestClient) -> None:
    """Test that endpoint returns 404 for missing job."""
    response = client.get("/internal/diarization/jobs/nonexistent-job-id")

    assert response.status_code == 404
    body = response.json()
    assert "not found" in body["detail"].lower()


def test_endpoint_returns_200_for_completed_job(client: TestClient, test_h5_path: str) -> None:
    """Test that endpoint returns 200 for successfully completed job."""
    job_id = "job-completed-ok"

    payload = {
        "job_id": job_id,
        "session_id": "session-2",
        "status": "completed",
        "progress_percent": 100,
        "created_at": "2025-11-09T22:20:49.567807Z",
        "completed_at": "2025-11-09T22:21:11.411440Z",
        "result_data": {
            "transcription": {"text": "Sample transcription"},
            "diarization": {"segments": []},
            "soap_status": "ok",
        },
    }
    _write_job(test_h5_path, job_id, payload)

    response = client.get(f"/internal/diarization/jobs/{job_id}")

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["job_id"] == job_id
    assert body["status"] == "completed"
    assert body["progress_pct"] == 100


def test_endpoint_returns_200_for_in_progress_job(client: TestClient, test_h5_path: str) -> None:
    """Test that endpoint returns 200 for in-progress job."""
    job_id = "job-in-progress"

    payload = {
        "job_id": job_id,
        "session_id": "session-3",
        "status": "in_progress",
        "progress_percent": 50,
        "created_at": "2025-11-09T22:20:49.567807Z",
        "completed_at": None,
        "result_data": {},
    }
    _write_job(test_h5_path, job_id, payload)

    response = client.get(f"/internal/diarization/jobs/{job_id}")

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["job_id"] == job_id
    assert body["status"] == "in_progress"
    assert body["progress_pct"] == 50


def test_endpoint_with_real_job_structure(client: TestClient, test_h5_path: str) -> None:
    """Test with actual job structure from production (dca6c6d2-be0b-4f2b-8704-c520d2a85958)."""
    job_id = "dca6c6d2-be0b-4f2b-8704-c520d2a85958"

    # Real production job data
    payload = {
        "job_id": job_id,
        "session_id": "abe95bf2-9360-4784-aa54-82a4a35595e2",
        "audio_file_path": "/var/folders/hm/19q56cfn6g3bqq9dnh0m9xbr0000gn/T/fi_audio/abe95bf2-9360-4784-aa54-82a4a35595e2_test.mp3",
        "audio_file_size": 552000,
        "status": "completed",
        "progress_percent": 100,
        "created_at": "2025-11-09T22:20:49.567807Z",
        "started_at": "2025-11-09T22:20:49.591036Z",
        "completed_at": "2025-11-09T22:21:11.411440Z",
        "error_message": None,
        "result_path": None,
        "processed_chunks": 0,
        "total_chunks": 0,
        "last_event": "JOB_CREATED",
        "updated_at": "2025-11-10T00:56:09.024570Z",
        "result_data": {
            "transcription": {
                "text": "Paciente femenina de 34 años...",
                "segments": [
                    {"start": 0.0, "end": 6.16, "text": "Paciente femenina de 34 años..."}
                ],
                "language": "es",
                "duration": 27.6,
                "available": True,
            },
            "diarization": {
                "segments": [
                    {
                        "start_time": 0.0,
                        "end_time": 27.2,
                        "speaker": "DESCONOCIDO",
                        "text": "Paciente femenina de 34 años...",
                        "improved_text": "Paciente femenina de 34 años...",
                    }
                ],
                "duration_sec": 27.6,
                "language": "es",
                "processing_time_sec": 0.0019450187683105469,
            },
            "soap_status": "failed",
            "soap_error": "SOAP generation timeout (60s) - Ollama may be overloaded",
        },
    }
    _write_job(test_h5_path, job_id, payload)

    response = client.get(f"/internal/diarization/jobs/{job_id}")

    assert response.status_code == 200, response.text
    body = response.json()

    # Verify status resolution
    assert body["job_id"] == job_id
    assert body["session_id"] == "abe95bf2-9360-4784-aa54-82a4a35595e2"
    assert body["status"] == "completed_with_errors"
    assert body["progress_pct"] == 100
    assert body["created_at"] == "2025-11-09T22:20:49.567807Z"
