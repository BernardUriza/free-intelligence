from __future__ import annotations

"""
Free Intelligence - LAN Guard Middleware

FastAPI middleware for LAN-only access enforcement.

File: backend/security/lan_guard.py
Created: 2025-10-29
Card: FI-SEC-FEAT-002

Philosophy:
- Default-deny: toda petición fuera de allowlist → 403
- Sampling logs: 1/50 para evitar ruido
- Métricas: block_count, allow_count
"""

import os
import random
from collections.abc import Callable
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.logger import get_logger
from backend.security.ip_validator import IPValidator

logger = get_logger(__name__)


class LANGuardMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce LAN-only access.

    Blocks all requests from IPs outside configured CIDR ranges.
    """

    def __init__(self, app, allowed_cidrs: list[Optional[str]] = None, sample_rate: float = 0.02):
        """
        Initialize LAN guard middleware.

        Args:
            app: FastAPI application
            allowed_cidrs: List of allowed CIDR ranges (default: private + localhost)
            sample_rate: Log sampling rate for blocked requests (default: 0.02 = 1/50)
        """
        super().__init__(app)
        self.validator = IPValidator(allowed_cidrs)
        self.sample_rate = sample_rate

        # Metrics
        self.block_count = 0
        self.allow_count = 0

        # Trusted proxies (from env)
        trusted_str = os.getenv("FI_TRUSTED_PROXIES", "127.0.0.1,::1")
        self.trusted_proxies = [ip.strip() for ip in trusted_str.split(",")]

        # Exclude paths (health check only if from LAN)
        self.exclude_paths = set()

        logger.info(
            "LAN_GUARD_INITIALIZED",
            allowed_networks=len(self.validator.allowed_networks),
            trusted_proxies=self.trusted_proxies,
            sample_rate=self.sample_rate,
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and enforce LAN-only access.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response (403 if blocked, normal response if allowed)
        """
        # Skip excluded paths (if any)
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Extract real client IP
        remote_addr = request.client.host if request.client else "unknown"
        x_forwarded_for = request.headers.get("X-Forwarded-For")

        client_ip = self.validator.get_client_ip(
            remote_addr=remote_addr,
            x_forwarded_for=x_forwarded_for,
            trusted_proxies=self.trusted_proxies,
        )

        # Check if IP is allowed
        if self.validator.is_allowed(client_ip):
            self.allow_count += 1
            return await call_next(request)

        # Block request
        self.block_count += 1

        # Sample logging (1/50 by default)
        if random.random() < self.sample_rate:
            logger.warning(
                "LAN_GUARD_BLOCK",
                client_ip=client_ip,
                remote_addr=remote_addr,
                x_forwarded_for=x_forwarded_for,
                path=request.url.path,
                method=request.method,
                user_agent=request.headers.get("User-Agent", "unknown"),
                block_count=self.block_count,
            )

        # Return 403 Forbidden
        return JSONResponse(
            status_code=403,
            content={
                "error": "lan_only",
                "message": "Access restricted to local network",
                "allowed_networks": [
                    "127.0.0.0/8",
                    "::1",
                    "10.0.0.0/8",
                    "172.16.0.0/12",
                    "192.168.0.0/16",
                ],
            },
        )

    def get_metrics(self) -> dict:
        """
        Get security metrics.

        Returns:
            Dictionary with block/allow counts
        """
        return {
            "lan_guard.block_count": self.block_count,
            "lan_guard.allow_count": self.allow_count,
            "lan_guard.total_requests": self.block_count + self.allow_count,
            "lan_guard.block_rate": (
                self.block_count / (self.block_count + self.allow_count)
                if (self.block_count + self.allow_count) > 0
                else 0.0
            ),
        }
