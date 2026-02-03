"""TV Content Seeds - Re-export from legacy tv_content_seeds.py.

Manages FI default content seeds for TV displays.

Endpoints (4 total):
- GET  /tv-content/list - List TV content (seeds + doctor content)
- PATCH /tv-content/{id} - Update TV content
- POST /tv-content/disable-seed - Disable seed for clinic
- POST /tv-content/enable-seed - Enable seed for clinic

Re-exported from: backend/api/routers/content/public/tv_content_seeds.py
Note: Router has NO prefix, paths include /tv-content.
"""

from __future__ import annotations

# Re-export router from legacy location
# Router has no prefix, paths already include /tv-content/
from backend.api.routers.content.public.tv_content_seeds import router

__all__ = ["router"]
