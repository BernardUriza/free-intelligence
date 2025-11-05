"""DEPRECATED: Use backend.services.restart_diarization_job instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.restart_diarization_job is deprecated. Use backend.services.restart_diarization_job",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for compatibility
from backend.services.restart_diarization_job import *  # noqa: F401, F403
