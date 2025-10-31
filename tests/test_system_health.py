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
    assert backend["ok"] is True
    assert backend["message"] == "operational"
    assert backend["latency_ms"] is not None


def test_service_health_structure():
    """Test each service has correct structure"""
    response = client.get("/api/system/health")
    data = response.json()

    for service_name, service_health in data["services"].items():
        # Each service must have 'ok' field
        assert "ok" in service_health
        assert isinstance(service_health["ok"], bool)

        # Each service should have optional message
        if "message" in service_health:
            assert isinstance(service_health["message"], str)

        # Each service should have optional latency_ms
        if "latency_ms" in service_health:
            if service_health["latency_ms"] is not None:
                assert isinstance(service_health["latency_ms"], (int, float))


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
        datetime.fromisoformat(data["time"].replace('Z', '+00:00'))
    except ValueError:
        pytest.fail("Timestamp is not valid ISO format")
