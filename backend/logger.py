#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Structured Logger

Timezone-aware structured logging with automatic config integration.
Uses structlog for structured output with JSON support.

FI-CORE-FEAT-002
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

import structlog


def get_logger(
    name: str = "free-intelligence",
    log_level: Optional[str] = None,
    timezone: str = "America/Mexico_City",
    log_file: Optional[str] = None,
) -> structlog.BoundLogger:
    """
    Get configured structured logger with timezone-aware timestamps.

    Args:
        name: Logger name (default: "free-intelligence")
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  If None, reads from config.yml via config_loader.
        timezone: Timezone for timestamps (default: "America/Mexico_City")
        log_file: Optional path to log file. If None, logs to stderr only.

    Returns:
        Configured structlog BoundLogger instance

    Examples:
        >>> logger = get_logger()
        >>> logger.info("system_started", version="0.1.0")

        >>> logger = get_logger(log_level="DEBUG", log_file="logs/system.log")
        >>> logger.debug("config_loaded", path="/path/to/config.yml")
    """
    # Load log level from config if not provided
    if log_level is None:
        try:
            from config_loader import load_config

            config = load_config()
            log_level = config["system"]["log_level"]
        except Exception:
            log_level = "INFO"  # Safe default

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure handlers
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    # Configure standard logging
    logging.basicConfig(format="%(message)s", level=numeric_level, handlers=handlers, force=True)

    # Timezone-aware timestamp processor
    def add_timestamp(
        logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
    ) -> dict[str, Any]:
        """Add timezone-aware timestamp to log entries."""
        tz = ZoneInfo(timezone)
        event_dict["timestamp"] = datetime.now(tz).isoformat()
        return event_dict

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            add_timestamp,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(name)


def init_logger_from_config(config_path: Optional[str] = None) -> structlog.BoundLogger:
    """
    Initialize logger using configuration from config.yml.

    Args:
        config_path: Optional path to config file. If None, uses default location.

    Returns:
        Configured logger instance

    Examples:
        >>> logger = init_logger_from_config()
        >>> logger.info("application_started")
    """
    try:
        from config_loader import load_config

        config = load_config(config_path)

        log_level = config["system"]["log_level"]
        timezone = config["system"]["timezone"]

        # Determine log file path
        log_file = None
        # Future: Add log_file configuration to config.yml if needed

        return get_logger(
            name="free-intelligence", log_level=log_level, timezone=timezone, log_file=log_file
        )
    except Exception as e:
        # Fallback to defaults if config loading fails
        fallback_logger = get_logger(log_level="INFO")
        fallback_logger.warning("config_load_failed", error=str(e), using_defaults=True)
        return fallback_logger


if __name__ == "__main__":
    # CLI demonstration
    import sys

    log_level = sys.argv[1] if len(sys.argv) > 1 else None
    logger = get_logger(log_level=log_level) if log_level else init_logger_from_config()

    logger.info("logger_initialized", version="0.1.0")
    logger.debug("debug_message", detail="This is a debug message")
    logger.warning("warning_message", reason="This is a warning")
    logger.error("error_message", code=500)

    print("\n✅ Logger working correctly with timezone-aware timestamps")
