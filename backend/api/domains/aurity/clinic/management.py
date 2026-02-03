"""Clinic Management - Re-export from legacy clinics.py.

CRUD operations for clinics, doctors, and appointments.

Endpoints (18 total):
## Clinics (5)
- GET    /clinics - List clinics
- GET    /clinics/{id} - Get clinic
- POST   /clinics - Create clinic
- PATCH  /clinics/{id} - Update clinic
- DELETE /clinics/{id} - Delete clinic

## Doctors (5)
- GET    /clinics/{id}/doctors - List doctors
- GET    /clinics/{id}/doctors/{id} - Get doctor
- POST   /clinics/{id}/doctors - Create doctor
- PATCH  /clinics/{id}/doctors/{id} - Update doctor
- DELETE /clinics/{id}/doctors/{id} - Delete doctor

## Appointments (4)
- POST   /clinics/{id}/appointments - Create appointment
- GET    /clinics/{id}/appointments - List appointments
- PATCH  /clinics/{id}/appointments/{id} - Update appointment
- DELETE /clinics/{id}/appointments/{id} - Delete appointment

## Doctor Limits (2)
- GET    /clinics/{id}/doctor-limits - Get doctor limits
- PATCH  /clinics/{id}/doctor-override - Update doctor override

Re-exported from: backend/api/routers/clinic/public/clinics.py
Note: Full migration planned for Phase 4 (Abisopelágica) when legacy routes are deprecated.
"""

from __future__ import annotations

# Re-export router from legacy location
# Router already has prefix="/clinics" so no additional prefix needed
from backend.api.routers.clinic.public.clinics import router

__all__ = ["router"]
