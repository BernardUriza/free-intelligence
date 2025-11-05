"""Common utilities and shared infrastructure.

NOTE: This module uses lazy loading via __getattr__ to avoid circular imports.
Do NOT add eager imports here - all dependencies must be lazy-loaded.
"""

from __future__ import annotations

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


def __getattr__(name: str):
    """Lazy load all exports to avoid circular import chain:
    backend.logger -> backend.common.logger -> backend.common.__init__ -> backend.common.metrics -> backend.logger
    """
    if name == "get_logger":
        from backend.common.logger import get_logger

        return get_logger
    elif name == "init_logger_from_config":
        from backend.common.logger import init_logger_from_config

        return init_logger_from_config
    elif name == "LLMCache":
        from backend.common.cache import LLMCache

        return LLMCache
    elif name == "MetricsCollector":
        from backend.common.metrics import MetricsCollector

        return MetricsCollector
    elif name == "get_container":
        from backend.common.container import get_container

        return get_container
    elif name == "load_config":
        from backend.common.config_loader import load_config

        return load_config
    elif name in ("ChunkID", "InteractionID", "JobID", "SessionID"):
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
