"""
Integration tests for PolicyEnforcer in LLM providers.

Tests:
- PolicyEnforcer initialization and integration
- Redaction functionality
- Policy violation handling
- Provider imports

Card: FI-POLICY-STR-001
Created: 2025-10-30
"""

import pytest

from backend.policy_enforcer import PolicyViolation, get_policy_enforcer, redact


class TestPolicyEnforcerIntegration:
    """Test policy enforcer integration and initialization."""

    def test_policy_enforcer_singleton(self):
        """Test that get_policy_enforcer returns same instance."""
        policy1 = get_policy_enforcer()
        policy2 = get_policy_enforcer()
        assert policy1 is policy2

    def test_policy_enforcer_has_required_methods(self):
        """Test that PolicyEnforcer has all required methods."""
        policy = get_policy_enforcer()
        assert hasattr(policy, "check_egress")
        assert hasattr(policy, "check_cost")
        assert hasattr(policy, "check_phi")
        assert callable(policy.check_egress)
        assert callable(policy.check_cost)
        assert callable(policy.check_phi)

    def test_redact_function_exists(self):
        """Test that redact function is available."""
        assert callable(redact)
        # Test basic redaction
        text = "Contact me at test@example.com"
        redacted = redact(text)
        assert "[REDACTED" in redacted


class TestRedactionFunctionality:
    """Test redaction patterns work correctly."""

    def test_email_redaction(self):
        """Test email redaction."""
        text = "Contact: john.doe@example.com"
        redacted = redact(text)
        assert "john.doe@example.com" not in redacted
        assert "[REDACTED" in redacted

    def test_phone_redaction(self):
        """Test phone number redaction."""
        text = "Call me: +1-555-123-4567"
        redacted = redact(text)
        assert "+1-555-123-4567" not in redacted
        assert "[REDACTED" in redacted

    def test_multiple_pattern_redaction(self):
        """Test multiple patterns in same text."""
        text = "Email: test@test.com, Phone: +1-555-123-4567"
        redacted = redact(text)
        assert "test@test.com" not in redacted
        assert "+1-555-123-4567" not in redacted
        assert redacted.count("[REDACTED") >= 2

    def test_preserve_non_sensitive_text(self):
        """Test that non-sensitive text is preserved."""
        text = "This is a normal sentence with no PII."
        redacted = redact(text)
        assert redacted == text  # Should be unchanged

    def test_redaction_with_stop_terms(self):
        """Test redaction of stop terms (password, token, etc)."""
        text = "My password is secret123"
        redacted = redact(text)
        # Stop terms like 'password' trigger redaction
        assert "password" not in redacted.lower() or "[REDACTED" in redacted


class TestEgressPolicyCheck:
    """Test egress policy checking."""

    def test_egress_check_blocks_external_url(self):
        """Test that external URLs are blocked when policy=deny."""
        policy = get_policy_enforcer()

        # Check policy setting
        egress_policy = policy.policy.get("sovereignty", {}).get("egress", {}).get("default")

        if egress_policy == "deny":
            # Should raise PolicyViolation for external URL
            with pytest.raises(PolicyViolation) as exc_info:
                policy.check_egress("https://api.anthropic.com")
            assert "denied by policy" in str(exc_info.value)
        else:
            # If policy allows, should not raise
            policy.check_egress("https://api.anthropic.com")  # Should pass

    def test_egress_check_allows_local_url(self):
        """Test that local URLs pass egress check."""
        policy = get_policy_enforcer()

        # Local URLs should always pass (or be handled based on policy)
        try:
            policy.check_egress("http://127.0.0.1:11434/api/generate")
            # If no exception, test passes
        except PolicyViolation:
            # If exception, check that it's intentional based on policy
            egress_policy = policy.policy.get("sovereignty", {}).get("egress", {}).get("default")
            assert egress_policy == "deny"  # Only fail if policy is deny


class TestCostPolicyCheck:
    """Test cost budget enforcement."""

    def test_cost_within_budget_passes(self):
        """Test that costs within budget pass check."""
        policy = get_policy_enforcer()

        # Get budget from policy
        budget_usd = policy.policy.get("llm", {}).get("budgets", {}).get("monthly_usd", 0)
        budget_cents = budget_usd * 100

        # Cost below budget should pass
        if budget_cents > 100:
            policy.check_cost(100)  # Should not raise

    def test_cost_exceeds_budget_raises(self):
        """Test that costs exceeding budget raise PolicyViolation."""
        policy = get_policy_enforcer()

        # Get budget from policy
        budget_usd = policy.policy.get("llm", {}).get("budgets", {}).get("monthly_usd", 0)
        budget_cents = budget_usd * 100

        # Cost above budget should raise
        with pytest.raises(PolicyViolation) as exc_info:
            policy.check_cost(budget_cents + 1000)
        assert "exceeds monthly budget" in str(exc_info.value)


class TestProvidersHavePolicyIntegration:
    """Test that providers have policy enforcement integrated."""

    def test_claude_adapter_imports_policy(self):
        """Test that Claude adapter imports PolicyEnforcer."""
        from backend.providers import claude

        assert hasattr(claude, "policy")
        assert hasattr(claude, "get_policy_enforcer")

    def test_ollama_adapter_imports_policy(self):
        """Test that Ollama adapter imports PolicyEnforcer."""
        from backend.providers import ollama

        assert hasattr(ollama, "policy")
        assert hasattr(ollama, "get_policy_enforcer")

    def test_llm_middleware_imports_policy(self):
        """Test that LLM middleware imports PolicyEnforcer."""
        from backend import llm_middleware

        assert hasattr(llm_middleware, "policy")
        assert hasattr(llm_middleware, "get_policy_enforcer")
        assert hasattr(llm_middleware, "redact")
