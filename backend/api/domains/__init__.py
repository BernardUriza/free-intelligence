"""API Domains - Namespace-based API structure for multi-app backend.

This module organizes public API endpoints by app namespace:
- /api/aurity/   - AURITY telemedicine app
- /api/fi-monitor/ - FI Monitor app (future)
- /api/shared/   - Shared endpoints (future)

Architecture:
    PUBLIC (this layer) -> INTERNAL -> SERVICES

Internal endpoints (/internal/*) remain separate and are not namespaced
as they are backend-to-backend communication.
"""

from __future__ import annotations
