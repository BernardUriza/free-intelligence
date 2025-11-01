"""
Tests for Triage API
Card: FI-API-FEAT-014
"""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.fi_consult_service import app

client = TestClient(app)

# Test data directory
TEST_DATA_DIR = Path("./data/test_triage_buffers")


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and cleanup test data directory"""
    # Setup: create test directory
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Override DATA_DIR for tests
    import backend.api.triage as triage_module
    original_data_dir = triage_module.DATA_DIR
    triage_module.DATA_DIR = TEST_DATA_DIR

    yield

    # Teardown: restore original and cleanup
    triage_module.DATA_DIR = original_data_dir
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)


def test_intake_ok() -> None:
    """Test successful triage intake"""
    payload = {
        "reason": "Consulta respiratoria",
        "symptoms": ["tos", "fiebre", "dolor de garganta"],
        "audioTranscription": "Paciente presenta tos seca y fiebre de 38 grados",
        "metadata": {"runId": "test_run_001"},
    }

    response = client.post("/api/triage/intake", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "bufferId" in data
    assert data["status"] == "received"
    assert "receivedAt" in data
    assert "manifestUrl" in data

    # Verify bufferId format
    buffer_id = data["bufferId"]
    assert buffer_id.startswith("tri_")
    assert len(buffer_id) == 36  # tri_ + 32 hex chars

    # Verify files exist
    buffer_dir = TEST_DATA_DIR / buffer_id
    assert buffer_dir.exists()
    assert (buffer_dir / "intake.json").exists()
    assert (buffer_dir / "manifest.json").exists()

    # Verify intake.json content
    with open(buffer_dir / "intake.json") as f:
        intake_data = json.load(f)

    assert intake_data["bufferId"] == buffer_id
    assert intake_data["payload"]["reason"] == payload["reason"]
    assert intake_data["payload"]["symptoms"] == payload["symptoms"]
    assert intake_data["payload"]["audioTranscription"] == payload["audioTranscription"]
    assert intake_data["payload"]["metadata"] == payload["metadata"]

    # Verify manifest.json content
    with open(buffer_dir / "manifest.json") as f:
        manifest = json.load(f)

    assert manifest["version"] == "1.0.0"
    assert manifest["bufferId"] == buffer_id
    assert manifest["payloadHash"].startswith("sha256:")
    assert manifest["payloadSubset"]["reason"] == payload["reason"]
    assert manifest["payloadSubset"]["symptomsCount"] == 3
    assert manifest["payloadSubset"]["hasTranscription"] is True
    assert manifest["metadata"]["runId"] == "test_run_001"


def test_intake_422_missing_reason() -> None:
    """Test intake validation: missing reason"""
    payload = {
        "symptoms": ["tos", "fiebre"],
    }

    response = client.post("/api/triage/intake", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_intake_422_short_reason() -> None:
    """Test intake validation: reason too short"""
    payload = {
        "reason": "ab",  # Less than 3 chars
        "symptoms": ["tos"],
    }

    response = client.post("/api/triage/intake", json=payload)

    assert response.status_code == 422


def test_intake_422_transcription_too_long() -> None:
    """Test intake validation: transcription exceeds 32k chars"""
    payload = {
        "reason": "Consulta muy larga",
        "symptoms": ["síntoma"],
        "audioTranscription": "a" * 33_000,  # Exceeds 32k limit
    }

    response = client.post("/api/triage/intake", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "32k" in str(data).lower() or "32000" in str(data)


def test_manifest_fields() -> None:
    """Test manifest contains all required fields"""
    payload = {
        "reason": "Test manifest fields",
        "symptoms": ["test"],
        "metadata": {"runId": "manifest_test", "customField": "value"},
    }

    response = client.post("/api/triage/intake", json=payload)
    assert response.status_code == 200

    buffer_id = response.json()["bufferId"]
    buffer_dir = TEST_DATA_DIR / buffer_id

    # Read manifest
    with open(buffer_dir / "manifest.json") as f:
        manifest = json.load(f)

    # Verify required fields
    assert "version" in manifest
    assert "bufferId" in manifest
    assert "receivedAt" in manifest
    assert "payloadHash" in manifest
    assert "payloadSubset" in manifest
    assert "metadata" in manifest

    # Verify payloadHash format (sha256:...)
    assert manifest["payloadHash"].startswith("sha256:")
    assert len(manifest["payloadHash"]) == 71  # "sha256:" + 64 hex chars

    # Verify metadata passthrough
    assert manifest["metadata"]["runId"] == "manifest_test"
    assert manifest["metadata"]["customField"] == "value"


def test_symptoms_normalization() -> None:
    """Test symptoms normalization from string to list"""
    # Test with list input
    payload1 = {
        "reason": "Test symptoms list",
        "symptoms": ["tos", "fiebre"],
    }

    response1 = client.post("/api/triage/intake", json=payload1)
    assert response1.status_code == 200

    buffer_id1 = response1.json()["bufferId"]
    with open(TEST_DATA_DIR / buffer_id1 / "intake.json") as f:
        intake1 = json.load(f)

    assert isinstance(intake1["payload"]["symptoms"], list)
    assert intake1["payload"]["symptoms"] == ["tos", "fiebre"]

    # Test with string input (comma-separated)
    payload2 = {
        "reason": "Test symptoms string",
        "symptoms": "tos, fiebre, dolor",
    }

    response2 = client.post("/api/triage/intake", json=payload2)
    assert response2.status_code == 200

    buffer_id2 = response2.json()["bufferId"]
    with open(TEST_DATA_DIR / buffer_id2 / "intake.json") as f:
        intake2 = json.load(f)

    assert isinstance(intake2["payload"]["symptoms"], list)
    assert intake2["payload"]["symptoms"] == ["tos", "fiebre", "dolor"]


def test_get_manifest() -> None:
    """Test GET /api/triage/manifest/{buffer_id}"""
    # Create intake first
    payload = {
        "reason": "Test manifest retrieval",
        "symptoms": ["test"],
    }

    response = client.post("/api/triage/intake", json=payload)
    assert response.status_code == 200
    buffer_id = response.json()["bufferId"]

    # Retrieve manifest
    manifest_response = client.get(f"/api/triage/manifest/{buffer_id}")
    assert manifest_response.status_code == 200

    manifest = manifest_response.json()
    assert manifest["bufferId"] == buffer_id
    assert manifest["version"] == "1.0.0"


def test_get_manifest_404() -> None:
    """Test GET /api/triage/manifest/{buffer_id} with non-existent ID"""
    response = client.get("/api/triage/manifest/nonexistent_buffer_id")
    assert response.status_code == 404
    data = response.json()
    # Check for either 'detail' (FastAPI default) or 'message' (custom middleware)
    error_text = data.get("detail", data.get("message", "")).lower()
    assert "not found" in error_text


def test_atomic_write() -> None:
    """Test that intake.json is written atomically (no .tmp file left)"""
    payload = {
        "reason": "Test atomic write",
        "symptoms": ["test"],
    }

    response = client.post("/api/triage/intake", json=payload)
    assert response.status_code == 200

    buffer_id = response.json()["bufferId"]
    buffer_dir = TEST_DATA_DIR / buffer_id

    # Verify no .tmp file exists
    assert not (buffer_dir / "intake.json.tmp").exists()
    # Verify final file exists
    assert (buffer_dir / "intake.json").exists()
