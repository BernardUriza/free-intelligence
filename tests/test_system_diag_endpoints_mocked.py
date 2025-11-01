"""Comprehensive mocked tests for system health and diagnostics endpoints.

Tests system.py and fi_diag.py endpoints using mocked services.
All tests use unittest.mock.Mock for service isolation.

Coverage:
- GET /api/system/health - system health aggregation
- GET /api/diag/health - comprehensive diagnostics
- GET /api/diag/services - PM2/service status
- GET /api/diag/system - system information
- GET /api/diag/readiness - Kubernetes readiness probe
- GET /api/diag/liveness - Kubernetes liveness probe
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.fi_diag import router as diag_router
from backend.api.system import router as system_router


@pytest.fixture
def test_client():
    """Create a FastAPI app with system and diag routers for testing."""
    app = FastAPI()
    app.include_router(system_router)
    app.include_router(diag_router)
    return TestClient(app)


class TestSystemHealthEndpoint:
    """Tests for GET /api/system/health endpoint."""

    def test_system_health_success(self, test_client):
        """Test successful system health check."""
        with patch("backend.api.system.get_container") as mock_get_container:
            mock_container = Mock()
            mock_health_service = Mock()

            mock_health_service.get_system_health.return_value = {
                "ok": True,
                "services": {
                    "backend": True,
                    "diarization": {"whisper": True, "ffmpeg": True},
                    "llm": {"ollama": True, "models": ["qwen2.5:7b"]},
                    "policy": True,
                },
            }

            mock_container.get_system_health_service.return_value = mock_health_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/system/health")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["services"]["backend"] is True
            assert data["services"]["diarization"]["whisper"] is True
            assert data["version"] == "v0.3.0"
            assert "time" in data

    def test_system_health_degraded(self, test_client):
        """Test degraded system health (LLM unavailable but critical OK)."""
        with patch("backend.api.system.get_container") as mock_get_container:
            mock_container = Mock()
            mock_health_service = Mock()

            mock_health_service.get_system_health.return_value = {
                "ok": True,  # Critical services OK
                "services": {
                    "backend": True,
                    "diarization": {"whisper": True, "ffmpeg": True},
                    "llm": {"ollama": False, "models": []},  # Optional service down
                    "policy": True,
                },
            }

            mock_container.get_system_health_service.return_value = mock_health_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/system/health")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True  # Still OK because LLM is optional
            assert data["services"]["llm"]["ollama"] is False

    def test_system_health_unhealthy(self, test_client):
        """Test unhealthy system health (critical service down)."""
        with patch("backend.api.system.get_container") as mock_get_container:
            mock_container = Mock()
            mock_health_service = Mock()

            mock_health_service.get_system_health.return_value = {
                "ok": False,
                "services": {
                    "backend": True,
                    "diarization": {"whisper": False, "ffmpeg": True},  # Critical service down
                    "llm": {"ollama": False, "models": []},
                    "policy": True,
                },
            }

            mock_container.get_system_health_service.return_value = mock_health_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/system/health")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is False  # Marked unhealthy
            assert data["services"]["diarization"]["whisper"] is False

    def test_system_health_service_error(self, test_client):
        """Test system health endpoint when service raises exception."""
        with patch("backend.api.system.get_container") as mock_get_container:
            mock_container = Mock()
            mock_health_service = Mock()

            mock_health_service.get_system_health.side_effect = RuntimeError("Service error")
            mock_container.get_system_health_service.return_value = mock_health_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/system/health")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is False  # Degraded on error
            assert "error" in data["services"]


class TestDiagnosticsHealthEndpoint:
    """Tests for GET /api/diag/health endpoint."""

    def test_diagnostics_health_all_healthy(self, test_client):
        """Test diagnostics with all checks healthy."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.get_diagnostics.return_value = {
                "status": "healthy",
                "checks": {
                    "python": {"status": "healthy", "version": "3.11.0"},
                    "storage": {"status": "healthy", "exists": True, "writable": True},
                    "data": {"status": "healthy", "exists": True, "writable": True},
                    "corpus": {"status": "healthy", "exists": True, "size_mb": 256.5},
                    "nodejs": {"status": "healthy", "version": "v18.0.0"},
                    "pnpm": {"status": "healthy", "version": "8.0.0"},
                    "pm2": {"status": "healthy", "services": []},
                },
            }

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["checks"]["python"]["status"] == "healthy"
            assert data["checks"]["storage"]["exists"] is True
            assert data["version"] == "0.1.0"
            assert "timestamp" in data

    def test_diagnostics_health_degraded(self, test_client):
        """Test diagnostics with degraded status (non-critical service down)."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.get_diagnostics.return_value = {
                "status": "degraded",
                "checks": {
                    "python": {"status": "healthy", "version": "3.11.0"},
                    "storage": {"status": "healthy", "exists": True, "writable": True},
                    "data": {"status": "degraded", "exists": False, "writable": False},
                    "corpus": {"status": "warning", "exists": False, "size_mb": 0},
                    "nodejs": {"status": "unhealthy", "version": None},
                    "pnpm": {"status": "unhealthy", "version": None},
                    "pm2": {"status": "warning", "services": []},
                },
            }

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["checks"]["nodejs"]["status"] == "unhealthy"

    def test_diagnostics_health_service_error(self, test_client):
        """Test diagnostics health when service raises exception."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.get_diagnostics.side_effect = RuntimeError("Service error")
            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"


