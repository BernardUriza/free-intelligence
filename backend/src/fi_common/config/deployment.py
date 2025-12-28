"""
Deployment target configuration for FI-Cloud vs FI-Edge (Desktop).

This module provides a single source of truth for deployment-specific
configuration. The same codebase runs on both targets, differentiated
only by the DEPLOYMENT_TARGET environment variable.

Usage:
    from fi_common.config.deployment import is_desktop, get_ollama_host

    if is_desktop():
        # Desktop-specific logic
        pass

Environment Variables:
    DEPLOYMENT_TARGET: "cloud" | "desktop" (default: "desktop")
    OLLAMA_HOST: Override Ollama endpoint (optional)
    DATA_DIR: Override data directory (optional)
"""

from enum import Enum

import os
from pathlib import Path


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
