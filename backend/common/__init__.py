"""Common utilities and shared infrastructure."""

from __future__ import annotations

from backend.common.cache import LLMCache
from backend.common.config_loader import load_config
from backend.common.container import get_container

# Re-export commonly used utilities
from backend.common.logger import get_logger, init_logger_from_config
from backend.common.metrics import MetricsCollector
from backend.common.type_defs import ChunkID, InteractionID, JobID, SessionID

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
