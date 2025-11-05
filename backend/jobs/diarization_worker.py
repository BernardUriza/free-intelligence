"""DEPRECATED: Use backend.jobs.diarization_worker instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "backend.diarization_worker is deprecated. Use backend.jobs.diarization_worker instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from backend.jobs.diarization_worker import *  # noqa: F401, F403
