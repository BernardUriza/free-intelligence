"""
Test suite for llm_adapter.py

Validates:
- LLMBudget tracking
- LLMAdapter base class
- Factory pattern
- Provider implementations (mock Claude, real Ollama stub)
"""

import time
import unittest

from backend.llm_adapter import (
    LLMBudget,
    LLMRequest,
    NotImplementedProviderError,
    create_adapter,
)


class TestLLMBudget(unittest.TestCase):
    """Test budget tracking"""

    def test_budget_initialization(self):
        """Test: Budget initializes with defaults"""
        budget = LLMBudget()

        self.assertEqual(budget.max_tokens_per_hour, 100_000)
        self.assertEqual(budget.max_requests_per_hour, 100)
        self.assertEqual(budget.tokens_used, 0)
        self.assertEqual(budget.requests_made, 0)

    def test_budget_can_make_request(self):
        """Test: Budget allows requests within limits"""
        budget = LLMBudget(max_tokens_per_hour=1000, max_requests_per_hour=10)

        # Should allow first request
        self.assertTrue(budget.can_make_request(estimated_tokens=500))

        # Track a request
        budget.track_request(500)

        # Should still allow another request
        self.assertTrue(budget.can_make_request(estimated_tokens=400))

        # Should deny request that would exceed budget
        self.assertFalse(budget.can_make_request(estimated_tokens=600))

    def test_budget_request_limit(self):
        """Test: Budget enforces request count limit"""
        budget = LLMBudget(max_requests_per_hour=3)

        # Track 3 requests
        for _ in range(3):
            self.assertTrue(budget.can_make_request())
            budget.track_request(100)

        # 4th request should be denied
        self.assertFalse(budget.can_make_request())

    def test_budget_reset_after_hour(self):
        """Test: Budget resets after 1 hour"""
        budget = LLMBudget(max_tokens_per_hour=1000)

        # Track a request
        budget.track_request(500)
        self.assertEqual(budget.tokens_used, 500)

        # Simulate 1 hour passing
        budget.period_start = time.time() - 3601

        # Reset should trigger
        budget.reset_if_needed()

        self.assertEqual(budget.tokens_used, 0)
        self.assertEqual(budget.requests_made, 0)


class TestLLMRequest(unittest.TestCase):
    """Test request model"""

    def test_request_creation(self):
        """Test: Request creates with defaults"""
        request = LLMRequest(prompt="Test prompt")

        self.assertEqual(request.prompt, "Test prompt")
        self.assertEqual(request.max_tokens, 4096)
        self.assertEqual(request.temperature, 0.7)
        self.assertIsNone(request.schema)
        self.assertIsNone(request.system_prompt)

    def test_request_with_schema(self):
        """Test: Request accepts JSON schema"""
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
        request = LLMRequest(prompt="Test", schema=schema)

        self.assertEqual(request.schema, schema)


class TestAdapterFactory(unittest.TestCase):
    """Test adapter factory"""

    def test_factory_ollama_stub(self):
        """Test: Factory creates Ollama stub"""
        adapter = create_adapter(provider="ollama")

        self.assertEqual(adapter.provider_name, "ollama")
        self.assertEqual(adapter.model, "llama3.2")

    def test_factory_unknown_provider(self):
        """Test: Factory raises error for unknown provider"""
        with self.assertRaises(ValueError):
            create_adapter(provider="unknown")


class TestOllamaStub(unittest.TestCase):
    """Test Ollama stub implementation"""

    def test_ollama_generate_not_implemented(self):
        """Test: Ollama generate raises NotImplementedProviderError"""
        adapter = create_adapter(provider="ollama")
        request = LLMRequest(prompt="Test")

        with self.assertRaises(NotImplementedProviderError) as ctx:
            adapter.generate(request)

        # Check error message contains helpful info
        self.assertIn("501 NOT IMPLEMENTED", str(ctx.exception))
        self.assertIn("Use provider='claude'", str(ctx.exception))

    def test_ollama_stream_not_implemented(self):
        """Test: Ollama stream raises NotImplementedProviderError"""
        adapter = create_adapter(provider="ollama")
        request = LLMRequest(prompt="Test")

        with self.assertRaises(NotImplementedProviderError):
            list(adapter.stream(request))


class TestPHIRedaction(unittest.TestCase):
    """Test PHI redaction"""

    def test_redact_email(self):
        """Test: Email addresses are redacted"""
        adapter = create_adapter(provider="ollama")

        text = "Contact me at john@example.com for details"
        redacted = adapter.redact_phi(text)

        self.assertIn("[EMAIL]", redacted)
        self.assertNotIn("john@example.com", redacted)

    def test_redact_phone(self):
        """Test: Phone numbers are redacted"""
        adapter = create_adapter(provider="ollama")

        text = "Call me at 555-123-4567"
        redacted = adapter.redact_phi(text)

        self.assertIn("[PHONE]", redacted)
        self.assertNotIn("555-123-4567", redacted)

    def test_redact_ssn(self):
        """Test: SSN patterns are redacted"""
        adapter = create_adapter(provider="ollama")

        text = "SSN: 123-45-6789"
        redacted = adapter.redact_phi(text)

        self.assertIn("[SSN]", redacted)
        self.assertNotIn("123-45-6789", redacted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
