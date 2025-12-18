from __future__ import annotations

"""Bridge to existing structured logger while migration completes."""

from backend.common.fi_common.logging.logger import get_logger, init_logger_from_config

__all__ = ["get_logger", "init_logger_from_config"]
