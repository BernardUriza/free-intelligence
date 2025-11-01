"""
Free Intelligence - IP Validator

CIDR-based IP validation for LAN-only access control.

File: backend/security/ip_validator.py
Created: 2025-10-29
Card: FI-SEC-FEAT-002

Philosophy:
- Confianza ≠ opinión; es topología (CIDR)
- Default-deny, allowlist explícita
- Transparencia: logs de todas las denegaciones
"""

import ipaddress
from typing import Optional


class IPValidator:
    """
    IP address validator using CIDR allowlists.

    Default allowlist:
    - 127.0.0.1/8 (localhost IPv4)
    - ::1 (localhost IPv6)
    - 10.0.0.0/8 (private class A)
    - 172.16.0.0/12 (private class B)
    - 192.168.0.0/16 (private class C)
    """

    DEFAULT_ALLOWED_CIDRS = [
        "127.0.0.1/8",  # Localhost
        "::1/128",  # IPv6 localhost
        "10.0.0.0/8",  # Private A
        "172.16.0.0/12",  # Private B
        "192.168.0.0/16",  # Private C
    ]

    def __init__(self, allowed_cidrs: Optional[list[str]] = None):
        """
        Initialize IP validator with CIDR allowlist.

        Args:
            allowed_cidrs: List of CIDR ranges (default: private ranges + localhost)
        """
        cidrs = allowed_cidrs or self.DEFAULT_ALLOWED_CIDRS
        self.allowed_networks = [ipaddress.ip_network(cidr, strict=False) for cidr in cidrs]

    def is_allowed(self, ip_address: str) -> bool:
        """
        Check if IP address is in allowlist.

        Args:
            ip_address: IP address to check (IPv4 or IPv6)

        Returns:
            True if allowed, False otherwise
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            return any(ip in network for network in self.allowed_networks)
        except ValueError:
            # Invalid IP format
            return False

    def get_client_ip(
        self,
        remote_addr: str,
        x_forwarded_for: Optional[str] = None,
        trusted_proxies: Optional[list[str]] = None,
    ) -> str:
        """
        Extract real client IP from request.

        Args:
            remote_addr: Direct connection IP (REMOTE_ADDR)
            x_forwarded_for: X-Forwarded-For header value
            trusted_proxies: List of trusted proxy IPs (default: localhost only)

        Returns:
            Real client IP address
        """
        # Default: trust only localhost as proxy
        if trusted_proxies is None:
            trusted_proxies = ["127.0.0.1", "::1"]

        # If no proxy or proxy not trusted, use remote_addr
        if not x_forwarded_for or remote_addr not in trusted_proxies:
            return remote_addr

        # Parse X-Forwarded-For (format: "client, proxy1, proxy2")
        forwarded_ips = [ip.strip() for ip in x_forwarded_for.split(",")]

        # Return leftmost IP (original client)
        return forwarded_ips[0] if forwarded_ips else remote_addr
