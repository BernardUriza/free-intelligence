"""Configuration for timeline verify API.

Centralizes environment variables and constants.
"""

from __future__ import annotations

from datetime import timezone

from backend.config_loader import load_config
from backend.logger import get_logger

__all__ = ["CORPUS_PATH", "UTC", "logger"]

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load configuration
config = load_config()
STORAGE_PATH = config.get("storage", {}).get("path", "./storage")
CORPUS_PATH = f"{STORAGE_PATH}/corpus.h5"

# UTC timezone constant (Python 3.9+ compatible)
UTC = timezone.utc

# Logger instance
logger = get_logger(__name__)
