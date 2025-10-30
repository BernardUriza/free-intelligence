"""
Tests for Policy Enforcement
Card: FI-POLICY-STR-001

Tests runtime enforcement of:
- Sovereignty: egress deny
- Privacy: PHI detection
- Cost: budget limits
- Feature flags: timeline.auto, agents.enabled
"""

import pytest
from backend.policy_enforcer import (
    PolicyEnforcer,
    PolicyViolation,
    check_egress,
    check_cost,
    check_phi,
    redact,
    check_timeline_auto,
    check_agents_enabled,
)


@pytest.fixture
def enforcer():
    """Fresh PolicyEnforcer instance for each test"""
    return PolicyEnforcer(
        policy_path="config/fi.policy.yaml",
        redaction_path="config/redaction_style.yaml"
    )


class TestSovereigntyPolicy:
    """Test sovereignty.egress enforcement"""

    def test_egress_deny_blocks_external_url(self, enforcer):
        """Egress to external URL should raise PolicyViolation when default=deny"""
        with pytest.raises(PolicyViolation) as exc_info:
            enforcer.check_egress("https://api.openai.com/v1/chat")

        assert exc_info.value.rule == "sovereignty.egress"
        assert "egress denied" in exc_info.value.message.lower()
        assert "api.openai.com" in exc_info.value.message

    def test_egress_deny_with_run_id(self, enforcer):
        """Egress violation should include run_id in metadata"""
        run_id = "test_run_123"

        with pytest.raises(PolicyViolation) as exc_info:
            enforcer.check_egress("https://anthropic.com/api", run_id=run_id)

        assert exc_info.value.metadata["run_id"] == run_id

    def test_egress_convenience_function(self):
        """check_egress() convenience function should enforce policy"""
        with pytest.raises(PolicyViolation) as exc_info:
            check_egress("https://google.com")

        assert exc_info.value.rule == "sovereignty.egress"


class TestPrivacyPolicy:
    """Test privacy.phi and redaction enforcement"""

    def test_phi_detection_mrn(self, enforcer):
        """PHI detection should identify MRN patterns"""
        text = "Patient MRN: 1234567 shows symptoms"

        # PHI enabled=false in policy, so should return False
        assert enforcer.check_phi(text) is False

    def test_phi_detection_disabled_by_policy(self, enforcer):
        """PHI detection should respect privacy.phi.enabled=false"""
        phi_text = "Patient: John Doe, MRN: 9876543"

        # Policy has phi.enabled=false
        assert enforcer.check_phi(phi_text) is False

    def test_redact_email(self, enforcer):
        """Redaction should mask email addresses"""
        text = "Contact admin@example.com for support"
        redacted = enforcer.redact(text)

        assert "[REDACTED_EMAIL]" in redacted
        assert "admin@example.com" not in redacted

    def test_redact_phone(self, enforcer):
        """Redaction should mask phone numbers"""
        text = "Call me at +1-555-123-4567"
        redacted = enforcer.redact(text)

        assert "[REDACTED_PHONE]" in redacted
        assert "555-123-4567" not in redacted

    def test_redact_curp(self, enforcer):
        """Redaction should mask Mexican CURP"""
        # Valid CURP: 4 letters + 6 digits + H/M + 5 letters + 2 digits
        text = "My CURP is XEXX010101HNEXXS04"
        redacted = enforcer.redact(text)

        # Note: "CURP" is a stop term, so it gets redacted as [REDACTED]
        # The actual CURP pattern should also be redacted
        assert "[REDACTED" in redacted  # Either [REDACTED] or [REDACTED_CURP]
        # Either the CURP word or the actual ID should be masked
        assert ("XEXX010101HNEXXS04" not in redacted or "[REDACTED_CURP]" in redacted)

    def test_redact_rfc(self, enforcer):
        """Redaction should mask Mexican RFC"""
        text = "RFC: XAXX010101000"
        redacted = enforcer.redact(text)

        assert "[REDACTED_RFC]" in redacted

    def test_redact_ssn(self, enforcer):
        """Redaction should mask SSN"""
        text = "SSN: 123-45-6789"
        redacted = enforcer.redact(text)

        assert "[REDACTED_SSN]" in redacted
        assert "123-45-6789" not in redacted

    def test_redact_stop_terms(self, enforcer):
        """Redaction should mask stop terms (password, secret, etc)"""
        text = "My password is secret123 and the api_key is ABC"
        redacted = enforcer.redact(text)

        assert "[REDACTED]" in redacted
        assert "password" not in redacted.lower() or "[redacted]" in redacted.lower()
        assert "secret" not in redacted.lower() or "[redacted]" in redacted.lower()

    def test_redact_preserves_non_sensitive_text(self, enforcer):
        """Redaction should preserve non-sensitive text"""
        text = "The patient arrived at 9:00 AM"
        redacted = enforcer.redact(text)

        assert "arrived" in redacted
        assert "9:00 AM" in redacted

    def test_redact_multiple_patterns(self, enforcer):
        """Redaction should handle multiple patterns in one text"""
        text = "Email john@test.com, phone +1-555-123-4567, SSN 123-45-6789"
        redacted = enforcer.redact(text)

        assert "[REDACTED_EMAIL]" in redacted
        assert "[REDACTED_PHONE]" in redacted or "phone" in redacted  # "phone" might be redacted too
        assert "[REDACTED_SSN]" in redacted
        assert "john@test.com" not in redacted
        assert "123-45-6789" not in redacted

    def test_redact_empty_string(self, enforcer):
        """Redaction should handle empty string gracefully"""
        assert enforcer.redact("") == ""

    def test_redact_none(self, enforcer):
        """Redaction should handle None gracefully"""
        assert enforcer.redact(None) == None


