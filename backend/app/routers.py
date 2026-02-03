"""Router registration for AURITY API.

Centralizes all router imports and registrations to keep main.py focused
on app configuration and middleware setup.

Author: Bernard Uriza Orozco
Created: 2026-01-06
"""

from __future__ import annotations

from fastapi import FastAPI


def register_routers(public_app: FastAPI, internal_app: FastAPI) -> None:
    """Register all API routers on public and internal sub-apps.

    Args:
        public_app: FastAPI app for public orchestration endpoints (/api/*)
        internal_app: FastAPI app for internal atomic resources (/internal/*)

    Raises:
        ImportError: If a required router module cannot be imported
    """
    # =========================================================================
    # Router Imports (lazy loaded to avoid circular imports)
    # =========================================================================

    # Admin & Auth
    # System Routes
    from backend.app.system_routes import router as system_router
    from backend.api.admin.api.internal.admin.users import router as users_router

    # NOTE: Assistant routers moved to aurity_router (backend.api.domains.aurity.assistant)

    # Audit
    from backend.api.audit.api.internal.audit import router as internal_audit_router
    from backend.api.audit.api.public import audit
    from backend.infrastructure.auth.adapters.fastapi_adapter import auth_router

    # Check-in & Payments
    from backend.api.routers.checkin import checkin
    # NOTE: clinics router moved to aurity_router (backend.api.domains.aurity.clinic)

    # Coder
    from backend.utils.coder.api.internal.fi_coder import router as fi_coder_router

    # Common
    from backend.infrastructure.common.api.internal.exports import router as exports_router
    from backend.infrastructure.common.api.public import notifications

    # KPIs
    from backend.api.routers.kpi.internal.router import router as kpis_router

    # Licensing
    from backend.api.license.api.internal import router as licenses_admin_router
    from backend.api.license.api.public import router as licenses_router

    # LLM
    from backend.api.routers.llm.internal.llm import router as llm_router
    from backend.api.routers.llm.public import llm_models_admin

    # Model Catalog
    from backend.infrastructure.model_catalog.api.public import catalog_admin

    # Observability
    from backend.infrastructure.observability.api import router as observability_router

    # Patients & Providers
    from backend.api.routers.patient.public import patients
    from backend.api.payment.api.public import payments

    # Policy
    from backend.api.policy.api.public import policy
    from backend.api.routers.provider.public import providers

    # Sessions
    from backend.api.routers.session.internal.sessions import router as sessions_router
    from backend.api.routers.session.internal.sessions.finalize import (
        router as sessions_finalize_router,
    )

    # System Resources
    from backend.infrastructure.system.api.public import system_resources
    # NOTE: system_info_router moved to aurity_router (backend.api.domains.aurity.system)

    # Timeline
    from backend.services.timeline.api.internal.timeline import router as timeline_internal_router
    # NOTE: timeline public router moved to aurity_router (backend.api.domains.aurity.timeline)

    # Transcription & Diarization
    from backend.api.routers.transcription.internal.diarization import router as diarization_router
    from backend.api.routers.transcription.internal.transcribe import router as transcribe_router

    # TTS
    from backend.services.tts.api.public import tts
    from backend.api.routers.user.public import user_clinic

    # Triage
    from backend.api.routers.workflow.internal.triage import router as triage_router

    # NOTE: public_workflows_router removed - replaced by aurity_router

    # =========================================================================
    # AURITY Domain API (Phase 3 - Batipelágica)
    # All AURITY-specific routes consolidated under /api/aurity/*
    # =========================================================================
    from backend.api.domains.aurity.router import aurity_router, tags_metadata

    public_app.include_router(aurity_router, prefix="/api")
    public_app.openapi_tags = tags_metadata

    # =========================================================================
    # PUBLIC API Registration (CORS enabled, non-AURITY routes)
    # =========================================================================

    public_app.include_router(auth_router)  # Auth0 Authentication (HIPAA G-003)
    public_app.include_router(patients.router)  # Patient CRUD (FI-DATA-DB-001)
    public_app.include_router(providers.router)  # Provider CRUD (FI-DATA-DB-001)
    public_app.include_router(
        audit.router, prefix="/audit", tags=["Audit"]
    )  # Audit logs (FI-UI-FEAT-206)
    public_app.include_router(policy.router)  # Policy viewer (FI-UI-FEAT-204)
    public_app.include_router(tts.router)  # Text-to-Speech (Azure OpenAI)
    public_app.include_router(checkin.router)  # FI Receptionist Check-in (FI-CHECKIN-001)
    public_app.include_router(payments.router)  # Stripe Payments (FI-CHECKIN-002)
    public_app.include_router(user_clinic.router)  # User-Clinic membership
    public_app.include_router(notifications.router)  # SMS/Email Notifications (FI-CHECKIN-003)
    public_app.include_router(llm_models_admin)  # LLM Models Admin (superadmin CRUD)
    public_app.include_router(catalog_admin.router)  # Model Catalog
    public_app.include_router(system_resources.router)  # System Resources Monitor
    public_app.include_router(observability_router)  # LLM Observability (FI Edge Monitor)
    public_app.include_router(licenses_router)  # License renewal API
    public_app.include_router(licenses_admin_router)  # License generation (superadmin)
    public_app.include_router(system_router)  # Health, version, root endpoints

    # =========================================================================
    # INTERNAL API Registration (atomic resources, AURITY-only)
    # =========================================================================

    internal_app.include_router(internal_audit_router, prefix="/audit", tags=["audit"])
    internal_app.include_router(diarization_router, prefix="/diarization", tags=["diarization"])
    internal_app.include_router(exports_router, prefix="/exports", tags=["exports"])
    internal_app.include_router(timeline_internal_router)  # verify-hash compatibility
    internal_app.include_router(kpis_router, prefix="/kpis", tags=["kpis"])
    internal_app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
    internal_app.include_router(
        sessions_finalize_router, prefix="", tags=["sessions-finalize"]
    )  # Session finalization + encryption + diarization
    internal_app.include_router(triage_router, prefix="/triage", tags=["triage"])
    internal_app.include_router(transcribe_router, prefix="/transcribe", tags=["transcribe"])
    internal_app.include_router(llm_router)  # Ultra observable LLM layer
    internal_app.include_router(users_router, tags=["admin"])  # Admin user management
    internal_app.include_router(
        fi_coder_router, prefix="/fi_coder", tags=["fi_coder"]
    )  # FI Coder task orchestrator


def init_observability() -> None:
    """Initialize observability database.

    Non-critical - logs to structlog if it fails.
    """
    try:
        from backend.infrastructure.observability import init_observability_db

        init_observability_db()
    except Exception:
        pass  # Non-critical, log to structlog in observability module
