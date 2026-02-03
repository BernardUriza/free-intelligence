"""Prescriptions Domain - Medication catalog, interactions, allergies, and prescriptions.

LARGE domain (~40 endpoints) organized into logical groups:

Sub-modules:
- prescriptions: All prescription-related endpoints

Endpoint Groups:
## Templates (2)
- GET /templates - List available templates
- GET /templates/{id} - Get template details

## Prescriptions CRUD (7)
- POST / - Create prescription
- POST /from-soap - Create from SOAP data
- GET / - List prescriptions
- GET /{id} - Get prescription
- PUT /{id} - Update prescription
- POST /{id}/sign - Sign prescription
- POST /{id}/cancel - Cancel prescription

## Export (1)
- GET /{id}/export - Export to text/json

## Medication Catalog (7)
- GET /catalog/search - Search medications
- GET /catalog/autocomplete - Autocomplete suggestions
- GET /catalog/{id} - Get medication details
- GET /catalog/categories/list - List categories
- GET /catalog/stats - Get catalog stats
- GET /catalog/essential - Essential medications
- GET /catalog/otc - OTC medications

## Drug Interactions (4)
- POST /interactions/check - Check drug-drug interactions
- POST /interactions/check-prescription - Check with full Medication objects
- GET /interactions/drug/{name} - Get interactions for specific drug
- GET /interactions/stats - Get interaction db stats

## Allergy Checks (3)
- POST /allergies/check - Check medications vs patient allergies
- GET /allergies/medication/{name} - Get allergens for medication
- GET /allergies/stats - Get allergen db stats

## Combined Safety (1)
- POST /safety/check - Full safety check (interactions + allergies)

Migrated from: backend/api/routers/prescription/public/prescriptions.py
"""

from __future__ import annotations

from fastapi import APIRouter

from . import prescriptions

router = APIRouter()
router.include_router(prescriptions.router)
