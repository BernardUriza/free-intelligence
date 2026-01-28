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

# Note: This file is intentionally left empty to show deprecation warning.
# All functionality has been moved to backend.infrastructure.
# Update your imports directly instead of relying on this redirect.
