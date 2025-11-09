"""Session management endpoints.

Contains:
- router.py → Main session CRUD
- athlete_sessions.py → Live athlete sessions (SESION-04/05)
- designs.py → Session design templates
"""

from __future__ import annotations

from . import athlete_sessions, designs
from .router import router

__all__ = ["router", "athlete_sessions", "designs"]
