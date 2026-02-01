"""Structlog adapter for ILogger interface.

Wraps structlog.BoundLogger to implement ILogger interface for type safety.

Author: Claude Sonnet 4.5 (El Revisor Agresivo)
Created: 2026-01-31
Purpose: Fix BoundLogger/ILogger type mismatch
"""

from typing import Any
from structlog.typing import FilteringBoundLogger
from backend.infrastructure.interfaces.ilogger import ILogger


class StructlogAdapter(ILogger):
    """Adapter that wraps structlog.BoundLogger to implement ILogger.

    Why Adapter Pattern:
    - structlog.BoundLogger has the methods we need (debug, info, warning, error)
    - But it doesn't inherit from ILogger (can't change 3rd party code)
    - Adapter wraps BoundLogger and delegates calls

    Type Safety:
    - Code can depend on ILogger (interface)
    - StructlogAdapter ensures BoundLogger conforms to ILogger
    - Pyright stops complaining about type mismatch
    """

    def __init__(self, bound_logger: FilteringBoundLogger):
        """Initialize adapter with structlog BoundLogger.

        Args:
            bound_logger: structlog.BoundLogger instance
        """
        self._logger = bound_logger

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message.

        Args:
            message: Log event name (e.g., "MEMORY_STORE_CACHE_HIT")
            **kwargs: Structured log fields
        """
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message.

        Args:
            message: Log event name (e.g., "MEMORY_STORE_OPERATION")
            **kwargs: Structured log fields
        """
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message.

        Args:
            message: Log event name (e.g., "HDF5_DECODE_ERROR")
            **kwargs: Structured log fields
        """
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message.

        Args:
            message: Log event name (e.g., "ELASTICSEARCH_CONNECTION_ERROR")
            **kwargs: Structured log fields
        """
        self._logger.error(message, **kwargs)


__all__ = ["StructlogAdapter"]
