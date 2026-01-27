"""Common utilities and shared infrastructure.

NOTE: This module uses lazy loading via __getattr__ to avoid circular imports.
Do NOT add eager imports here - all dependencies must be lazy-loaded.
"""

from __future__ import annotations

# pyright: reportUnsupportedDunderAll=false
__all__ = [
    "LLMCache",
    "MetricsCollector",
    "get_container",
    "get_logger",
    "init_logger_from_config",
    "load_config",
]


def __getattr__(name: str):
    """Lazy load all exports to avoid circular import chain.

    Re-exports from src/fi_common/* (new location) for zero-breaking-change
    refactoring. Old imports from backend.common still work.
    """
    if name == "get_logger":
        from backend.utils.common.logging.logger import get_logger

        return get_logger
    elif name == "init_logger_from_config":
        from backend.utils.common.logging.logger import init_logger_from_config

        return init_logger_from_config
    elif name == "LLMCache":
        from backend.utils.common.cache.cache import LLMCache

        return LLMCache
    elif name == "MetricsCollector":
        from backend.utils.common.metrics.metrics import MetricsCollector

        return MetricsCollector
    elif name == "get_container":
        from backend.utils.common.infrastructure.container import get_container

        return get_container
    elif name == "load_config":
        from backend.utils.common.config.config_loader import load_config

        return load_config

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