class TestServiceStatusEndpoint:
    """Tests for GET /api/diag/services endpoint."""

    def test_service_status_with_pm2(self, test_client):
        """Test service status with PM2 running services."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.check_pm2.return_value = {
                "status": "healthy",
                "services": [
                    {"name": "backend", "status": "online", "pid": 1234, "uptime": 3600},
                    {"name": "frontend", "status": "online", "pid": 5678, "uptime": 3600},
                    {"name": "ollama", "status": "online", "pid": 9012, "uptime": 3600},
                ],
            }

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/services")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[0]["service"] == "backend"
            assert data[0]["status"] == "online"
            assert data[0]["pid"] == 1234

    def test_service_status_empty(self, test_client):
        """Test service status with no services running."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.check_pm2.return_value = {
                "status": "healthy",
                "services": [],
            }

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/services")

            assert response.status_code == 200
            data = response.json()
            assert data == []

    def test_service_status_service_error(self, test_client):
        """Test service status when service raises exception."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.check_pm2.side_effect = RuntimeError("PM2 error")
            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/services")

            assert response.status_code == 200
            data = response.json()
            assert data == []  # Returns empty list on error


class TestSystemInfoEndpoint:
    """Tests for GET /api/diag/system endpoint."""

    def test_system_info_complete(self, test_client):
        """Test system info with all details available."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.get_system_info.return_value = {
                "os": "Darwin",
                "release": "25.0.0",
                "python": "3.11.0 (main, Oct 24 2024)",
                "cpu_count": 8,
                "cpu_percent": 25.5,
                "disk_total_gb": 500.0,
                "disk_used_gb": 250.0,
                "disk_percent": 50.0,
                "memory_total_gb": 32.0,
                "memory_used_gb": 16.0,
                "memory_percent": 50.0,
            }

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/system")

            assert response.status_code == 200
            data = response.json()
            assert data["os"] == "Darwin"
            assert data["cpu_count"] == 8
            assert data["memory_total_gb"] == 32.0

    def test_system_info_minimal(self, test_client):
        """Test system info with minimal details (psutil unavailable)."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.get_system_info.return_value = {
                "os": "Linux",
                "release": "5.10.0",
                "python": "3.11.0",
            }

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/system")

            assert response.status_code == 200
            data = response.json()
            assert data["os"] == "Linux"

    def test_system_info_service_error(self, test_client):
        """Test system info when service raises exception."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.get_system_info.side_effect = RuntimeError("System info error")
            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/system")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data


