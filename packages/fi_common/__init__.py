from __future__ import annotations

"""Shared core package for Free Intelligence.

Provides domain/application/infrastructure/shared layers intended to be
imported by backend services and adapters. Implementations are gradually
migrated from backend.common.fi_common and backend storage/services.
"""

__all__ = [
    "domain",
    "application",
    "infrastructure",
    "shared",
]
