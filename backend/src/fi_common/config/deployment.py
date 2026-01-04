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

import logging
import os
from enum import Enum
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


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


def get_ollama_host() -> str:
    """
    Get Ollama endpoint based on deployment target.

    Priority:
        1. Explicit OLLAMA_HOST env var (always wins)
        2. Default based on target:
           - Desktop: http://localhost:11434
           - Cloud: reads from /tmp/ollama-tunnel-url.txt or uses env var

    Returns:
        Ollama API endpoint URL
    """
    explicit = os.getenv("OLLAMA_HOST")
    if explicit:
        return explicit

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

    Priority:
        1. Windows tunnel (from file or env var) - primary
        2. Mac localhost - fallback when traveling

    If OLLAMA_HOST is explicitly set, returns only that host (no fallback).

    Returns:
        List of OllamaHost TypedDicts, sorted by priority
    """
    # If explicit OLLAMA_HOST, use only that (disable fallback)
    explicit = os.getenv("OLLAMA_HOST")
    if explicit:
        return [OllamaHost(url=explicit, name="explicit_override", priority=1)]

    hosts: list[OllamaHost] = []

    # 1. Windows tunnel from file (primary - set by ollama-tunnel.sh)
    tunnel_file = Path("/tmp/ollama-tunnel-url.txt")
    if tunnel_file.exists():
        try:
            tunnel_url = tunnel_file.read_text().strip()
            if tunnel_url and tunnel_url.startswith("http"):
                hosts.append(OllamaHost(
                    url=tunnel_url,
                    name="windows_tunnel",
                    priority=1,
                ))
            elif tunnel_file.stat().st_size == 0 or not tunnel_url:
                # FI-BACKEND-FALLBACK-001: Warn about empty tunnel file
                logger.warning(
                    "OLLAMA_TUNNEL_FILE_EMPTY: %s exists but is empty, "
                    "skipping Windows tunnel host",
                    tunnel_file,
                )
        except OSError as e:
            logger.warning(
                "OLLAMA_TUNNEL_FILE_READ_ERROR: Failed to read %s: %s",
                tunnel_file,
                e,
            )

    # 2. Windows tunnel from env var (GitHub Secret fallback)
    tunnel_env = os.getenv("OLLAMA_TUNNEL_URL")
    if tunnel_env and not any(h["url"] == tunnel_env for h in hosts):
        hosts.append(OllamaHost(
            url=tunnel_env,
            name="windows_tunnel_env",
            priority=2,
        ))

    # 3. Mac localhost (fallback when traveling/developing)
    mac_fallback = os.getenv("OLLAMA_MAC_FALLBACK", "http://localhost:11434")
    hosts.append(OllamaHost(
        url=mac_fallback,
        name="mac_localhost",
        priority=99,
    ))

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
