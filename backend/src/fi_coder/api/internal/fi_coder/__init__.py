from __future__ import annotations

from backend.src.fi_coder.service import FiCoderService

service = FiCoderService()
router = service.get_api_router()
