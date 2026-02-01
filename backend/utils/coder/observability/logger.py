"""Logger utilities for FI Coder.

Provides structured logging with redaction and timezone-aware timestamps.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import sys

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for older Python versions
    from backports.zoneinfo import ZoneInfo

import structlog

from ..config.policies import LOGGING_POLICY


def _add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add timezone-aware timestamp to log entries."""
    tz = ZoneInfo("America/Mexico_City")
    import datetime

    event_dict["timestamp"] = datetime.datetime.now(tz).isoformat()
    return event_dict


def _redact_sensitive_data(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Redact sensitive information from log entries."""
    for key, value in event_dict.items():
        if isinstance(value, str):
            for pattern in LOGGING_POLICY["redact_patterns"]:
                value = re.sub(pattern, "[REDACTED]", value)
            event_dict[key] = value
    return event_dict


def _setup_structlog():
    """Configure structlog for FI Coder."""
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stderr)],
        force=True,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            _add_timestamp,
            _redact_sensitive_data,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.KeyValueRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Initialize structlog on import
_setup_structlog()


def get_logger(name: str = "fi_coder"):
    """Get structured logger for FI Coder.

    Args:
        name: Logger name (defaults to 'fi_coder')

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def redact_logs(text: str) -> str:
    """Redact sensitive information from text.

    Args:
        text: Text to redact

    Returns:
        Redacted text
    """
    for pattern in LOGGING_POLICY["redact_patterns"]:
        text = re.sub(pattern, "[REDACTED]", text)
    return text


# Default logger instance
logger = get_logger()

__all__ = ["get_logger", "logger", "redact_logs"]
