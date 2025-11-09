"""DEPRECATED: Use backend.storage.corpus_schema instead."""

from __future__ import annotations

import warnings

warnings.warn(
    "backend.corpus_schema is deprecated. Use backend.storage.corpus_schema instead.",
    DeprecationWarning,
    stacklevel=2,
)

from packages.fi_common.storage.corpus_schema import *  # noqa: F403
