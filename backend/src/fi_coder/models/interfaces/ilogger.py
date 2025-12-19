"""Logger interface for dependency injection."""

from abc import ABC, abstractmethod
from typing import Any


class ILogger(ABC):
    """Abstract interface for logging."""

    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        pass

    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        pass