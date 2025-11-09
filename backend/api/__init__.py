"""API routers organized by access level.

Architecture:
- public/   → CORS enabled, orchestrators (accessible from external clients)
- internal/ → Localhost-only, atomic resources (restricted in production)

File: backend/api/__init__.py
Reorganized: 2025-11-08 (public/internal split)
"""

from __future__ import annotations

from . import internal, public

__all__ = ["public", "internal"]
