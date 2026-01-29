"""Backward compatibility redirect for workers module.

DEPRECATED: Use backend.infrastructure.workers instead.

This module redirects all imports to the new location.
"""

import warnings

warnings.warn(
    "backend.core.infrastructure.workers is deprecated. Use backend.infrastructure.workers",
    DeprecationWarning,
    stacklevel=2,
)

# Redirect all imports to new location
from backend.infrastructure.workers import *  # noqa: F401, F403
