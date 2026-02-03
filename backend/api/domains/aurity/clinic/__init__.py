"""Clinic Domain - Clinic management and waiting room features.

This is a LARGE domain (~33 endpoints) organized into sub-modules:

Sub-modules:
- management: CRUD operations for clinics, doctors, appointments, limits
- media: Clinic media upload/management for TV displays
- waiting_room: AI-generated health tips and trivia
- tv_content: TV content seeds management
- widgets: Widget configuration (trivia, breathing, tips)

Endpoints (when connected to router):

## Management (from clinics.py - 18 endpoints)
- GET    /clinics - List clinics
- GET    /clinics/{id} - Get clinic
- POST   /clinics - Create clinic
- PATCH  /clinics/{id} - Update clinic
- DELETE /clinics/{id} - Delete clinic
- GET    /clinics/{id}/doctors - List doctors
- GET    /clinics/{id}/doctors/{id} - Get doctor
- POST   /clinics/{id}/doctors - Create doctor
- PATCH  /clinics/{id}/doctors/{id} - Update doctor
- DELETE /clinics/{id}/doctors/{id} - Delete doctor
- POST   /clinics/{id}/appointments - Create appointment
- GET    /clinics/{id}/appointments - List appointments
- PATCH  /clinics/{id}/appointments/{id} - Update appointment
- DELETE /clinics/{id}/appointments/{id} - Delete appointment
- GET    /clinics/{id}/doctor-limits - Get doctor limits
- PATCH  /clinics/{id}/doctor-override - Update doctor override

## Media (from clinic_media.py - 5 endpoints)
- POST   /clinic-media/upload - Upload media
- GET    /clinic-media/list - List media
- PUT    /clinic-media/{id} - Update media
- DELETE /clinic-media/{id} - Delete media
- GET    /clinic-media/file/{filename} - Serve file

## Waiting Room (from waiting_room.py - 2 endpoints)
- POST   /waiting-room/generate-tip - Generate health tip
- POST   /waiting-room/generate-trivia - Generate trivia

## TV Content (from tv_content_seeds.py - 4 endpoints)
- GET    /tv-content/list - List TV content
- PATCH  /tv-content/{id} - Update content
- POST   /tv-content/disable-seed - Disable seed
- POST   /tv-content/enable-seed - Enable seed

## Widgets (from widget_configs.py - 4 endpoints)
- GET    /widget-config/trivia - Get trivia config
- GET    /widget-config/breathing - Get breathing config
- GET    /widget-config/daily-tips - Get tips config
- GET    /widget-config/random-tip - Get random tip

Migrated from:
- backend/api/routers/clinic/public/clinics.py
- backend/api/routers/clinic/public/clinic_media.py
- backend/api/routers/workflow/public/waiting_room.py
- backend/api/routers/content/public/tv_content_seeds.py
- backend/api/widget/api/public/widget_configs.py

Status: Structure ready, waiting for file migration
"""

from __future__ import annotations

from fastapi import APIRouter

from . import management, media, tv_content, waiting_room, widgets

# Aggregated router for clinic domain
router = APIRouter()

# Management: clinics, doctors, appointments, limits (18 endpoints)
# Router already has prefix="/clinics" from legacy
router.include_router(management.router)

# Media: clinic media upload/management (4 endpoints - STUB)
# Router already has prefix="/clinic-media" from legacy
router.include_router(media.router)

# TV Content: seeds management (4 endpoints)
# Router has no prefix, paths include /tv-content/
router.include_router(tv_content.router)

# Waiting room: AI-generated health tips (2 endpoints)
router.include_router(waiting_room.router, prefix="/waiting-room")

# Widgets: trivia, breathing, tips config (4 endpoints)
# widgets.py already has /widget-config prefix in paths
router.include_router(widgets.router)

__all__ = ["router"]
