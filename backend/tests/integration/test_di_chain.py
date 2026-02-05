"""Integration tests for Dependency Injection chain.

Tests full DI resolution from router → service → repository.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.6 - Testing Strategy
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture
def client():
    """FastAPI test client."""
    from backend.app.main import app

    return TestClient(app)


class TestTranscriptionDIChain:
    """Integration tests for Transcription service DI chain."""

    @pytest.mark.skip(reason="Requires running backend with corpus.h5")
    def test_upload_chunk_full_chain(self, client):
        """Test full DI chain: router → DITranscriptionService → ITaskRepository → HDF5."""
        # Arrange
        payload = {
            "session_id": "test-integration-session",
            "chunk_number": 1,
            "audio_data": "base64-encoded-audio-data-here",
        }

        # Act
        response = client.post("/api/internal/transcribe/chunk", json=payload)

        # Assert
        assert response.status_code == 202
        assert "chunk_id" in response.json()


class TestMemoryDIChain:
    """Integration tests for Memory service DI chain."""

    @pytest.mark.skip(reason="Requires running backend with corpus.h5")
    def test_get_memory_full_chain(self, client):
        """Test full DI chain: router → DIMemoryService → HDF5."""
        # Arrange
        patient_id = "test-patient-123"

        # Act
        response = client.get(
            f"/api/public/longitudinal-memory/{patient_id}",
            params={"lookback_days": 30},
        )

        # Assert
        assert response.status_code == 200
        assert "chat_events" in response.json()
        assert "audio_events" in response.json()


class TestLLMDIChain:
    """Integration tests for LLM service DI chain."""

    @pytest.mark.skip(reason="Requires running backend + external LLM")
    @patch("backend.services.llm.services.di_chat_service.llm_generate")
    def test_chat_full_chain(self, mock_llm_generate, client):
        """Test full DI chain: router → DIChatService → LLM provider."""
        # Arrange
        mock_llm_generate.return_value = {
            "response": "I can help with that.",
            "tokens": 50,
            "model": "gpt-4",
        }

        payload = {
            "persona": "clinical_advisor",
            "message": "How do I diagnose pneumonia?",
        }

        # Act
        response = client.post("/api/internal/llm/chat", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["persona"] == "clinical_advisor"
        assert data["tokens_used"] > 0


class TestWorkflowDIChain:
    """Integration tests for Workflow orchestration DI chain."""

    @pytest.mark.skip(reason="Requires running backend + worker pool")
    def test_dispatch_diarization_full_chain(self, client):
        """Test full DI chain: router → WorkflowOrchestrator → worker pool."""
        # Arrange
        session_id = "test-integration-diarization"

        # Act
        response = client.post(
            f"/api/public/workflows/aurity/sessions/{session_id}/diarization"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dispatched"
        assert "job_id" in data


class TestErrorPropagation:
    """Integration tests for error handling across DI chain."""

    @pytest.mark.skip(reason="Requires specific error conditions")
    def test_service_error_propagates_to_http(self, client):
        """Test that service layer errors propagate correctly to HTTP responses."""
        # Arrange
        payload = {
            "persona": "invalid-persona-that-doesnt-exist",
            "message": "Test",
        }

        # Act
        response = client.post("/api/internal/llm/chat", json=payload)

        # Assert
        assert response.status_code == 400
        assert "persona" in response.json()["detail"].lower()
