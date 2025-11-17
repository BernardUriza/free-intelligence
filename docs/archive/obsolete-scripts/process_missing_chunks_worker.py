"""DEPRECATED: Use backend.jobs.process_missing_chunks instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.process_missing_chunks_worker is deprecated. Use backend.jobs.process_missing_chunks",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for compatibility
from backend.jobs.process_missing_chunks import *  # noqa: F401, F403
