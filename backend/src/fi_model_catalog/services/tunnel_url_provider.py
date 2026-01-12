"""
Tunnel URL Provider - Reads Cloudflare tunnel URL from Azure Blob Storage.

fi-monitor uploads the tunnel URL to Azure blob when it starts cloudflared.
This provider reads that URL so the cloud backend can reach the local Ollama.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class TunnelURLProvider:
    """
    Provides the current Cloudflare tunnel URL for reaching local Ollama.
    
    Reads from Azure Blob Storage:
    - Container: fi-tunnels
    - Blob: tunnel-url.json
    
    Caches the URL for 60 seconds to avoid excessive Azure calls.
    """

    def __init__(
        self,
        blob_url: str | None = None,
        cache_ttl_seconds: int = 60,
        fallback_url: str = "http://localhost:11434",
    ):
        """
        Initialize the tunnel URL provider.
        
        Args:
            blob_url: Full URL to the Azure blob (with or without SAS token).
                     If not provided, reads from FI_TUNNEL_BLOB_URL env var.
            cache_ttl_seconds: How long to cache the URL before refreshing.
            fallback_url: URL to use if Azure blob is unavailable.
        """
        self._blob_url = blob_url or os.getenv(
            "FI_TUNNEL_BLOB_URL",
            "https://aurityreleases.blob.core.windows.net/fi-tunnels/tunnel-url.json"
        )
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._fallback_url = fallback_url
        
        # Cache state
        self._cached_url: str | None = None
        self._cached_data: dict[str, Any] | None = None
        self._cache_expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_ollama_url(self) -> str:
        """
        Get the current Ollama URL (tunnel or fallback).
        
        Returns:
            The tunnel URL if available, otherwise the fallback URL.
        """
        # Check cache first
        if self._is_cache_valid():
            return self._cached_url or self._fallback_url
        
        async with self._lock:
            # Double-check after acquiring lock
            if self._is_cache_valid():
                return self._cached_url or self._fallback_url
            
            # Fetch from Azure
            try:
                tunnel_data = await self._fetch_tunnel_data()
                if tunnel_data and "tunnel_url" in tunnel_data:
                    self._cached_url = tunnel_data["tunnel_url"]
                    self._cached_data = tunnel_data
                    self._cache_expires_at = datetime.utcnow() + self._cache_ttl
                    
                    logger.info(
                        "tunnel_url_updated",
                        tunnel_url=self._cached_url,
                        hostname=tunnel_data.get("hostname"),
                        updated_at=tunnel_data.get("updated_at"),
                    )
                    return self._cached_url
            except Exception as e:
                logger.warning(
                    "tunnel_url_fetch_failed",
                    error=str(e),
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

    def _is_cache_valid(self) -> bool:
        """Check if the cached URL is still valid."""
        if self._cached_url is None or self._cache_expires_at is None:
            return False
        return datetime.utcnow() < self._cache_expires_at

    async def _fetch_tunnel_data(self) -> dict[str, Any] | None:
        """Fetch tunnel data from Azure blob."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self._blob_url, timeout=10.0)
                
                if response.status_code == 404:
                    logger.debug("tunnel_blob_not_found")
                    return None
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.warning("tunnel_blob_http_error", status=e.response.status_code)
            return None
        except Exception as e:
            logger.warning("tunnel_blob_fetch_error", error=str(e))
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
