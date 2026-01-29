"""Backward compatibility redirect for tunnel_url_provider module.

DEPRECATED: Use backend.infrastructure.model_catalog.services.tunnel_url_provider instead.
"""

import warnings

warnings.warn(
    "backend.core.infrastructure.model_catalog.services.tunnel_url_provider is deprecated. "
    "Use backend.infrastructure.model_catalog.services.tunnel_url_provider",
    DeprecationWarning,
    stacklevel=2,
)

# Redirect all imports to new location
from backend.infrastructure.model_catalog.services.tunnel_url_provider import *  # noqa: F401, F403
