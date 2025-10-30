"""
Integration tests for PolicyEnforcer Dependency Injection in LLM providers.

Tests that providers correctly accept injected PolicyEnforcer and use it for egress checks.

File: tests/test_provider_di.py
Created: 2025-10-30
Reference: FI-BACKEND-REF-006
"""

import pytest
from unittest.mock import Mock, patch

from backend.llm_adapter import LLMBudget, LLMRequest
from backend.policy_enforcer import PolicyEnforcer, PolicyViolation
from backend.providers.claude import ClaudeAdapter
from backend.providers.ollama import OllamaAdapter


@pytest.fixture
def mock_policy_allow():
    """Mock PolicyEnforcer that allows all egress"""
    policy = Mock(spec=PolicyEnforcer)
    policy.check_egress = Mock(return_value=None)  # No exception = allowed
    return policy


@pytest.fixture
def mock_policy_deny():
    """Mock PolicyEnforcer that denies all egress"""
    policy = Mock(spec=PolicyEnforcer)
    policy.check_egress = Mock(side_effect=PolicyViolation(
        rule="sovereignty.egress",
        message="External egress denied by test policy",
        metadata={"url": "test"}
    ))
    return policy


class TestClaudeAdapterDI:
    """Test ClaudeAdapter dependency injection"""

    def test_claude_accepts_policy_enforcer(self, mock_policy_allow):
        """ClaudeAdapter should accept PolicyEnforcer via constructor"""
        adapter = ClaudeAdapter(
            api_key="test-key",
            policy_enforcer=mock_policy_allow
        )
        assert adapter.policy == mock_policy_allow

    def test_claude_uses_default_policy_if_none(self):
        """ClaudeAdapter should create default PolicyEnforcer if not provided"""
        adapter = ClaudeAdapter(api_key="test-key")
        assert isinstance(adapter.policy, PolicyEnforcer)

    @patch('anthropic.Anthropic')
    def test_claude_uses_injected_policy_on_generate(self, mock_anthropic, mock_policy_allow):
        """ClaudeAdapter should use injected policy for egress checks"""
        # Setup mock client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="test response")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=20)
        mock_response.stop_reason = "stop"
        mock_response.id = "test-id"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        adapter = ClaudeAdapter(
            api_key="test-key",
            policy_enforcer=mock_policy_allow
        )

        request = LLMRequest(
            prompt="test prompt",
            max_tokens=100,
            temperature=0.7
        )

        adapter.generate(request)

        # Verify policy was called with correct URL
        mock_policy_allow.check_egress.assert_called_once()
        call_args = mock_policy_allow.check_egress.call_args
        assert "https://api.anthropic.com" in call_args[0]

    @patch('anthropic.Anthropic')
    def test_claude_respects_policy_denial(self, mock_anthropic, mock_policy_deny):
        """ClaudeAdapter should respect PolicyViolation from injected policy"""
        adapter = ClaudeAdapter(
            api_key="test-key",
            policy_enforcer=mock_policy_deny
        )

        request = LLMRequest(
            prompt="test prompt",
            max_tokens=100,
            temperature=0.7
        )

        # Should raise LLMProviderError due to policy denial
        with pytest.raises(Exception) as exc_info:
            adapter.generate(request)

        # Verify error mentions policy blocking
        assert "policy" in str(exc_info.value).lower() or "blocked" in str(exc_info.value).lower()


class TestOllamaAdapterDI:
    """Test OllamaAdapter dependency injection"""

    def test_ollama_accepts_policy_enforcer(self, mock_policy_allow):
        """OllamaAdapter should accept PolicyEnforcer via constructor"""
        adapter = OllamaAdapter(policy_enforcer=mock_policy_allow)
        assert adapter.policy == mock_policy_allow

    def test_ollama_uses_default_policy_if_none(self):
        """OllamaAdapter should create default PolicyEnforcer if not provided"""
        adapter = OllamaAdapter()
        assert isinstance(adapter.policy, PolicyEnforcer)

    @patch('backend.providers.ollama.requests.post')
    def test_ollama_uses_injected_policy_on_generate(self, mock_post, mock_policy_allow):
        """OllamaAdapter should use injected policy for egress checks"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "test response"},
            "done": True
        }
        mock_post.return_value = mock_response

        adapter = OllamaAdapter(policy_enforcer=mock_policy_allow)

        request = LLMRequest(
            prompt="test prompt",
            max_tokens=100,
            temperature=0.7
        )

        adapter.generate(request)

        # Verify policy was called with Ollama URL
        mock_policy_allow.check_egress.assert_called_once()
        call_args = mock_policy_allow.check_egress.call_args
        assert "127.0.0.1" in call_args[0][0] or "localhost" in call_args[0][0]

    @patch('backend.providers.ollama.requests.post')
    def test_ollama_respects_policy_denial(self, mock_post, mock_policy_deny):
        """OllamaAdapter should respect PolicyViolation from injected policy"""
        adapter = OllamaAdapter(policy_enforcer=mock_policy_deny)

        request = LLMRequest(
            prompt="test prompt",
            max_tokens=100,
            temperature=0.7
        )

        # Should raise LLMProviderError due to policy denial
        with pytest.raises(Exception) as exc_info:
            adapter.generate(request)

        # Verify error mentions policy blocking
        assert "policy" in str(exc_info.value).lower() or "blocked" in str(exc_info.value).lower()


class TestPolicyIsolation:
    """Test that each adapter instance has isolated policy"""

    def test_different_adapters_have_independent_policies(self, mock_policy_allow, mock_policy_deny):
        """Different adapter instances should use their own injected policies"""
        adapter_allow = ClaudeAdapter(
            api_key="test-key",
            policy_enforcer=mock_policy_allow
        )
        adapter_deny = ClaudeAdapter(
            api_key="test-key-2",
            policy_enforcer=mock_policy_deny
        )

        assert adapter_allow.policy == mock_policy_allow
        assert adapter_deny.policy == mock_policy_deny
        assert adapter_allow.policy != adapter_deny.policy


# Run tests:
# python3 -m pytest tests/test_provider_di.py -v
