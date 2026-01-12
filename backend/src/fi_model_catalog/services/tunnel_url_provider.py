"""
Tunnel URL Provider - Reads Cloudflare tunnel URL from Azure Blob Storage.

fi-monitor uploads the tunnel URL to Azure blob when it starts cloudflared.
This provider reads that URL so the cloud backend can reach the local Ollama.

Features:
- Caches URL with configurable TTL
- Validates tunnel freshness (stale URLs are rejected)
- Health check to verify tunnel connectivity
- Multiple fallback strategies
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Maximum age of tunnel URL before considered stale (10 minutes)
MAX_TUNNEL_AGE_MINUTES = 10


class TunnelURLProvider:
    """
    Provides the current Cloudflare tunnel URL for reaching local Ollama.
    
    Reads from Azure Blob Storage:
    - Container: fi-tunnels
    - Blob: tunnel-url.json
    
    Features:
    - Caches the URL for 60 seconds to avoid excessive Azure calls
    - Validates that the tunnel URL is not stale (updated within 10 minutes)
    - Health check before returning URL
    - Circuit breaker for failed Azure calls
    """

    def __init__(
        self,
        blob_url: str | None = None,
        cache_ttl_seconds: int = 60,
        fallback_url: str = "http://localhost:11434",
        max_tunnel_age_minutes: int = MAX_TUNNEL_AGE_MINUTES,
        verify_tunnel_health: bool = False,
    ):
        """
        Initialize the tunnel URL provider.
        
        Args:
            blob_url: Full URL to the Azure blob (with or without SAS token).
                     If not provided, reads from FI_TUNNEL_BLOB_URL env var.
            cache_ttl_seconds: How long to cache the URL before refreshing.
            fallback_url: URL to use if Azure blob is unavailable.
            max_tunnel_age_minutes: Maximum age of tunnel URL before considered stale.
            verify_tunnel_health: If True, verify tunnel is reachable before returning.
        """
        self._blob_url = blob_url or os.getenv(
            "FI_TUNNEL_BLOB_URL",
            "https://aurityreleases.blob.core.windows.net/fi-tunnels/tunnel-url.json"
        )
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._fallback_url = fallback_url
        self._max_tunnel_age = timedelta(minutes=max_tunnel_age_minutes)
        self._verify_health = verify_tunnel_health
        
        # Cache state
        self._cached_url: str | None = None
        self._cached_data: dict[str, Any] | None = None
        self._cache_expires_at: datetime | None = None
        self._lock = asyncio.Lock()
        
        # Circuit breaker for Azure failures
        self._consecutive_failures = 0
        self._circuit_open_until: datetime | None = None
        self._max_failures_before_open = 3
        self._circuit_reset_seconds = 60

    async def get_ollama_url(self) -> str:
        """
        Get the current Ollama URL (tunnel or fallback).
        
        Returns:
            The tunnel URL if available and fresh, otherwise the fallback URL.
        """
        # Check cache first
        if self._is_cache_valid():
            return self._cached_url or self._fallback_url
        
        async with self._lock:
            # Double-check after acquiring lock
            if self._is_cache_valid():
                return self._cached_url or self._fallback_url
            
            # Check circuit breaker
            if self._is_circuit_open():
                logger.debug("tunnel_provider_circuit_open", fallback=self._fallback_url)
                return self._fallback_url
            
            # Fetch from Azure
            try:
                tunnel_data = await self._fetch_tunnel_data()
                if tunnel_data and "tunnel_url" in tunnel_data:
                    # Validate freshness
                    if not self._is_tunnel_fresh(tunnel_data):
                        logger.warning(
                            "tunnel_url_stale",
                            updated_at=tunnel_data.get("updated_at"),
                            max_age_minutes=self._max_tunnel_age.total_seconds() / 60,
                        )
                        self._reset_circuit_breaker()
                        return self._fallback_url
                    
                    self._cached_url = tunnel_data["tunnel_url"]
                    self._cached_data = tunnel_data
                    self._cache_expires_at = datetime.now(timezone.utc) + self._cache_ttl
                    self._reset_circuit_breaker()
                    
                    # Optional health check
                    if self._verify_health:
                        if not await self._check_tunnel_health(self._cached_url):
                            logger.warning("tunnel_health_check_failed", url=self._cached_url)
                            return self._fallback_url
                    
                    logger.info(
                        "tunnel_url_updated",
                        tunnel_url=self._cached_url,
                        hostname=tunnel_data.get("hostname"),
                        updated_at=tunnel_data.get("updated_at"),
                    )
                    return self._cached_url
                    
            except Exception as e:
                self._record_failure()
                logger.warning(
                    "tunnel_url_fetch_failed",
                    error=str(e),
                    consecutive_failures=self._consecutive_failures,
                    fallback_url=self._fallback_url,
                )
        
        return self._fallback_url

    async def get_tunnel_info(self) -> dict[str, Any] | None:
        """
        Get full tunnel information including hostname and timestamp.
        
        Returns:
            Dict with tunnel_url, hostname, updated_at, or None if unavailable.
        """
        await self.get_ollama_url()  # Ensure cache is populated
        return self._cached_data

    async def is_tunnel_available(self) -> bool:
        """Check if a valid tunnel URL is currently available."""
        url = await self.get_ollama_url()
        return url != self._fallback_url

    def _is_cache_valid(self) -> bool:
        """Check if the cached URL is still valid."""
        if self._cached_url is None or self._cache_expires_at is None:
            return False
        return datetime.now(timezone.utc) < self._cache_expires_at

    def _is_tunnel_fresh(self, tunnel_data: dict[str, Any]) -> bool:
        """Check if the tunnel URL was updated recently enough."""
        updated_at_str = tunnel_data.get("updated_at")
        if not updated_at_str:
            return False
        
        try:
            # Parse ISO 8601 timestamp
            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - updated_at
            return age < self._max_tunnel_age
        except (ValueError, TypeError):
            logger.warning("tunnel_timestamp_parse_error", timestamp=updated_at_str)
            return False

    async def _check_tunnel_health(self, url: str) -> bool:
        """Verify the tunnel is reachable by checking Ollama's tags endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/api/tags", timeout=5.0)
                return response.status_code == 200
        except Exception:
            return False

    def _is_circuit_open(self) -> bool:
        """Check if the circuit breaker is open (blocking requests)."""
        if self._circuit_open_until is None:
            return False
        if datetime.now(timezone.utc) >= self._circuit_open_until:
            # Reset circuit breaker
            self._circuit_open_until = None
            self._consecutive_failures = 0
            return False
        return True

    def _record_failure(self) -> None:
        """Record a failure and potentially open the circuit breaker."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._max_failures_before_open:
            self._circuit_open_until = datetime.now(timezone.utc) + timedelta(
                seconds=self._circuit_reset_seconds
            )
            logger.warning(
                "tunnel_provider_circuit_opened",
                failures=self._consecutive_failures,
                reset_in_seconds=self._circuit_reset_seconds,
            )

    def _reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker after a successful call."""
        self._consecutive_failures = 0
        self._circuit_open_until = None

    async def _fetch_tunnel_data(self) -> dict[str, Any] | None:
        """Fetch tunnel data from Azure blob with retry."""
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self._blob_url, timeout=10.0)
                    
                    if response.status_code == 404:
                        logger.debug("tunnel_blob_not_found")
                        return None
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.HTTPStatusError as e:
                logger.warning("tunnel_blob_http_error", status=e.response.status_code, attempt=attempt + 1)
                if attempt == max_retries - 1:
                    return None
            except Exception as e:
                logger.warning("tunnel_blob_fetch_error", error=str(e), attempt=attempt + 1)
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(0.5)  # Brief delay before retry
        
        return None

    def invalidate_cache(self) -> None:
        """Force a refresh on the next call."""
        self._cache_expires_at = None


# Singleton instance for app-wide use
_provider: TunnelURLProvider | None = None


def get_tunnel_url_provider() -> TunnelURLProvider:
    """Get the singleton TunnelURLProvider instance."""
    global _provider
    if _provider is None:
        _provider = TunnelURLProvider()
    return _provider


async def get_ollama_host() -> str:
    """
    Convenience function to get the Ollama host URL.
    
    This replaces the static os.getenv("OLLAMA_HOST", "http://localhost:11434")
    with a dynamic lookup from the Azure blob.
    """
    provider = get_tunnel_url_provider()
    return await provider.get_ollama_url()
