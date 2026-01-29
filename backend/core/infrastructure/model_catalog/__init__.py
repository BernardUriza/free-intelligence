"""Backward compatibility redirect for model_catalog module.

DEPRECATED: Use backend.infrastructure.model_catalog instead.
"""

import warnings

warnings.warn(
    "backend.core.infrastructure.model_catalog is deprecated. Use backend.infrastructure.model_catalog",
    DeprecationWarning,
    stacklevel=2,
)

# Redirect all imports to new location
from backend.infrastructure.model_catalog import *  # noqa: F401, F403
