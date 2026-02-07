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

    # Payments
    # NOTE: checkin router moved to aurity_router (backend.api.domains.aurity.checkin)
    # NOTE: clinics router moved to aurity_router (backend.api.domains.aurity.clinic)

    # Coder
    from backend.utils.coder.api.internal.fi_coder import router as fi_coder_router

    # Common
    from backend.infrastructure.common.api.internal.exports import router as exports_router
    from backend.infrastructure.common.api.public import notifications

    # KPIs (migrated to infrastructure/)
    from backend.infrastructure.kpi.api.internal.router import router as kpis_router

    # Downloads (GitHub release proxy for private repo)
    from backend.api.downloads.api.public import router as downloads_router

    # Licensing
    from backend.api.license.api.internal import router as licenses_admin_router
    from backend.api.license.api.public import router as licenses_router

    # LLM
    from backend.infrastructure.llm.api.internal import router as llm_router
    from backend.infrastructure.model_catalog.api.public.llm_models_admin import (
        router as llm_models_admin_router,
    )

    # Model Catalog
    from backend.infrastructure.model_catalog.api.public import catalog_admin

    # Observability
    from backend.infrastructure.observability.api import router as observability_router

    # Providers & Payments
    # NOTE: patients router moved to aurity_router (backend.api.domains.aurity.patients)
    from backend.api.payment.api.public import payments

    # Policy
    from backend.api.policy.api.public import policy
    # NOTE: providers router moved to aurity_router (backend.api.domains.aurity.providers)

    # Sessions (migrated to infrastructure/)
    from backend.infrastructure.session.api.internal import (
        sessions_router,
        finalize_router as sessions_finalize_router,
    )

    # System Resources
    from backend.infrastructure.system.api.public import system_resources
    # NOTE: system_info_router moved to aurity_router (backend.api.domains.aurity.system)

    # Timeline
    from backend.services.timeline.api.internal.timeline import router as timeline_internal_router
    # NOTE: timeline public router moved to aurity_router (backend.api.domains.aurity.timeline)

    # Transcription & Diarization (migrated to infrastructure/)
    from backend.infrastructure.transcription.api.internal import (
        diarization_router,
        transcribe_router,
    )

    # TTS
    from backend.services.tts.api.public import tts
    # NOTE: user_clinic router moved to aurity_router (backend.api.domains.aurity.clinic.user_clinic)

    # Triage (migrated to infrastructure/)
    from backend.infrastructure.workflow.api.internal import triage_router

    # NOTE: public_workflows_router removed - replaced by aurity_router

    # =========================================================================
    # AURITY Domain API (Phase 3 - Batipelágica)
    # All AURITY-specific routes consolidated under /api/aurity/*
    # =========================================================================
    from backend.api.domains.aurity.router import aurity_router, tags_metadata

    # FIXED: Don't add "/api" prefix since public_app is already mounted at "/api"
    # The aurity_router has prefix="/aurity" internally, resulting in /api/aurity/*
    public_app.include_router(aurity_router)
    public_app.openapi_tags = tags_metadata

    # =========================================================================
    # PUBLIC API Registration (CORS enabled, non-AURITY routes)
    # =========================================================================

    public_app.include_router(auth_router)  # JWT Authentication
    # NOTE: patients.router removed - now in aurity_router at /api/aurity/patients/*
    # NOTE: providers.router removed - now in aurity_router at /api/aurity/providers/*
    public_app.include_router(
        audit.router, prefix="/audit", tags=["Audit"]
    )  # Audit logs (FI-UI-FEAT-206)
    public_app.include_router(policy.router)  # Policy viewer (FI-UI-FEAT-204)
    public_app.include_router(tts.router)  # Text-to-Speech (Azure OpenAI)
    # NOTE: checkin.router removed - now in aurity_router at /api/aurity/checkin/*
    public_app.include_router(payments.router)  # Stripe Payments (FI-CHECKIN-002)
    # NOTE: user_clinic.router removed - now in aurity_router at /api/aurity/clinic/users/me/*
    public_app.include_router(notifications.router)  # SMS/Email Notifications (FI-CHECKIN-003)
    public_app.include_router(llm_models_admin_router)  # LLM Models Admin (superadmin CRUD)
    public_app.include_router(catalog_admin.router)  # Model Catalog
    public_app.include_router(system_resources.router)  # System Resources Monitor
    public_app.include_router(observability_router)  # LLM Observability (FI Edge Monitor)
    public_app.include_router(licenses_router)  # License renewal API
    public_app.include_router(licenses_admin_router)  # License generation (superadmin)
    public_app.include_router(downloads_router)  # GitHub release proxy (private repo)
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
