"""Environment parsing shared by every consumer."""

from __future__ import annotations

import os

TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def env_flag(name: str, default: bool = False) -> bool:
    """True when `name` is one of `TRUE_VALUES` (any case); `default` when unset or blank."""
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in TRUE_VALUES
