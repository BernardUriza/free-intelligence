"""
Security-focused tests for PolicyEnforcer allowlist validation.

Tests egress allowlist cannot be bypassed by attacker-controlled input.

File: tests/test_policy_enforcement_security.py
Created: 2025-10-30
Reference: Peer Review Report 2025-10-30 (Critical Finding #2)
"""

import pytest

from backend.policy_enforcer import PolicyEnforcer, PolicyViolation


@pytest.fixture
def enforcer_with_allowlist():
    """Create PolicyEnforcer with test allowlist"""
    # Create temp policy dict (bypass file loading)
    enforcer = PolicyEnforcer.__new__(PolicyEnforcer)
    enforcer.policy = {
        "sovereignty": {
            "egress": {
                "default": "deny",
                "allowlist": [
                    "api.anthropic.com",
                    "127.0.0.1:11434",
                    "localhost:11434",
                    ".example.com",  # Wildcard test
                ],
            }
        }
    }
    return enforcer


class TestAllowlistSecurityBypass:
    """Test allowlist cannot be bypassed by attacker-controlled input"""

    def test_egress_exact_host_allowed(self, enforcer_with_allowlist) -> None:
        """Exact host match should be allowed"""
        # Should NOT raise PolicyViolation
        enforcer_with_allowlist.check_egress("https://api.anthropic.com/v1/messages")
        enforcer_with_allowlist.check_egress("http://127.0.0.1:11434/api/chat")
        enforcer_with_allowlist.check_egress("http://localhost:11434/api/generate")

    def test_egress_exact_host_port_required(self, enforcer_with_allowlist) -> None:
        """Port must match exactly if specified in allowlist"""
        # Allowed: exact port match
        enforcer_with_allowlist.check_egress("http://127.0.0.1:11434/api/chat")

        # Blocked: different port
        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("http://127.0.0.1:11435/api/chat")

        # Blocked: no port specified when allowlist requires port
        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("http://127.0.0.1/api/chat")

    def test_egress_wildcard_subdomain_allowed(self, enforcer_with_allowlist) -> None:
        """Wildcard .example.com should match subdomains"""
        # Should allow subdomains
        enforcer_with_allowlist.check_egress("https://api.example.com/v1")
        enforcer_with_allowlist.check_egress("https://www.example.com/")
        enforcer_with_allowlist.check_egress("https://subdomain.example.com/path")

        # Should also allow bare domain
        enforcer_with_allowlist.check_egress("https://example.com/")

    def test_egress_substring_injection_blocked(self, enforcer_with_allowlist) -> None:
        """Attacker cannot bypass allowlist by embedding domain in URL"""
        # Attack: Query param injection
        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("https://evil.com/?redirect=api.anthropic.com")

        # Attack: Path injection
        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress(
                "https://malicious.com/api.anthropic.com/v1/messages"
            )

        # Attack: Fragment injection
        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("https://evil.com/steal#api.anthropic.com")

    def test_egress_subdomain_injection_blocked(self, enforcer_with_allowlist) -> None:
        """Allowlist domain should not match malicious subdomains"""
        # Attack: Add allowlisted domain as subdomain of evil domain
        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("https://api.anthropic.com.evil.com/steal")

        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("https://api.anthropic.com-evil.com/phishing")

    def test_egress_partial_domain_match_blocked(self, enforcer_with_allowlist) -> None:
        """Allowlist entry should not match partial strings"""
        # Attack: Embed allowlisted string in different host
        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("http://malicious-127.0.0.1:11434.evil.com")

        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("http://prefix127.0.0.1:11434/api")

    def test_egress_case_sensitivity_normalized(self, enforcer_with_allowlist) -> None:
        """Allowlist matching should be case-insensitive"""
        # Lowercase (original)
        enforcer_with_allowlist.check_egress("https://api.anthropic.com")

        # Uppercase variants should also work
        enforcer_with_allowlist.check_egress("https://API.ANTHROPIC.COM")
        enforcer_with_allowlist.check_egress("https://Api.Anthropic.Com")
        enforcer_with_allowlist.check_egress("HTTPS://API.ANTHROPIC.COM/V1/MESSAGES")

    def test_egress_wildcard_does_not_match_unrelated(self, enforcer_with_allowlist) -> None:
        """Wildcard .example.com should not match unrelated domains"""
        # Should NOT match: different domain
        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("https://example.org/")

        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("https://notexample.com/")

        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer_with_allowlist.check_egress("https://evil-example.com/")

    def test_egress_empty_allowlist_blocks_all(self) -> None:
        """Empty allowlist should block all requests"""
        enforcer = PolicyEnforcer.__new__(PolicyEnforcer)
        enforcer.policy = {"sovereignty": {"egress": {"default": "deny", "allowlist": []}}}

        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer.check_egress("https://api.anthropic.com")

        with pytest.raises(PolicyViolation, match="External egress denied"):
            enforcer.check_egress("http://localhost:11434")


@pytest.mark.skip(reason="Requires pytest-benchmark: pip install pytest-benchmark")
class TestAllowlistPerformance:
    """Test allowlist check performance (should be <100μs)"""

    def test_allowlist_check_performance(self, enforcer_with_allowlist, benchmark) -> None:
        """Allowlist check should complete in <100μs"""

        def check_allowed_url():
            enforcer_with_allowlist.check_egress("https://api.anthropic.com/v1/messages")

        # Run benchmark
        result = benchmark(check_allowed_url)

        # Assert performance: median should be <100μs (0.0001s)
        assert (
            result.stats.median < 0.0001
        ), f"Allowlist check too slow: {result.stats.median*1000:.2f}ms"


# Run tests:
# python3 -m pytest tests/test_policy_enforcement_security.py -v
# python3 -m pytest tests/test_policy_enforcement_security.py -v --benchmark-only
