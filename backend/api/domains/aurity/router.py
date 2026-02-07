"""AURITY App Router - Aggregates all domain routers under /api/aurity/.

This is the main router for the AURITY telemedicine app.
All domain routers are included here with their respective prefixes and tags.

Usage:
    from backend.api.domains.aurity.router import aurity_router, tags_metadata

    app.include_router(aurity_router, prefix="/api")
    app.openapi_tags = tags_metadata

Oceanic API Restructure - Phase 5 (Hadopelágica) Complete.
Legacy /api/workflows/aurity/* routes removed. 94 endpoints total.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.domains.aurity import (
    assistant,
    checkin,
    clinic,
    knowledge_base,
    medical_ai,
    patients,
    prescriptions,
    providers,
    system,
    timeline,
    transcription,
)

# Router with app namespace
aurity_router = APIRouter(prefix="/aurity")

# OpenAPI tags metadata for Swagger UI grouping
tags_metadata = [
    {
        "name": "Medical AI",
        "description": "Core medical workflow: sessions, diarization, SOAP notes, emotion analysis.",
    },
    {
        "name": "Transcription",
        "description": "Real-time audio streaming and transcription job management.",
    },
    {
        "name": "Prescriptions",
        "description": "Medication catalog, drug interactions, allergy checking.",
    },
    {
        "name": "Clinic",
        "description": "Clinic-specific features: TV content, waiting room, widgets.",
    },
    {
        "name": "Assistant",
        "description": "AI chat with configurable personas.",
    },
    {
        "name": "Timeline",
        "description": "Session history and longitudinal memory.",
    },
    {
        "name": "Knowledge Base",
        "description": "Document upload and RAG-powered search.",
    },
    {
        "name": "System",
        "description": "Infrastructure: disk usage, memory, LLM status.",
    },
    {
        "name": "Check-in",
        "description": "Patient self-service check-in: QR codes, identification, waiting room.",
    },
    {
        "name": "Patients",
        "description": "Patient record management: CRUD operations, CURP validation.",
    },
    {
        "name": "Providers",
        "description": "Healthcare provider management: CRUD operations, license validation.",
    },
]

# =============================================================================
# Domain Routers - Phase 2 (Mesopelágica) Complete
# =============================================================================

# Medical AI - Core workflow endpoints
# Includes: workflows, monitor, diarization, audio, transcription_sources, audit
aurity_router.include_router(
    medical_ai.router,
    prefix="/medical-ai",
    tags=["Medical AI"],
)

# Transcription - Audio streaming and job management
# Includes: stream, jobs, end-session, chunks
aurity_router.include_router(
    transcription.router,
    prefix="/transcription",
    tags=["Transcription"],
)

# Prescriptions - Medication catalog and safety checks
# Includes: templates, prescriptions, catalog, interactions, allergies, safety
# Note: Router already has /prescriptions prefix
aurity_router.include_router(
    prescriptions.router,
    tags=["Prescriptions"],
)

# Clinic - Clinic management and waiting room
# Includes: waiting_room, widgets (partial - management, media, tv_content pending)
aurity_router.include_router(
    clinic.router,
    prefix="/clinic",
    tags=["Clinic"],
)

# Assistant - AI chat with personas
# Includes: chat, stream, introduction, history
aurity_router.include_router(
    assistant.router,
    prefix="/assistant",
    tags=["Assistant"],
)

# Timeline - Session history (re-exported from legacy)
# Includes: sessions list, session detail
aurity_router.include_router(
    timeline.router,
    tags=["Timeline"],  # Router already has /timeline prefix
)

# Knowledge Base - Document management (placeholder)
# Note: Legacy has import issues - routes will be added in Phase 3
aurity_router.include_router(
    knowledge_base.router,
    prefix="/knowledge-base",
    tags=["Knowledge Base"],
)

# System - Infrastructure endpoints (re-exported from legacy)
# Includes: disk-usage, llm-status, clear-memory
aurity_router.include_router(
    system.router,
    tags=["System"],  # Router already has /system prefix
)

# Check-in - Patient self-service check-in (FI Receptionist)
# Includes: QR generation, session management, identification, actions, waiting room
# Note: Router already has /checkin prefix
aurity_router.include_router(
    checkin.router,
    tags=["Check-in"],
)

# Patients - Patient record management
# Includes: CRUD operations, CURP validation
# Note: Router already has /patients prefix
aurity_router.include_router(
    patients.router,
    tags=["Patients"],
)

# Providers - Healthcare provider management
# Includes: CRUD operations, license validation
# Note: Router already has /providers prefix
aurity_router.include_router(
    providers.router,
    tags=["Providers"],
)
