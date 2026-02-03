"""Centralized configuration for backend services.

Single source of truth for paths and settings, avoiding relative path hell.

Author: Claude Code
Created: 2026-01-29
Purpose: DI Refactor Fix #1 - Eliminate _CORPUS_PATH duplication across 14 files
"""
from pathlib import Path
import os

# Project root (parent of backend/ directory)
PROJECT_ROOT = Path(__file__).parent.parent

# Storage paths
CORPUS_PATH = PROJECT_ROOT / "storage" / "corpus.h5"
LOGS_PATH = PROJECT_ROOT / "logs"
EXPORT_PATH = PROJECT_ROOT / "exports"

# Environment configuration
DEPLOYMENT_TARGET = os.getenv("DEPLOYMENT_TARGET", "dev")
GIT_COMMIT = os.getenv("GIT_COMMIT", "dev")

# Feature flags
# NEW_API_STRUCTURE_ENABLED: Enable new domain-based API routes (/api/aurity/...)
# When True, both legacy (/api/workflows/aurity/...) and new routes are available
# Phase 5 (Hadopelágica) will remove legacy routes and set this to True by default
NEW_API_STRUCTURE_ENABLED = os.getenv("NEW_API_STRUCTURE_ENABLED", "false").lower() == "true"


def get_corpus_path() -> Path:
    """Get corpus.h5 path (allows testing override).

    Returns:
        Path to HDF5 corpus file

    Usage:
        # Production:
        corpus = get_corpus_path()  # Returns PROJECT_ROOT/storage/corpus.h5

        # Testing:
        import backend.config as config
        config.CORPUS_PATH = Path("/tmp/test-corpus.h5")
        corpus = get_corpus_path()  # Returns /tmp/test-corpus.h5
    """
    return CORPUS_PATH


def validate_corpus_exists() -> None:
    """Validate corpus.h5 exists, create parent directory if needed.

    Raises:
        FileNotFoundError: If corpus.h5 doesn't exist and can't be created
    """
    if not CORPUS_PATH.exists():
        # Create parent directory if missing
        CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

        if not CORPUS_PATH.exists():
            raise FileNotFoundError(
                f"Corpus file not found: {CORPUS_PATH}\n"
                f"Expected location: {CORPUS_PATH.absolute()}\n"
                "Run: make init-storage to create corpus structure"
            )
