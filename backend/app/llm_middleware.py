"""DEPRECATED: Use backend.app.llm_middleware instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "backend.llm_middleware is deprecated. Use backend.app.llm_middleware instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from backend.app.llm_middleware import *  # noqa: F401, F403
