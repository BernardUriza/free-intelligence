"""
Test suite for LAN-only security.

File: tests/test_lan_security.py
Created: 2025-10-29
Card: FI-SEC-FEAT-002

Tests:
- IP validation (CIDR allowlisting)
- Client IP extraction (X-Forwarded-For handling)
- LAN guard middleware (allow/deny)
- Security metrics
"""


from backend.security.ip_validator import IPValidator


class TestIPValidator:
    """Test IP validation and CIDR checking."""

    def test_localhost_ipv4_allowed(self):
        """Test localhost IPv4 is allowed."""
        validator = IPValidator()
        assert validator.is_allowed("127.0.0.1")
        assert validator.is_allowed("127.1.2.3")  # All 127.x.x.x
        assert validator.is_allowed("127.255.255.255")

    def test_localhost_ipv6_allowed(self):
        """Test localhost IPv6 is allowed."""
        validator = IPValidator()
        assert validator.is_allowed("::1")

    def test_private_class_a_allowed(self):
        """Test private class A (10.x.x.x) is allowed."""
        validator = IPValidator()
        assert validator.is_allowed("10.0.0.1")
        assert validator.is_allowed("10.255.255.255")
        assert validator.is_allowed("10.123.45.67")

    def test_private_class_b_allowed(self):
        """Test private class B (172.16-31.x.x) is allowed."""
        validator = IPValidator()
        assert validator.is_allowed("172.16.0.1")
        assert validator.is_allowed("172.31.255.255")
        assert validator.is_allowed("172.20.10.5")

    def test_private_class_c_allowed(self):
        """Test private class C (192.168.x.x) is allowed."""
        validator = IPValidator()
        assert validator.is_allowed("192.168.1.1")
        assert validator.is_allowed("192.168.255.255")
        assert validator.is_allowed("192.168.0.100")

    def test_public_ip_denied(self):
        """Test public IPs are denied."""
        validator = IPValidator()
        # Google DNS
        assert not validator.is_allowed("8.8.8.8")
        assert not validator.is_allowed("8.8.4.4")
        # Cloudflare DNS
        assert not validator.is_allowed("1.1.1.1")
        assert not validator.is_allowed("1.0.0.1")
        # Random public IPs
        assert not validator.is_allowed("93.184.216.34")  # example.com
        assert not validator.is_allowed("142.250.80.46")  # google.com

    def test_invalid_ip_denied(self):
        """Test invalid IP formats are denied."""
        validator = IPValidator()
        assert not validator.is_allowed("not-an-ip")
        assert not validator.is_allowed("999.999.999.999")
        assert not validator.is_allowed("")
        assert not validator.is_allowed("localhost")  # Hostname not allowed

    def test_docker_bridge_allowed(self):
        """Test Docker bridge network (172.17.x.x) is allowed."""
        validator = IPValidator()
        assert validator.is_allowed("172.17.0.1")
        assert validator.is_allowed("172.18.0.2")

    def test_custom_cidrs(self):
        """Test custom CIDR allowlist."""
        validator = IPValidator(allowed_cidrs=["192.168.1.0/24"])
        # Allowed: 192.168.1.x
        assert validator.is_allowed("192.168.1.1")
        assert validator.is_allowed("192.168.1.255")
        # Denied: other subnets
        assert not validator.is_allowed("192.168.2.1")
        assert not validator.is_allowed("127.0.0.1")  # Even localhost!


