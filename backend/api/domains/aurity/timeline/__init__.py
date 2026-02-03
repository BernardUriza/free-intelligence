"""Timeline Domain - Session history and longitudinal memory.

Endpoints:
- GET  /timeline/sessions - List all sessions (paginated)
- GET  /timeline/sessions/{id} - Get session details

Features:
- Multi-tenancy: Sessions filtered by clinic_id
- SUPERADMIN bypass for all-clinic access
- HDF5-based session storage

Migrated from: backend/services/timeline/api/public/timeline.py
"""

from __future__ import annotations

# Re-export router from legacy location
# TODO: Full migration in Phase 3 when HTTP routes change
from backend.services.timeline.api.public.timeline import router

__all__ = ["router"]
