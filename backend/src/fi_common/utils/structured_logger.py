"""Concrete logger implementation."""

from backend.src.fi_common.interfaces.ilogger import ILogger
from backend.src.fi_common.logging.logger import get_logger


class StructuredLogger(ILogger):
    """Structured logger implementation using fi_coder logger."""

    def __init__(self, name: str = __name__):
        self._logger = get_logger(name)

    def info(self, message: str, **kwargs):
        self._logger.info(message, **kwargs)

    def error(self, message: str, **kwargs):
        self._logger.error(message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._logger.warning(message, **kwargs)