class TestClientIPExtraction:
    """Test client IP extraction with proxy handling."""

    def test_no_proxy_uses_remote_addr(self):
        """Test direct connection uses REMOTE_ADDR."""
        validator = IPValidator()
        client_ip = validator.get_client_ip(
            remote_addr="192.168.1.100",
            x_forwarded_for=None,
        )
        assert client_ip == "192.168.1.100"

    def test_untrusted_proxy_ignored(self):
        """Test X-Forwarded-For from untrusted proxy is ignored."""
        validator = IPValidator()
        client_ip = validator.get_client_ip(
            remote_addr="8.8.8.8",  # Untrusted public IP
            x_forwarded_for="192.168.1.100",  # Claims to be LAN
        )
        # Should use remote_addr (untrusted proxy)
        assert client_ip == "8.8.8.8"

    def test_trusted_proxy_uses_forwarded(self):
        """Test X-Forwarded-For from trusted proxy is used."""
        validator = IPValidator()
        client_ip = validator.get_client_ip(
            remote_addr="127.0.0.1",  # Trusted localhost proxy
            x_forwarded_for="192.168.1.100, 127.0.0.1",
            trusted_proxies=["127.0.0.1"],
        )
        # Should extract leftmost IP (real client)
        assert client_ip == "192.168.1.100"

    def test_multiple_proxies_extracts_leftmost(self):
        """Test multiple proxies returns leftmost (original client)."""
        validator = IPValidator()
        client_ip = validator.get_client_ip(
            remote_addr="127.0.0.1",
            x_forwarded_for="10.0.0.50, 192.168.1.1, 127.0.0.1",
            trusted_proxies=["127.0.0.1"],
        )
        assert client_ip == "10.0.0.50"

    def test_empty_forwarded_falls_back(self):
        """Test empty X-Forwarded-For falls back to remote_addr."""
        validator = IPValidator()
        client_ip = validator.get_client_ip(
            remote_addr="127.0.0.1",
            x_forwarded_for="",
            trusted_proxies=["127.0.0.1"],
        )
        assert client_ip == "127.0.0.1"


class TestSecurityMetrics:
    """Test security metrics collection."""

    def test_metrics_initialization(self):
        """Test metrics start at zero."""
        from backend.security.lan_guard import LANGuardMiddleware

        # Create middleware without app (just for metrics)
        class FakeApp:
            pass

        middleware = LANGuardMiddleware(FakeApp())
        metrics = middleware.get_metrics()

        assert metrics["lan_guard.block_count"] == 0
        assert metrics["lan_guard.allow_count"] == 0
        assert metrics["lan_guard.total_requests"] == 0
        assert metrics["lan_guard.block_rate"] == 0.0

    def test_metrics_after_blocks(self):
        """Test metrics after blocking requests."""
        from backend.security.lan_guard import LANGuardMiddleware

        class FakeApp:
            pass

        middleware = LANGuardMiddleware(FakeApp())

        # Simulate blocks
        middleware.block_count = 5
        middleware.allow_count = 15

        metrics = middleware.get_metrics()

        assert metrics["lan_guard.block_count"] == 5
        assert metrics["lan_guard.allow_count"] == 15
        assert metrics["lan_guard.total_requests"] == 20
        assert metrics["lan_guard.block_rate"] == 0.25  # 5/20


class TestEdgeCases:
    """Test edge cases and security scenarios."""

    def test_ipv6_private_ranges(self):
        """Test IPv6 link-local and unique local addresses."""
        validator = IPValidator(
            allowed_cidrs=["::1/128", "fe80::/10", "fc00::/7"]  # Link-local, ULA
        )
        assert validator.is_allowed("::1")  # Localhost
        assert validator.is_allowed("fe80::1")  # Link-local
        assert validator.is_allowed("fc00::1")  # Unique local

    def test_spoofed_forwarded_header(self):
        """Test spoofed X-Forwarded-For is ignored from public IP."""
        validator = IPValidator()
        # Attacker from public IP spoofs X-Forwarded-For
        client_ip = validator.get_client_ip(
            remote_addr="93.184.216.34",  # Public IP
            x_forwarded_for="127.0.0.1",  # Spoofed
            trusted_proxies=["127.0.0.1"],
        )
        # Should use remote_addr (untrusted)
        assert client_ip == "93.184.216.34"
        assert not validator.is_allowed(client_ip)
