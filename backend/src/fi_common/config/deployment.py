"""
Deployment target configuration for FI-Cloud vs FI-Edge (Desktop).

This module provides a single source of truth for deployment-specific
configuration. The same codebase runs on both targets, differentiated
only by the DEPLOYMENT_TARGET environment variable.

Usage:
    from backend.src.fi_common.config.deployment import is_desktop, get_ollama_host

    if is_desktop():
        # Desktop-specific logic
        pass

Environment Variables:
    DEPLOYMENT_TARGET: "cloud" | "desktop" (default: "desktop")
    OLLAMA_HOST: Override Ollama endpoint (optional)
    DATA_DIR: Override data directory (optional)
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import TypedDict
from urllib.parse import urlparse

import httpx
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Config file for Ollama source selection
OLLAMA_SOURCE_CONFIG = Path.home() / ".aurity" / "ollama-source.json"


def _is_valid_ollama_url(url: str) -> bool:
    """Validate that URL is a proper HTTP(S) URL with host."""
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)  # Must have host
            and len(url) < 2048  # Sanity check
        )
    except Exception:
        return False


class OllamaHost(TypedDict):
    """Type-safe structure for Ollama host configuration (FI-BACKEND-FALLBACK-001)."""

    url: str
    name: str
    priority: int


class DeploymentTarget(Enum):
    """Deployment target environments."""

    CLOUD = "cloud"  # Production on Digital Ocean (app.aurity.io)
    DESKTOP = "desktop"  # Local installable app (FI-Edge)


def get_target() -> DeploymentTarget:
    """
    Get current deployment target from DEPLOYMENT_TARGET env var.

    Returns:
        DeploymentTarget.CLOUD for production server
        DeploymentTarget.DESKTOP for local development/desktop app
    """
    target = os.getenv("DEPLOYMENT_TARGET", "desktop").lower()
    if target == "cloud":
        return DeploymentTarget.CLOUD
    return DeploymentTarget.DESKTOP


def is_cloud() -> bool:
    """Check if running in cloud/production mode."""
    return get_target() == DeploymentTarget.CLOUD


def is_desktop() -> bool:
    """Check if running in desktop/local mode."""
    return get_target() == DeploymentTarget.DESKTOP


def get_data_dir() -> Path:
    """
    Get data directory based on deployment target.

    Returns:
        - Desktop: ~/.aurity/
        - Cloud: /opt/free-intelligence/storage/ (or DATA_DIR env var)
    """
    explicit = os.getenv("DATA_DIR")
    if explicit:
        return Path(explicit).expanduser()

    if is_desktop():
        return Path.home() / ".aurity"

    return Path("/opt/free-intelligence/storage")


def _load_ollama_source_config() -> dict | None:
    """Load Ollama source config from ~/.aurity/ollama-source.json."""
    if not OLLAMA_SOURCE_CONFIG.exists():
        return None
    try:
        return json.loads(OLLAMA_SOURCE_CONFIG.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("OLLAMA_SOURCE_CONFIG_READ_ERROR: %s", e)
        return None


def _fetch_azure_tunnel_url_sync() -> str | None:
    """
    Fetch tunnel URL from Azure Blob Storage (sync version).

    Reads from fi-tunnels/tunnel-url.json blob which is updated
    automatically by fi-monitor when cloudflared starts.

    Returns:
        Tunnel URL if available and valid, None otherwise.
    """
    blob_url = os.getenv(
        "FI_TUNNEL_BLOB_URL",
        "https://aurityreleases.blob.core.windows.net/fi-tunnels/tunnel-url.json",
    )
    try:
        response = httpx.get(blob_url, timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            tunnel_url = data.get("tunnel_url")
            if tunnel_url and _is_valid_ollama_url(tunnel_url):
                logger.debug("OLLAMA_HOST_FROM_AZURE: url=%s", tunnel_url)
                return tunnel_url
    except Exception as e:
        logger.debug("AZURE_TUNNEL_FETCH_FAILED: %s", e)
    return None


def get_ollama_host() -> str:
    """
    Get Ollama endpoint based on deployment target.

    Priority:
        1. Explicit OLLAMA_HOST env var (always wins)
        2. User config from ~/.aurity/ollama-source.json
        3. Default based on target:
           - Desktop: http://localhost:11434
           - Cloud: reads from /tmp/ollama-tunnel-url.txt or uses env var

    Returns:
        Ollama API endpoint URL
    """
    explicit = os.getenv("OLLAMA_HOST")
    if explicit:
        return explicit

    # Check user config (FI-BACKEND-SOURCE-001)
    config = _load_ollama_source_config()
    if config:
        source = config.get("source", "local")
        if source == "tunnel":
            tunnel_url = config.get("tunnel_url", "")
            if tunnel_url and _is_valid_ollama_url(tunnel_url):
                logger.debug("OLLAMA_HOST_FROM_CONFIG: source=tunnel url=%s", tunnel_url)
                return tunnel_url
        else:
            local_url = config.get("local_url", "http://localhost:11434")
            if local_url and _is_valid_ollama_url(local_url):
                logger.debug("OLLAMA_HOST_FROM_CONFIG: source=local url=%s", local_url)
                return local_url

    # Desktop always uses localhost
    if is_desktop():
        return "http://localhost:11434"

    # Cloud: try to read tunnel URL (set by ollama-tunnel.sh script)
    tunnel_file = Path("/tmp/ollama-tunnel-url.txt")
    if tunnel_file.exists():
        try:
            return tunnel_file.read_text().strip()
        except OSError:
            pass

    # Fallback for cloud without tunnel
    return "http://localhost:11434"


def get_ollama_hosts() -> list[OllamaHost]:
    """
    Get ordered list of Ollama hosts for multi-host fallback.

    Priority (FI-BACKEND-FALLBACK-002):
        1. Azure Blob (fi-tunnels/tunnel-url.json) - primary, auto-updated by fi-monitor
        2. Local file (/tmp/ollama-tunnel-url.txt) - manual override
        3. Env var (OLLAMA_TUNNEL_URL) - CI/CD fallback
        99. Mac localhost - development fallback

    If OLLAMA_HOST is explicitly set, returns only that host (no fallback).

    Returns:
        List of OllamaHost TypedDicts, sorted by priority
    """
    # If explicit OLLAMA_HOST, use only that (disable fallback)
    explicit = os.getenv("OLLAMA_HOST")
    if explicit:
        return [OllamaHost(url=explicit, name="explicit_override", priority=1)]

    hosts: list[OllamaHost] = []

    # 1. Azure Blob (primary - auto-updated by fi-monitor)
    azure_url = _fetch_azure_tunnel_url_sync()
    if azure_url:
        hosts.append(
            OllamaHost(
                url=azure_url,
                name="azure_tunnel",
                priority=1,
            )
        )

    # 2. Local file (manual override - set by ollama-tunnel.sh or user)
    tunnel_file = Path("/tmp/ollama-tunnel-url.txt")
    if tunnel_file.exists():
        try:
            tunnel_url = tunnel_file.read_text().strip()
            if tunnel_url and _is_valid_ollama_url(tunnel_url):
                if not any(h["url"] == tunnel_url for h in hosts):
                    hosts.append(
                        OllamaHost(
                            url=tunnel_url,
                            name="tunnel_file",
                            priority=2,
                        )
                    )
            elif tunnel_file.stat().st_size == 0 or not tunnel_url:
                logger.warning(
                    "OLLAMA_TUNNEL_FILE_EMPTY: %s exists but is empty",
                    tunnel_file,
                )
        except OSError as e:
            logger.warning(
                "OLLAMA_TUNNEL_FILE_READ_ERROR: Failed to read %s: %s",
                tunnel_file,
                e,
            )

    # 3. Env var (CI/CD fallback - GitHub Secret)
    tunnel_env = os.getenv("OLLAMA_TUNNEL_URL")
    if tunnel_env and not any(h["url"] == tunnel_env for h in hosts):
        hosts.append(
            OllamaHost(
                url=tunnel_env,
                name="tunnel_env",
                priority=3,
            )
        )

    # 99. Mac localhost (development fallback)
    mac_fallback = os.getenv("OLLAMA_MAC_FALLBACK", "http://localhost:11434")
    hosts.append(
        OllamaHost(
            url=mac_fallback,
            name="mac_localhost",
            priority=99,
        )
    )

    return sorted(hosts, key=lambda h: h["priority"])


def get_storage_path(relative_path: str = "") -> Path:
    """
    Get a path within the data directory.

    Args:
        relative_path: Path relative to data directory (e.g., "sessions/abc123")

    Returns:
        Absolute path combining data_dir with relative_path
    """
    base = get_data_dir()
    if relative_path:
        return base / relative_path
    return base


def ensure_data_dir() -> Path:
    """
    Ensure the data directory exists (creates if needed).

    Returns:
        Path to the data directory
    """
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
