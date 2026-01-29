"""Backward compatibility redirect for auth.adapters module.

DEPRECATED: Use backend.infrastructure.auth.adapters instead.
"""

import warnings

warnings.warn(
    "backend.core.infrastructure.auth.adapters is deprecated. Use backend.infrastructure.auth.adapters",
    DeprecationWarning,
    stacklevel=2,
)

# Redirect all imports to new location
from backend.infrastructure.auth.adapters import *  # noqa: F401, F403
