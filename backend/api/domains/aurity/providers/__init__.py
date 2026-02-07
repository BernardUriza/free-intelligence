"""Providers Domain - Healthcare provider management.

CRUD operations for provider records with PostgreSQL persistence.

Endpoints (5 total):
- POST   /providers - Create provider
- GET    /providers - List providers with search/pagination
- GET    /providers/{id} - Get provider by ID
- PUT    /providers/{id} - Update provider
- DELETE /providers/{id} - Delete provider

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
Card: FI-DATA-DB-001
"""

from __future__ import annotations

from fastapi import APIRouter

from .models import ProviderCreate, ProviderResponse, ProviderUpdate
from .providers_crud import router as crud_router

# Aggregate router for the providers domain
router = APIRouter(prefix="/providers", tags=["Providers"])

# Include sub-routers (strip prefix since crud_router already has /providers)
for route in crud_router.routes:
    router.routes.append(route)

# Re-export models for convenience
__all__ = [
    "router",
    "ProviderCreate",
    "ProviderResponse",
    "ProviderUpdate",
]
