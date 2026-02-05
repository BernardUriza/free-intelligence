"""Timeline verification endpoint (internal).

Validates timeline event hashes against corpus data for data integrity.
"""

from __future__ import annotations

from .router import router

__all__ = ["router"]
