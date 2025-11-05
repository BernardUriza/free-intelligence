"""Dependency injection container.

Re-exports from backend.common.container for backward compatibility.
"""

from __future__ import annotations

from backend.common.container import get_container

__all__ = ["get_container"]
