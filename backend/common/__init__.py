"""Common utilities and shared infrastructure.

NOTE: This module uses lazy loading via __getattr__ to avoid circular imports.
Do NOT add eager imports here - all dependencies must be lazy-loaded.
"""

from __future__ import annotations

# pyright: reportUnsupportedDunderAll=false
__all__ = [
    "get_logger",
    "init_logger_from_config",
    "load_config",
    "LLMCache",
    "MetricsCollector",
    "get_container",
]


def __getattr__(name: str):
    """Lazy load all exports to avoid circular import chain.

    Re-exports from packages/fi_common/* (new location) for zero-breaking-change
    refactoring. Old imports from backend.common still work.
    """
    if name == "get_logger":
        from packages.fi_common.logging.logger import get_logger

        return get_logger
    elif name == "init_logger_from_config":
        from packages.fi_common.logging.logger import init_logger_from_config

        return init_logger_from_config
    elif name == "LLMCache":
        from packages.fi_common.cache.cache import LLMCache

        return LLMCache
    elif name == "MetricsCollector":
        from packages.fi_common.metrics.metrics import MetricsCollector

        return MetricsCollector
    elif name == "get_container":
        from packages.fi_common.infrastructure.container import get_container

        return get_container
    elif name == "load_config":
        from packages.fi_common.config.config_loader import load_config

        return load_config

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
