"""Shared structlog setup. Call from each bot's `__main__.py` BEFORE
importing any project module — because modules do
`log = structlog.get_logger()` at import time and cache the configuration.

`LOG_FORMAT=json` (prod / KQL) picks JSONRenderer; anything else picks
ConsoleRenderer (local dev with colors).

`processors_extra` is inserted right before the final renderer so each
bot can wire its own observability hooks (metrics collector, Sentry
breadcrumb, etc.) without forking the base processor chain.
"""

from __future__ import annotations

import os

import structlog
from structlog.typing import Processor


def configure_structlog(processors_extra: list[Processor] | None = None) -> None:
    """Wire structlog with the canonical processor chain.

    Args:
        processors_extra: optional list of processors inserted RIGHT BEFORE
            the final renderer. Insult passes `[metrics_processor]`; ALICE
            currently passes nothing.
    """
    log_format = os.environ.get("LOG_FORMAT", "console").lower()
    renderer = structlog.processors.JSONRenderer() if log_format == "json" else structlog.dev.ConsoleRenderer()

    base_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    processors: list[Processor] = base_processors + list(processors_extra or []) + [renderer]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
