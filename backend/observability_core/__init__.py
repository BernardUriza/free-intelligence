from __future__ import annotations

__all__ = [
    "get_logger",
]

import structlog


def get_logger(name: str | None = None):
    return structlog.get_logger(name or __name__)
