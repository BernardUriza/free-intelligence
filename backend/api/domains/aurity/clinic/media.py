"""Clinic Media - Re-export from legacy clinic_media_stub.py.

STUB implementation returning 501 Not Implemented.

Endpoints (4 total):
- POST   /clinic-media/upload - Upload media (STUB)
- GET    /clinic-media/list - List media (STUB)
- PUT    /clinic-media/{id} - Update media (STUB)
- DELETE /clinic-media/{id} - Delete media (STUB)

Re-exported from: backend/api/routers/clinic/public/clinic_media_stub.py
Note: Full implementation planned when storage layer is ready.
"""

from __future__ import annotations

# Re-export router from legacy location
# Router already has prefix="/clinic-media" so no additional prefix needed
from backend.api.routers.clinic.public.clinic_media_stub import router

__all__ = ["router"]
