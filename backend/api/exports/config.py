"""Configuration for export API.

Centralizes environment variables and constants.
"""

from __future__ import annotations

import os
from datetime import timezone
from pathlib import Path

from backend.logger import get_logger

__all__ = ["EXPORT_DIR", "BASE_DOWNLOAD_URL", "UTC", "logger"]

# ============================================================================
# CONFIGURATION
# ============================================================================

# Export directory (env var or default)
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "/tmp/fi_exports"))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Base download URL (env var or default)
BASE_DOWNLOAD_URL = os.getenv("BASE_DOWNLOAD_URL", "http://localhost:7001/downloads")

# UTC timezone constant (Python 3.9+ compatible)
UTC = timezone.utc

# Logger instance
logger = get_logger(__name__)
