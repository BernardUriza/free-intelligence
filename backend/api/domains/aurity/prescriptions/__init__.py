"""Prescriptions Domain - Medication catalog, interactions, allergies, and prescriptions.

Refactored domain (~25 endpoints) organized into logical modules:

## Modules:
- templates.py: Template management (2 endpoints)
- prescriptions_crud.py: Prescription CRUD + export (6 endpoints)
- prescriptions_actions.py: Sign/cancel actions (2 endpoints)
- catalog.py: Medication catalog (7 endpoints)
- interactions.py: Drug-drug interactions (4 endpoints)
- allergies.py: Allergy checks (3 endpoints)
- safety.py: Combined safety checks (1 endpoint)

## Supporting modules:
- models.py: Pydantic request/response models
- transformers.py: Alert formatting helpers
- dependencies.py: Shared service dependencies

Author: Bernard Uriza Orozco
Refactored: 2026-02-03
"""

from __future__ import annotations

from fastapi import APIRouter

from . import (
    allergies,
    catalog,
    interactions,
    prescriptions_actions,
    prescriptions_crud,
    safety,
    templates,
)

router = APIRouter()

# Include all sub-routers
router.include_router(templates.router)
router.include_router(prescriptions_crud.router)
router.include_router(prescriptions_actions.router)
router.include_router(catalog.router)
router.include_router(interactions.router)
router.include_router(allergies.router)
router.include_router(safety.router)

# Re-export models for backwards compatibility
from .models import (
    CancelPrescriptionRequest,
    CheckAllergiesMedicationRequest,
    CheckAllergiesRequest,
    CheckInteractionsRequest,
    CheckPrescriptionInteractionsRequest,
    CreateFromSOAPRequest,
    CreatePrescriptionRequest,
    FullSafetyCheckRequest,
    PrescriptionListResponse,
    PrescriptionResponse,
    TemplateListResponse,
    UpdatePrescriptionRequest,
)

__all__ = [
    # Router
    "router",
    # Request models
    "CancelPrescriptionRequest",
    "CheckAllergiesMedicationRequest",
    "CheckAllergiesRequest",
    "CheckInteractionsRequest",
    "CheckPrescriptionInteractionsRequest",
    "CreateFromSOAPRequest",
    "CreatePrescriptionRequest",
    "FullSafetyCheckRequest",
    "UpdatePrescriptionRequest",
    # Response models
    "PrescriptionListResponse",
    "PrescriptionResponse",
    "TemplateListResponse",
]
