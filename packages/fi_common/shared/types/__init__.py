from __future__ import annotations

"""Shared type aliases and Protocols."""

from . import type_defs
from .type_defs import *  # noqa: F401,F403

__all__ = getattr(type_defs, "__all__", [])
