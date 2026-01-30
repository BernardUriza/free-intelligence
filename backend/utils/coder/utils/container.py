"""Dependency injection container.

Re-exports from backend.infrastructure.common.container for backward compatibility.
"""

from __future__ import annotations

from backend.infrastructure.common.container import get_container

__all__ = ["get_container"]
