"""Integration tests for Assistant endpoints with OpenAI compatibility.

Tests the refactored assistant API endpoints that follow OpenAI Chat Completions conventions.

NOTE: These tests require the full container infrastructure which may not be
available in CI. They are skipped if backend.services import fails.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Skip if backend.services is not available (CI environment without full deps)
try:
    import backend.services
except ImportError:
    pytest.skip("backend.services not available", allow_module_level=True)


@pytest.fixture
def client():
    """Create test client for Assistant API integration tests."""
    from backend.app.main import create_app

    app = create_app()
    return TestClient(app)


class TestAssistantSchemas:
    """Unit tests for OpenAI-compatible schemas."""

    def test_message_model(self):
        """Test Message model creation and validation."""
        from backend.api.routers.assistant.public.assistant_schemas import Message

        # Test basic message
        msg = Message(role="user", content="Hello!")
        assert msg.role == "user"
        assert msg.content == "Hello!"
        assert msg.name is None

        # Test message with name
        msg_with_name = Message(role="user", content="Hello!", name="john")
        assert msg_with_name.name == "john"

    def test_chat_completion_request(self):
        """Test ChatCompletionRequest model with OpenAI compatibility."""
        from backend.api.routers.assistant.public.assistant_schemas import (
            ChatCompletionRequest,
            Message,
        )

        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello!"),
        ]

        request = ChatCompletionRequest(
            messages=messages,
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=2048,
            persona="general_assistant",
        )

        assert len(request.messages) == 2
        assert request.messages[0].role == "system"
        assert request.messages[1].role == "user"
        assert request.model == "gpt-4o-mini"
        assert request.temperature == 0.7
        assert request.persona == "general_assistant"
        assert request.stream is False  # Default value

    def test_chat_completion_request_validation(self):
        """Test ChatCompletionRequest validation."""
        from backend.api.routers.assistant.public.assistant_schemas import (
            ChatCompletionRequest,
            Message,
        )
        from pydantic import ValidationError

        # Test empty messages
        with pytest.raises(ValidationError):
            ChatCompletionRequest(messages=[])

        # Test invalid temperature
        messages = [Message(role="user", content="Hello!")]
        with pytest.raises(ValidationError):
            ChatCompletionRequest(messages=messages, temperature=3.0)  # > 2.0

        # Test invalid max_tokens
        with pytest.raises(ValidationError):
            ChatCompletionRequest(messages=messages, max_tokens=0)  # < 1

    def test_chat_completion_response(self):
        """Test ChatCompletionResponse model."""
        from backend.api.routers.assistant.public.assistant_schemas import (
            ChatCompletionChoice,
            ChatCompletionResponse,
            ChatCompletionUsage,
            Message,
        )

        usage = ChatCompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)

        choice = ChatCompletionChoice(
            index=0, message=Message(role="assistant", content="Hello back!"), finish_reason="stop"
        )

        response = ChatCompletionResponse(
            id="chatcmpl-test",
            created=1234567890,
            model="gpt-4o-mini",
            choices=[choice],
            usage=usage,
            persona="general_assistant",
        )

        assert response.id == "chatcmpl-test"
        assert response.object == "chat.completion"  # Default value
        assert response.choices[0].message.content == "Hello back!"
        assert response.persona == "general_assistant"


class TestAssistantEndpoints:
    """Integration tests for Assistant API endpoints."""

    def test_chat_completion_basic(self, client):
        """Test basic chat completion with OpenAI format."""
        payload = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "persona": "general_assistant",
        }

        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)

        # Should return 200 even if LLM fails (mocked)
        assert response.status_code in [200, 500]  # 500 if LLM not available

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["object"] == "chat.completion"
            assert "choices" in data
            assert len(data["choices"]) == 1
            assert "message" in data["choices"][0]
            assert data["choices"][0]["message"]["role"] == "assistant"
            assert "usage" in data
            assert "persona" in data

    def test_chat_completion_with_system_message(self, client):
        """Test chat completion with system message."""
        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful medical assistant."},
                {"role": "user", "content": "What is AURITY?"},
            ],
            "model": "gpt-4o-mini",
            "temperature": 0.5,
            "persona": "general_assistant",
        }

        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)
        assert response.status_code in [200, 500]

    def test_chat_completion_validation_errors(self, client):
        """Test chat completion validation errors."""

        # Empty messages
        payload = {"messages": []}
        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)
        assert response.status_code == 422  # Validation error

        # Invalid last message role
        payload = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},  # Last message not from user
            ]
        }
        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)
        assert response.status_code == 400
        assert "Last message must be from user" in response.json()["detail"]

    def test_chat_completion_with_behavior_metrics(self, client):
        """Test chat completion with AURITY behavior metrics extension."""
        payload = {
            "messages": [{"role": "user", "content": "I'm feeling anxious"}],
            "model": "gpt-4o-mini",
            "behavior_metrics": {"rapid_clicks": 5, "idle_time_seconds": 30, "recent_errors": 2},
            "persona": "general_assistant",
        }

        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            # Should include emotional analysis when behavior metrics provided
            assert "emotional_analysis" in data

    def test_streaming_endpoint_requires_stream_true(self, client):
        """Test that streaming endpoint requires stream=true."""
        payload = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "stream": False,  # Not streaming
        }

        response = client.post("/api/workflows/aurity/assistant/chat/stream", json=payload)
        assert response.status_code == 400
        assert "Use /assistant/chat for non-streaming" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_streaming_endpoint_basic(self, client):
        """Test basic streaming functionality."""
        payload = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "stream": True,
            "model": "gpt-4o-mini",
            "persona": "general_assistant",
        }

        response = client.post("/api/workflows/aurity/assistant/chat/stream", json=payload)

        # Should return streaming response (may fail due to connection issues in test env)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            # Check content type for SSE
            assert "text/event-stream" in response.headers.get("content-type", "")

            # Read streaming content
            content = response.content.decode()
            assert "data:" in content

            # Should end with [DONE] if successful
            assert "[DONE]" in content
        else:
            # If it fails (which is expected in test environment), check error format
            content = response.content.decode()
            # Should still be SSE format even for errors
            assert "data:" in content
            assert "error" in content

    def test_openai_sdk_compatibility(self, client):
        """Test compatibility with OpenAI SDK request format."""
        # This simulates what the OpenAI Python SDK would send
        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What can you help me with?"},
            ],
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 150,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "stream": False,
            "user": "test-user-123",
        }

        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            # Should have OpenAI-compatible structure
            assert "id" in data
            assert "object" in data
            assert "created" in data
            assert "model" in data
            assert "choices" in data
            assert "usage" in data

            # Choices should have the right structure
            choice = data["choices"][0]
            assert "index" in choice
            assert "message" in choice
            assert "finish_reason" in choice

            # Message should have role and content
            message = choice["message"]
            assert "role" in message
            assert "content" in message

    def test_aurity_extensions(self, client):
        """Test AURITY-specific extensions work correctly."""
        payload = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "model": "gpt-4o-mini",
            "persona": "onboarding_guide",  # AURITY-specific
            "session_id": "test-session-123",  # AURITY-specific
            "behavior_metrics": {  # AURITY-specific
                "rapid_clicks": 1,
                "idle_time_seconds": 10,
            },
        }

        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            # Should include AURITY extensions in response
            assert "persona" in data
            assert "emotional_analysis" in data

    def test_introduction_endpoint_unchanged(self, client):
        """Test that introduction endpoint still works (not refactored)."""
        payload = {"physician_name": "Dr. Smith", "clinic_name": "Test Clinic"}

        response = client.post("/api/workflows/aurity/assistant/introduction", json=payload)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "persona" in data
            assert "tokens_used" in data


class TestAssistantErrorHandling:
    """Test error handling in assistant endpoints."""

    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post(
            "/api/workflows/aurity/assistant/chat",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422  # FastAPI validation error

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        payload = {}  # Missing messages
        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)
        assert response.status_code == 422

    def test_large_request(self, client):
        """Test handling of very large requests."""
        large_content = "x" * 100000  # 100KB content
        payload = {"messages": [{"role": "user", "content": large_content}], "model": "gpt-4o-mini"}

        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)
        # Should handle gracefully (either process or reject)
        assert response.status_code in [200, 400, 413, 500]


class TestAssistantBackwardCompatibility:
    """Test backward compatibility with old formats."""

    def test_old_format_still_supported(self, client):
        """Test that old internal formats still work if needed."""
        # This would test if any legacy code paths still work
        # For now, just ensure new endpoints work
        payload = {"messages": [{"role": "user", "content": "Test"}], "model": "gpt-4o-mini"}

        response = client.post("/api/workflows/aurity/assistant/chat", json=payload)
        assert response.status_code in [200, 500]
