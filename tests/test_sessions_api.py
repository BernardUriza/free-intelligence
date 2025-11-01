#!/usr/bin/env python3
"""
Free Intelligence - Sessions API Tests

Tests for FastAPI Sessions endpoints.

File: tests/test_sessions_api.py
Card: FI-API-FEAT-009
Created: 2025-10-29
"""

import shutil
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.sessions import router, store


@pytest.fixture
def app():
    """Create FastAPI app with sessions router"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset store before each test"""
    # Use temp directory for tests
    from pathlib import Path

    temp_dir = tempfile.mkdtemp()
    store.data_dir = Path(temp_dir)
    store.manifest_path = Path(temp_dir) / "manifest.jsonl"
    store.index_path = Path(temp_dir) / "index.json"

    # Initialize
    with open(store.manifest_path, "w") as f:
        pass
    store._write_index({})

    yield

    # Cleanup
    shutil.rmtree(temp_dir)


def test_list_sessions_empty(client) -> None:
    """Test listing sessions when empty"""
    response = client.get("/api/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_create_session(client) -> None:
    """Test creating a new session"""
    response = client.post(
        "/api/sessions",
        json={
            "owner_hash": "sha256:test123",
            "status": "new",
            "thread_id": "thread_abc",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["owner_hash"] == "sha256:test123"
    assert data["status"] == "new"
    assert data["thread_id"] == "thread_abc"
    assert data["interaction_count"] == 0


def test_create_session_minimal(client) -> None:
    """Test creating session with minimal data"""
    response = client.post(
        "/api/sessions",
        json={"owner_hash": "sha256:minimal"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["owner_hash"] == "sha256:minimal"
    assert data["status"] == "new"  # default


def test_get_session(client) -> None:
    """Test retrieving session by ID"""
    # Create session
    create_resp = client.post(
        "/api/sessions",
        json={"owner_hash": "sha256:get_test"},
    )
    session_id = create_resp.json()["id"]

    # Get session
    response = client.get(f"/api/sessions/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["owner_hash"] == "sha256:get_test"


def test_get_session_not_found(client) -> None:
    """Test getting non-existent session"""
    response = client.get("/api/sessions/NONEXISTENT_ID")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_sessions_with_pagination(client) -> None:
    """Test list sessions with pagination"""
    # Create 5 sessions
    for i in range(5):
        client.post(
            "/api/sessions",
            json={"owner_hash": f"sha256:owner{i}"},
        )

    # List all
    response = client.get("/api/sessions?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 5
    assert data["total"] == 5

    # Page 1
    response = client.get("/api/sessions?limit=2&offset=0")
    data = response.json()
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Page 2
    response = client.get("/api/sessions?limit=2&offset=2")
    data = response.json()
    assert len(data["items"]) == 2
    assert data["offset"] == 2


def test_list_sessions_filter_by_owner(client) -> None:
    """Test filtering sessions by owner_hash"""
    # Create sessions
    client.post("/api/sessions", json={"owner_hash": "sha256:alice"})
    client.post("/api/sessions", json={"owner_hash": "sha256:alice"})
    client.post("/api/sessions", json={"owner_hash": "sha256:bob"})

    # Filter by alice
    response = client.get("/api/sessions?owner_hash=sha256:alice")
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2

    # Filter by bob
    response = client.get("/api/sessions?owner_hash=sha256:bob")
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1


def test_update_session_status(client) -> None:
    """Test updating session status"""
    # Create session
    create_resp = client.post(
        "/api/sessions",
        json={"owner_hash": "sha256:update_test"},
    )
    session_id = create_resp.json()["id"]

    # Update status
    response = client.patch(
        f"/api/sessions/{session_id}",
        json={"status": "active"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["id"] == session_id


def test_update_session_interaction_count(client) -> None:
    """Test updating interaction count"""
    # Create session
    create_resp = client.post(
        "/api/sessions",
        json={"owner_hash": "sha256:count_test"},
    )
    session_id = create_resp.json()["id"]

    # Update count
    response = client.patch(
        f"/api/sessions/{session_id}",
        json={"interaction_count": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["interaction_count"] == 10


def test_update_session_not_found(client) -> None:
    """Test updating non-existent session"""
    response = client.patch(
        "/api/sessions/NONEXISTENT",
        json={"status": "active"},
    )

    assert response.status_code == 404


def test_create_session_invalid_status(client) -> None:
    """Test creating session with invalid status"""
    response = client.post(
        "/api/sessions",
        json={
            "owner_hash": "sha256:test",
            "status": "invalid_status",
        },
    )

    assert response.status_code == 422  # Validation error


def test_update_session_invalid_status(client) -> None:
    """Test updating with invalid status"""
    # Create session
    create_resp = client.post(
        "/api/sessions",
        json={"owner_hash": "sha256:test"},
    )
    session_id = create_resp.json()["id"]

    # Update with invalid status
    response = client.patch(
        f"/api/sessions/{session_id}",
        json={"status": "invalid"},
    )

    assert response.status_code == 422


def test_health_check_via_list(client) -> None:
    """Test API health via list endpoint (health check moved to app level)"""
    response = client.get("/api/sessions")

    # If we can list sessions, API is healthy
    assert response.status_code == 200
    assert "items" in response.json()


def test_timestamps_auto_updated(client) -> None:
    """Test that timestamps are auto-updated on PATCH"""
    # Create session
    create_resp = client.post(
        "/api/sessions",
        json={"owner_hash": "sha256:timestamp_test"},
    )
    session_id = create_resp.json()["id"]
    original_updated_at = create_resp.json()["updated_at"]

    import time

    time.sleep(0.1)

    # Update session
    response = client.patch(
        f"/api/sessions/{session_id}",
        json={"status": "active"},
    )

    data = response.json()
    assert data["updated_at"] != original_updated_at
    assert data["last_active"] != create_resp.json()["last_active"]
