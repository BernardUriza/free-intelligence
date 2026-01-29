"""Backward compatibility redirect for auth module.

DEPRECATED: Use backend.infrastructure.auth instead.

This module redirects all imports to the new location.
"""

import warnings

warnings.warn(
    "backend.core.infrastructure.auth is deprecated. Use backend.infrastructure.auth",
    DeprecationWarning,
    stacklevel=2,
)

# Redirect all imports to new location
from backend.infrastructure.auth import *  # noqa: F401, F403

# Explicitly re-export commonly used names
try:
    from backend.infrastructure.auth import (  # noqa: F401
        User,
        UserRole,
        get_current_user,
        verify_admin_role,
    )
except ImportError as e:
    # If infrastructure.auth doesn't have these, provide stubs
    import warnings
    warnings.warn(f"Failed to import from backend.infrastructure.auth: {e}", UserWarning)
