"""DEPRECATED: Use backend.app.main instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "backend.main is deprecated. Use backend.app.main instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from backend.app.main import *  # noqa: F401, F403
