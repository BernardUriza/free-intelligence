"""Backward compatibility redirect for fastapi_adapter module.

DEPRECATED: Use backend.infrastructure.auth.adapters.fastapi_adapter instead.
"""

import warnings

warnings.warn(
    "backend.core.infrastructure.auth.adapters.fastapi_adapter is deprecated. Use backend.infrastructure.auth.adapters.fastapi_adapter",
    DeprecationWarning,
    stacklevel=2,
)

# Redirect all imports to new location
from backend.infrastructure.auth.adapters.fastapi_adapter import *  # noqa: F401, F403
