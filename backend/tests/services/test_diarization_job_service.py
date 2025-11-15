"""Unit tests for DiarizationJobService.

Tests scalar Dataset and Group HDF5 structures, status resolution,
and error handling.
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py
import pytest

from backend.services.diarization.job_controller import DiarizationJobService


def _write_scalar_job(h5_path: str, job_id: str, payload: dict) -> None:
    """Helper to write scalar Dataset job."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    with h5py.File(h5_path, "a") as f:
        path = f"/jobs/{job_id}"
        if path in f:
            del f[path]
        f.create_dataset(path, data=data)


def test_scalar_dataset_completed_with_soap_failed(tmp_path: Path) -> None:
    """Test that completed job with soap_status=failed resolves to completed_with_errors."""
    h5 = tmp_path / "diarization.h5"
    job_id = "dca6c6d2-be0b-4f2b-8704-c520d2a85958"

    payload = {
        "job_id": job_id,
        "session_id": "abe95bf2-9360-4784-aa54-82a4a35595e2",
        "status": "completed",
        "progress_percent": 100,
        "created_at": "2025-11-09T22:20:49.567807Z",
        "completed_at": "2025-11-09T22:21:11.411440Z",
        "result_data": {
            "transcription": {},
            "diarization": {},
            "soap_status": "failed",
            "soap_error": "SOAP generation timeout (60s) - Ollama may be overloaded",
        },
    }
    _write_scalar_job(h5.as_posix(), job_id, payload)

    svc = DiarizationJobService(hdf5_path=h5.as_posix(), persist_resolved=False)
    out = svc.get_job_status(job_id)

    assert out["status"] == "completed_with_errors"
    assert out["resolved_status"] == "completed_with_errors"
    assert out["progress_percent"] == 100
    assert "errors" in out
    assert any(e.get("component") == "soap" for e in out["errors"])


def test_scalar_dataset_completed_no_soap_error(tmp_path: Path) -> None:
    """Test that completed job without SOAP errors stays completed."""
    h5 = tmp_path / "diarization.h5"
    job_id = "test-job-1"

    payload = {
        "job_id": job_id,
        "session_id": "session-1",
        "status": "completed",
        "progress_percent": 100,
        "created_at": "2025-11-09T22:20:49.567807Z",
        "completed_at": "2025-11-09T22:21:11.411440Z",
        "result_data": {
            "transcription": {},
            "diarization": {},
            "soap_status": "ok",
        },
    }
    _write_scalar_job(h5.as_posix(), job_id, payload)

    svc = DiarizationJobService(hdf5_path=h5.as_posix(), persist_resolved=False)
    out = svc.get_job_status(job_id)

    assert out["status"] == "completed"
    assert out["resolved_status"] == "completed"
    assert out["progress_percent"] == 100
    assert "errors" not in out or len(out["errors"]) == 0


def test_not_found_raises_key_error(tmp_path: Path) -> None:
    """Test that missing job raises KeyError."""
    h5 = tmp_path / "diarization.h5"

    # Create empty HDF5 file
    with h5py.File(h5, "w") as f:
        f.create_group("jobs")

    svc = DiarizationJobService(hdf5_path=h5.as_posix(), persist_resolved=False)

    with pytest.raises(KeyError, match="not found"):
        svc.get_job_status("missing-job-id")


def test_file_not_found_raises_error(tmp_path: Path) -> None:
    """Test that missing HDF5 file raises FileNotFoundError."""
    h5 = tmp_path / "nonexistent.h5"

    svc = DiarizationJobService(hdf5_path=h5.as_posix(), persist_resolved=False)

    with pytest.raises(FileNotFoundError, match="HDF5 not found"):
        svc.get_job_status("any-job-id")


def test_persist_resolved_status(tmp_path: Path) -> None:
    """Test that persist_resolved=True rewrites the dataset."""
    h5 = tmp_path / "diarization.h5"
    job_id = "persist-test"

    payload = {
        "job_id": job_id,
        "session_id": "session-1",
        "status": "completed",
        "progress_percent": 95,  # Will be updated to 100
        "created_at": "2025-11-09T22:20:49.567807Z",
        "completed_at": "2025-11-09T22:21:11.411440Z",
        "result_data": {
            "soap_status": "failed",
            "soap_error": "timeout",
        },
    }
    _write_scalar_job(h5.as_posix(), job_id, payload)

    # Enable persistence
    svc = DiarizationJobService(hdf5_path=h5.as_posix(), persist_resolved=True)
    out = svc.get_job_status(job_id)

    assert out["status"] == "completed_with_errors"
    assert out["progress_percent"] == 100

    # Re-read from HDF5 to verify persistence
    with h5py.File(h5, "r") as f:
        raw = f[f"/jobs/{job_id}"][()]
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)

        # Check that persisted status is resolved
        assert data["status"] == "completed_with_errors"
        assert data["progress_percent"] == 100


def test_in_progress_status_unchanged(tmp_path: Path) -> None:
    """Test that in_progress jobs don't get status changed."""
    h5 = tmp_path / "diarization.h5"
    job_id = "in-progress-job"

    payload = {
        "job_id": job_id,
        "session_id": "session-1",
        "status": "in_progress",
        "progress_percent": 50,
        "created_at": "2025-11-09T22:20:49.567807Z",
        "completed_at": None,
        "result_data": {},
    }
    _write_scalar_job(h5.as_posix(), job_id, payload)

    svc = DiarizationJobService(hdf5_path=h5.as_posix(), persist_resolved=False)
    out = svc.get_job_status(job_id)

    assert out["status"] == "in_progress"
    assert out["resolved_status"] == "in_progress"
    assert out["progress_percent"] == 50


def test_failed_status_normalized(tmp_path: Path) -> None:
    """Test that failed/error statuses are normalized to 'failed'."""
    h5 = tmp_path / "diarization.h5"
    job_id = "failed-job"

    payload = {
        "job_id": job_id,
        "session_id": "session-1",
        "status": "error",  # Alternative spelling
        "progress_percent": 30,
        "created_at": "2025-11-09T22:20:49.567807Z",
        "completed_at": None,
        "result_data": {},
    }
    _write_scalar_job(h5.as_posix(), job_id, payload)

    svc = DiarizationJobService(hdf5_path=h5.as_posix(), persist_resolved=False)
    out = svc.get_job_status(job_id)

    assert out["status"] == "failed"
    assert out["resolved_status"] == "failed"
