"""System Domain - Infrastructure metrics and management.

Endpoints:
- GET  /system/disk-usage - Get disk usage stats
- GET  /system/llm-status - Get LLM provider status
- POST /system/clear-memory - Clear memory cache

Features:
- Disk usage monitoring for storage directory
- LLM status checking (tunnel + local fallback)
- fi-monitor gateway integration

Migrated from: backend/infrastructure/system/api/public/system.py
"""

from __future__ import annotations

# Re-export router from legacy location
# TODO: Full migration in Phase 3 when HTTP routes change
from backend.infrastructure.system.api.public.system import router

__all__ = ["router"]
