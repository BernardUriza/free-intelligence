"""Logger utilities.

Re-exports from backend.src.fi_common.logging.logger for backward compatibility.
"""

from __future__ import annotations

from backend.src.fi_common.logging.logger import get_logger

__all__ = ["get_logger"]
