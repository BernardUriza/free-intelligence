"""Legacy scripts directory - DEPRECATED.

All scripts have been reorganized into backend/jobs, backend/cli, backend/tools, and backend/services.
This module provides backward compatibility facades only.

Migration path:
- Jobs (background workers) → backend/jobs/
- CLI tools → backend/cli/
- Operational tools → backend/tools/
- Services (domain logic) → backend/services/
"""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts/ is deprecated. Use backend/jobs/, backend/cli/, backend/tools/, or backend/services/ instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = []
