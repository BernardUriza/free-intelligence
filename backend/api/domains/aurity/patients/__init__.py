"""Patients Domain - Patient record management.

CRUD operations for patient records with PostgreSQL persistence.

Endpoints (6 total):
- POST   /patients/validate-curp - Validate CURP format and availability
- POST   /patients - Create patient
- GET    /patients - List patients with search/pagination
- GET    /patients/{id} - Get patient by ID
- PUT    /patients/{id} - Update patient
- DELETE /patients/{id} - Delete patient

Migrated from: backend/api/routers/patient/public/patients.py (444 lines)
Card: FI-DATA-DB-001
Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from fastapi import APIRouter

from . import patients_crud

# Aggregated router for patients domain
router = APIRouter(prefix="/patients", tags=["Patients"])

# CRUD: 6 endpoints
router.include_router(patients_crud.router)

# Re-export models for backwards compatibility
from .models import (
    CurpValidationRequest,
    CurpValidationResponse,
    GenderEnum,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)

__all__ = [
    "router",
    "GenderEnum",
    "PatientCreate",
    "PatientUpdate",
    "PatientResponse",
    "CurpValidationRequest",
    "CurpValidationResponse",
]
