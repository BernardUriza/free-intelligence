"""Common utilities and shared infrastructure."""

from __future__ import annotations

# Re-export commonly used utilities
from backend.common.logger import setup_logger
from backend.common.config_loader import load_config
from backend.common.cache import InMemoryCache
from backend.common.metrics import MetricsCollector
from backend.common.container import Container
from backend.common.dependencies import get_dependencies
from backend.common.type_defs import (
    SessionID,
    InteractionID,
    JobID,
    ChunkID,
)

__all__ = [
    "setup_logger",
    "load_config",
    "InMemoryCache",
    "MetricsCollector",
    "Container",
    "get_dependencies",
    "SessionID",
    "InteractionID",
    "JobID",
    "ChunkID",
]
