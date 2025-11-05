"""Common utilities and shared infrastructure."""

from __future__ import annotations

# Re-export commonly used utilities
from backend.common.logger import get_logger, init_logger_from_config
from backend.common.config_loader import load_config
from backend.common.cache import LLMCache
from backend.common.metrics import MetricsCollector
from backend.common.container import get_container
from backend.common.type_defs import (
    SessionID,
    InteractionID,
    JobID,
    ChunkID,
)

__all__ = [
    "get_logger",
    "init_logger_from_config",
    "load_config",
    "LLMCache",
    "MetricsCollector",
    "get_container",
    "SessionID",
    "InteractionID",
    "JobID",
    "ChunkID",
]
