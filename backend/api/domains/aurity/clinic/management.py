"""Clinic Management - CRUD operations for clinics, doctors, and appointments.

Refactored into sub-modules:
- clinics_crud.py: Clinic CRUD (5 endpoints)
- doctors.py: Doctor CRUD (5 endpoints)
- appointments.py: Appointment CRUD (4 endpoints)
- doctor_limits.py: Doctor limits (2 endpoints)

Supporting modules:
- models.py: Pydantic request/response schemas
- helpers.py: Utility functions

Total: 16 endpoints

Consolidated: 2026-02 (Oceanic API Restructure - Phase Consolidation)
Refactored: 2026-02-03
"""

from __future__ import annotations

from fastapi import APIRouter

from . import appointments, clinics_crud, doctor_limits, doctors

# Router with /clinics prefix (added here)
router = APIRouter(prefix="/clinics", tags=["Clinics"])

# Include all sub-routers
router.include_router(clinics_crud.router)
router.include_router(doctors.router)
router.include_router(appointments.router)
router.include_router(doctor_limits.router)

# Re-export models for backwards compatibility
from .models import (
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentUpdate,
    ClinicCreate,
    ClinicListResponse,
    ClinicResponse,
    ClinicUpdate,
    DoctorCreate,
    DoctorLimitInfoResponse,
    DoctorListResponse,
    DoctorOverrideUpdate,
    DoctorResponse,
    DoctorUpdate,
)

__all__ = [
    "router",
    # Clinic models
    "ClinicCreate",
    "ClinicUpdate",
    "ClinicResponse",
    "ClinicListResponse",
    # Doctor models
    "DoctorCreate",
    "DoctorUpdate",
    "DoctorResponse",
    "DoctorListResponse",
    "DoctorLimitInfoResponse",
    "DoctorOverrideUpdate",
    # Appointment models
    "AppointmentCreate",
    "AppointmentUpdate",
    "AppointmentResponse",
    "AppointmentListResponse",
]