class TestReadinessProbe:
    """Tests for GET /api/diag/readiness endpoint."""

    def test_readiness_ready(self, test_client):
        """Test readiness check when system is ready."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.check_readiness.return_value = True

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/readiness")

            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is True
            assert "timestamp" in data

    def test_readiness_not_ready(self, test_client):
        """Test readiness check when system is not ready."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.check_readiness.return_value = False

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/readiness")

            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is False

    def test_readiness_service_error(self, test_client):
        """Test readiness check when service raises exception."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.check_readiness.side_effect = RuntimeError("Readiness check error")
            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/readiness")

            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is False
            assert "error" in data


class TestLivenessProbe:
    """Tests for GET /api/diag/liveness endpoint."""

    def test_liveness_alive(self, test_client):
        """Test liveness check when system is alive."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.check_liveness.return_value = True

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/liveness")

            assert response.status_code == 200
            data = response.json()
            assert data["alive"] is True
            assert "timestamp" in data
            assert "pid" in data

    def test_liveness_always_true(self, test_client):
        """Test that liveness is always true (process alive if responding)."""
        # If we get a response, the process must be alive
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.check_liveness.return_value = True

            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/liveness")

            assert response.status_code == 200
            data = response.json()
            assert data["alive"] is True

    def test_liveness_service_error(self, test_client):
        """Test liveness check when service raises exception."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()

            mock_diag_service.check_liveness.side_effect = RuntimeError("Liveness check error")
            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/liveness")

            assert response.status_code == 200
            data = response.json()
            assert data["alive"] is False
            assert "error" in data


class TestErrorHandling:
    """Tests for error handling across all endpoints."""

    def test_container_initialization_error_system_health(self, test_client):
        """Test system health endpoint when container fails to initialize."""
        with patch("backend.api.system.get_container") as mock_get_container:
            mock_get_container.side_effect = RuntimeError("Container init error")

            response = test_client.get("/api/system/health")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is False
            assert "error" in data["services"]

    def test_container_initialization_error_diag_health(self, test_client):
        """Test diagnostics health endpoint when container fails to initialize."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_get_container.side_effect = RuntimeError("Container init error")

            response = test_client.get("/api/diag/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"

    def test_service_getter_error_services(self, test_client):
        """Test service status when service getter fails."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_container.get_diagnostics_service.side_effect = RuntimeError(
                "Service getter error"
            )
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/services")

            assert response.status_code == 200
            data = response.json()
            assert data == []


class TestResponseFormats:
    """Tests for response format validation."""

    def test_system_health_response_format(self, test_client):
        """Test system health response has all required fields."""
        with patch("backend.api.system.get_container") as mock_get_container:
            mock_container = Mock()
            mock_health_service = Mock()
            mock_health_service.get_system_health.return_value = {
                "ok": True,
                "services": {"backend": True},
            }
            mock_container.get_system_health_service.return_value = mock_health_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/system/health")
            data = response.json()

            assert "ok" in data
            assert "services" in data
            assert "version" in data
            assert "time" in data
            assert isinstance(data["ok"], bool)
            assert isinstance(data["services"], dict)

    def test_diagnostics_health_response_format(self, test_client):
        """Test diagnostics health response has all required fields."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()
            mock_diag_service.get_diagnostics.return_value = {
                "status": "healthy",
                "checks": {},
            }
            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/health")
            data = response.json()

            assert "status" in data
            assert "timestamp" in data
            assert "checks" in data
            assert "version" in data

    def test_service_status_response_format(self, test_client):
        """Test service status response items have required fields."""
        with patch("backend.api.fi_diag.get_container") as mock_get_container:
            mock_container = Mock()
            mock_diag_service = Mock()
            mock_diag_service.check_pm2.return_value = {
                "status": "healthy",
                "services": [
                    {"name": "svc", "status": "online", "pid": 123},
                ],
            }
            mock_container.get_diagnostics_service.return_value = mock_diag_service
            mock_get_container.return_value = mock_container

            response = test_client.get("/api/diag/services")
            data = response.json()

            assert len(data) > 0
            service = data[0]
            assert "service" in service
            assert "status" in service
            assert "pid" in service
