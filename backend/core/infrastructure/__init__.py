"""DEPRECATED: Infrastructure has been moved to backend.infrastructure.

This module has been deprecated. Please update imports to:
- backend.core.infrastructure.auth → backend.infrastructure.auth
- backend.core.infrastructure.workers → backend.infrastructure.workers
- backend.core.infrastructure.model_catalog → backend.infrastructure.model_catalog
- backend.core.infrastructure.observability → backend.infrastructure.observability

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - Infrastructure Extraction
"""

import warnings

warnings.warn(
    "backend.core.infrastructure is deprecated. Update imports to backend.infrastructure",
    DeprecationWarning,
    stacklevel=2,
)

# Backward compatibility redirects (temporary during migration)
# TODO: Remove these after updating all imports to backend.infrastructure

try:
    from backend.infrastructure.auth import *  # noqa: F401, F403
except ImportError:
    pass  # Module doesn't exist yet

try:
    from backend.infrastructure.workers import *  # noqa: F401, F403
except ImportError:
    pass  # Module doesn't exist yet

try:
    from backend.infrastructure.model_catalog import *  # noqa: F401, F403
except ImportError:
    pass  # Module doesn't exist yet
