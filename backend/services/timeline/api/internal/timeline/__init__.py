"""Timeline verification endpoint (internal/compatibility).

Minimal compatibility layer for legacy timeline hash verification tests.
Validates timeline event hashes against historical corpus data.
"""

from __future__ import annotations

from .router import router

__all__ = ["router"]
