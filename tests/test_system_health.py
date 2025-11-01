"""
Test System Health API
Card: FI-UI-FEAT-204 (Service Health + Diarization Progress)

Tests for unified system health endpoint GET /api/system/health
"""

import pytest
from fastapi.testclient import TestClient

from backend.fi_consult_service import app

client = TestClient(app)


def test_health_endpoint_exists():
    """Test that health endpoint exists and returns 200"""
    response = client.get("/api/system/health")
    assert response.status_code == 200


def test_health_response_structure():
    """Test health response has correct structure"""
    response = client.get("/api/system/health")
    assert response.status_code == 200

    data = response.json()

    # Check top-level fields
    assert "ok" in data
    assert "services" in data
    assert "version" in data
    assert "time" in data

    # Check ok is boolean
    assert isinstance(data["ok"], bool)

    # Check services dict
    services = data["services"]
    assert isinstance(services, dict)

    # Check critical services exist
    assert "backend" in services
    assert "diarization" in services
    assert "llm" in services
    assert "policy" in services


def test_backend_service_health():
    """Test backend service always reports healthy"""
    response = client.get("/api/system/health")
    data = response.json()

    backend = data["services"]["backend"]
    assert backend is True


def test_service_health_structure():
    """Test each service has correct structure"""
    response = client.get("/api/system/health")
    data = response.json()

    services = data["services"]

    # backend and policy are booleans
    assert isinstance(services["backend"], bool)
    assert isinstance(services["policy"], bool)

    # diarization is dict with whisper and ffmpeg
    assert isinstance(services["diarization"], dict)
    assert "whisper" in services["diarization"]
    assert "ffmpeg" in services["diarization"]
    assert isinstance(services["diarization"]["whisper"], bool)
    assert isinstance(services["diarization"]["ffmpeg"], bool)

    # llm is dict with ollama and models
    assert isinstance(services["llm"], dict)
    assert "ollama" in services["llm"]
    assert "models" in services["llm"]
    assert isinstance(services["llm"]["ollama"], bool)
    assert isinstance(services["llm"]["models"], list)


def test_version_field():
    """Test version field is present and valid"""
    response = client.get("/api/system/health")
    data = response.json()

    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


def test_timestamp_field():
    """Test timestamp field is present and valid ISO format"""
    response = client.get("/api/system/health")
    data = response.json()

    assert "time" in data
    assert isinstance(data["time"], str)

    # Verify it's a valid ISO format timestamp
    from datetime import datetime

    try:
        datetime.fromisoformat(data["time"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail("Timestamp is not valid ISO format")
