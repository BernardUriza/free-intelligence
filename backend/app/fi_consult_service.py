"""DEPRECATED: Use backend.app.fi_consult_service instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "backend.fi_consult_service is deprecated. Use backend.app.fi_consult_service instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from backend.app.fi_consult_service import *  # noqa: F401, F403
