"""AURITY App Router - Aggregates all domain routers under /api/aurity/.

This is the main router for the AURITY telemedicine app.
All domain routers are included here with their respective prefixes and tags.

Usage:
    from backend.api.domains.aurity.router import aurity_router, tags_metadata

    app.include_router(aurity_router, prefix="/api")
    app.openapi_tags = tags_metadata
"""

from __future__ import annotations

from fastapi import APIRouter

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
]

# =============================================================================
# Domain routers will be included here in Phase 2 (Mesopelágica)
# =============================================================================
#
# from backend.api.domains.aurity import (
#     medical_ai,
#     clinic,
#     transcription,
#     assistant,
#     prescriptions,
#     timeline,
#     knowledge_base,
#     system,
# )
#
# aurity_router.include_router(
#     medical_ai.router,
#     prefix="/medical-ai",
#     tags=["Medical AI"]
# )
# aurity_router.include_router(
#     clinic.router,
#     prefix="/clinic",
#     tags=["Clinic"]
# )
# aurity_router.include_router(
#     transcription.router,
#     prefix="/transcription",
#     tags=["Transcription"]
# )
# aurity_router.include_router(
#     assistant.router,
#     prefix="/assistant",
#     tags=["Assistant"]
# )
# aurity_router.include_router(
#     prescriptions.router,
#     prefix="/prescriptions",
#     tags=["Prescriptions"]
# )
# aurity_router.include_router(
#     timeline.router,
#     prefix="/timeline",
#     tags=["Timeline"]
# )
# aurity_router.include_router(
#     knowledge_base.router,
#     prefix="/knowledge-base",
#     tags=["Knowledge Base"]
# )
# aurity_router.include_router(
#     system.router,
#     prefix="/system",
#     tags=["System"]
# )
