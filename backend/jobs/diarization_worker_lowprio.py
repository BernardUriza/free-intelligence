"""DEPRECATED: Use backend.jobs.diarization_worker_lowprio instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "backend.diarization_worker_lowprio is deprecated. Use backend.jobs.diarization_worker_lowprio instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from backend.jobs.diarization_worker_lowprio import *  # noqa: F401, F403
