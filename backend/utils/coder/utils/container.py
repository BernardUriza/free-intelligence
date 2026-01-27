"""Dependency injection container.

Re-exports from backend.utils.common.infrastructure.container for backward compatibility.
"""

from __future__ import annotations

from backend.utils.common.infrastructure.container import get_container

__all__ = ["get_container"]
