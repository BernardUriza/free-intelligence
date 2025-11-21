"""Configuration for export API.

Centralizes environment variables and constants.
"""

from __future__ import annotations

import os
from datetime import UTC
from pathlib import Path

from backend.logger import get_logger

__all__ = ["BASE_DOWNLOAD_URL", "EXPORT_DIR", "UTC", "logger"]

# ============================================================================
# CONFIGURATION
# ============================================================================

# Export directory (env var or default)
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "/tmp/fi_exports"))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Base download URL (env var or default)
BASE_DOWNLOAD_URL = os.getenv("BASE_DOWNLOAD_URL", "http://localhost:7001/downloads")

# Logger instance
logger = get_logger(__name__)
