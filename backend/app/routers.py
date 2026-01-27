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

    # Assistant & Personas
    from backend.core.services.assistant.api.public import aurity_personas

    # Audit
    from backend.api.audit.api.internal.audit import router as internal_audit_router
    from backend.api.audit.api.public import audit
    from backend.core.infrastructure.auth.adapters.fastapi_adapter import auth_router

    # Check-in & Payments
    from backend.core.services.checkin.api.public import checkin
    from backend.core.domain.clinic.api.public import clinics

    # Coder
    from backend.utils.coder.api.internal.fi_coder import router as fi_coder_router

    # Common
    from backend.utils.common.api.internal.exports import router as exports_router
    from backend.utils.common.api.public import notifications

    # KPIs
    from backend.core.services.kpi.api.internal.kpis import router as kpis_router

    # Licensing
    from backend.api.license.api.internal import router as licenses_admin_router
    from backend.api.license.api.public import router as licenses_router

    # LLM
    from backend.core.services.llm.api.internal.llm import router as llm_router
    from backend.core.services.llm.api.public import llm_models_admin

    # Model Catalog
    from backend.core.infrastructure.model_catalog.api.public import catalog_admin

    # Observability
    from backend.core.infrastructure.observability.api import router as observability_router

    # Patients & Providers
    from backend.core.domain.patient.api.public import patients
    from backend.api.payment.api.public import payments

    # Policy
    from backend.api.policy.api.public import policy
    from backend.core.domain.provider.api.public import providers

    # Sessions
    from backend.core.domain.session.api.internal.sessions import router as sessions_router
    from backend.core.domain.session.api.internal.sessions.finalize import (
        router as sessions_finalize_router,
    )

    # System Resources
    from backend.utils.system.api.public import system_resources

    # Timeline
    from backend.core.services.timeline.api.internal.timeline import router as timeline_internal_router
    from backend.core.services.timeline.api.public import timeline

    # Transcription & Diarization
    from backend.core.services.transcription.api.internal.diarization import router as diarization_router
    from backend.core.services.transcription.api.internal.transcribe import router as transcribe_router

    # TTS
    from backend.core.services.tts.api.public import tts
    from backend.core.domain.user.api.public import user_clinic

    # Triage
    from backend.core.services.workflow.api.internal.triage import router as triage_router

    # Workflows
    from backend.core.services.workflow.api.public.workflows_router import (
        router as public_workflows_router,
    )

    # =========================================================================
    # PUBLIC API Registration (CORS enabled, orchestrators)
    # =========================================================================

    public_app.include_router(auth_router)  # Auth0 Authentication (HIPAA G-003)
    public_app.include_router(public_workflows_router)  # AURITY orchestrator
    public_app.include_router(timeline.router)  # Timeline/sessions listing
    public_app.include_router(aurity_personas.router)  # Personas list (public)
    public_app.include_router(patients.router)  # Patient CRUD (FI-DATA-DB-001)
    public_app.include_router(providers.router)  # Provider CRUD (FI-DATA-DB-001)
    public_app.include_router(
        audit.router, prefix="/audit", tags=["Audit"]
    )  # Audit logs (FI-UI-FEAT-206)
    public_app.include_router(policy.router)  # Policy viewer (FI-UI-FEAT-204)
    public_app.include_router(tts.router)  # Text-to-Speech (Azure OpenAI)
    public_app.include_router(checkin.router)  # FI Receptionist Check-in (FI-CHECKIN-001)
    public_app.include_router(payments.router)  # Stripe Payments (FI-CHECKIN-002)
    public_app.include_router(clinics.router)  # Clinic/Doctor CRUD (FI-CHECKIN-002)
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
        from backend.core.infrastructure.observability import init_observability_db

        init_observability_db()
    except Exception:
        pass  # Non-critical, log to structlog in observability module