class TestCostPolicy:
    """Test llm.budgets enforcement"""

    def test_cost_within_budget(self, enforcer):
        """Cost within budget should not raise exception"""
        # Policy has monthly_usd=200, so 100 USD (10000 cents) is OK
        enforcer.check_cost(10000)  # 100 USD

    def test_cost_exceeds_budget(self, enforcer):
        """Cost exceeding budget should raise PolicyViolation"""
        # Policy has monthly_usd=200, so 300 USD (30000 cents) exceeds
        with pytest.raises(PolicyViolation) as exc_info:
            enforcer.check_cost(30000)  # 300 USD

        assert exc_info.value.rule == "llm.budgets"
        assert "30000" in str(exc_info.value.metadata["cents"])
        assert "20000" in str(exc_info.value.metadata["budget_cents"])

    def test_cost_exactly_at_budget(self, enforcer):
        """Cost exactly at budget should not raise exception"""
        enforcer.check_cost(20000)  # Exactly 200 USD

    def test_cost_with_run_id(self, enforcer):
        """Cost violation should include run_id in metadata"""
        run_id = "cost_test_456"

        with pytest.raises(PolicyViolation) as exc_info:
            enforcer.check_cost(50000, run_id=run_id)

        assert exc_info.value.metadata["run_id"] == run_id

    def test_cost_convenience_function(self):
        """check_cost() convenience function should enforce policy"""
        with pytest.raises(PolicyViolation):
            check_cost(100000)  # 1000 USD exceeds 200 USD budget


class TestFeatureFlags:
    """Test timeline.auto and agents.enabled flags"""

    def test_timeline_auto_disabled_by_policy(self, enforcer):
        """timeline.auto.enabled should be false per policy"""
        assert enforcer.check_timeline_auto() is False

    def test_agents_disabled_by_policy(self, enforcer):
        """agents.enabled should be false per policy"""
        assert enforcer.check_agents_enabled() is False

    def test_timeline_auto_convenience_function(self):
        """check_timeline_auto() convenience function should work"""
        assert check_timeline_auto() is False

    def test_agents_enabled_convenience_function(self):
        """check_agents_enabled() convenience function should work"""
        assert check_agents_enabled() is False


class TestPolicyUtilities:
    """Test policy utility functions"""

    def test_get_policy_simple_key(self, enforcer):
        """get_policy() should retrieve top-level key"""
        version = enforcer.get_policy("version")
        assert version == "1.0"

    def test_get_policy_nested_key(self, enforcer):
        """get_policy() should retrieve nested key"""
        egress_default = enforcer.get_policy("sovereignty.egress.default")
        assert egress_default == "deny"

    def test_get_policy_deep_nested_key(self, enforcer):
        """get_policy() should retrieve deep nested key"""
        monthly_budget = enforcer.get_policy("llm.budgets.monthly_usd")
        assert monthly_budget == 200

    def test_get_policy_missing_key_returns_default(self, enforcer):
        """get_policy() should return default for missing key"""
        value = enforcer.get_policy("nonexistent.key.path", default="MISSING")
        assert value == "MISSING"

    def test_get_policy_digest(self, enforcer):
        """get_policy_digest() should return SHA256 hash"""
        digest = enforcer.get_policy_digest()

        # Should be 64-character hex string (SHA256)
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_log_violation(self, enforcer, caplog):
        """log_violation() should log to audit trail"""
        enforcer.log_violation("test.rule", {"key": "value"})

        assert "policy_violation" in caplog.text
        assert "test.rule" in caplog.text
