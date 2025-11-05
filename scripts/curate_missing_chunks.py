"""DEPRECATED: Use backend.services.diarization_curation instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "scripts.curate_missing_chunks is deprecated. Use backend.services.diarization_curation",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for compatibility
from backend.services.diarization_curation import *  # noqa: F401, F403

