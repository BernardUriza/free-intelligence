"""Backward compatibility redirect for model_catalog.services module.

DEPRECATED: Use backend.infrastructure.model_catalog.services instead.
"""

import warnings

warnings.warn(
    "backend.core.infrastructure.model_catalog.services is deprecated. Use backend.infrastructure.model_catalog.services",
    DeprecationWarning,
    stacklevel=2,
)

# Redirect all imports to new location
from backend.infrastructure.model_catalog.services import *  # noqa: F401, F403
