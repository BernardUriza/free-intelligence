"""Logger interface for dependency injection."""

from abc import ABC, abstractmethod
from typing import Any


class ILogger(ABC):
    """Abstract interface for logging.

    Provides standard logging levels: debug, info, warning, error.
    Compatible with structlog.BoundLogger via StructlogAdapter.
    """

    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        ...

    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        ...

    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        ...
