#!/bin/bash
# Update backend/app/main.py to use new package structure

set -e

echo "Creating backup..."
cp app/main.py app/main.py.bak

echo "Updating imports in main.py..."

# The main.py file has complex imports. We need to replace:
# 1. from backend.api import internal, public
# 2. from backend.api.internal.admin import users_router  
# 3. from backend.api.public import (audit, catalog_admin, ...)
# 4. from backend.api.public.workflows import aurity_personas, timeline

# This is tricky because we're replacing module imports with direct imports.
# The new structure has routers in backend/src/fi_DOMAIN/api/public/*.py

# First, let me create a new version of the imports section
cat > /tmp/main_imports_new.py << 'EOF'
        # Import all routers from new package structure
        from backend.src.fi_audit.api.public import audit
        from backend.src.fi_admin.api.internal.admin import users as admin_users
        from backend.src.fi_auth.adapters.fastapi_adapter import auth_router
        from backend.src.fi_checkin.api.public import checkin
        from backend.src.fi_clinic.api.public import clinics
        from backend.src.fi_common.api.public import notifications
        from backend.src.fi_model_catalog.api.public import catalog_admin, llm_models_admin
        from backend.src.fi_patient.api.public import patients
        from backend.src.fi_payment.api.public import payments
        from backend.src.fi_policy.api.public import policy
        from backend.src.fi_provider.api.public import providers
        from backend.src.fi_system.api.public import system_resources
        from backend.src.fi_tts.api.public import tts
        from backend.src.fi_user.api.public import user_clinic
        from backend.src.fi_llm.api.public import personas_admin
        from backend.src.fi_timeline.api.public.workflows import timeline
        from backend.src.fi_assistant.api.public.workflows import aurity_personas
        
        # Import internal API routers
        from backend.src.fi_audit.api.internal.audit import router as internal_audit_router
        from backend.src.fi_session.api.internal import (
            diarization,
            exports,
            sessions,
        )
        from backend.src.fi_session.api.internal.sessions import (
            checkpoint as sessions_checkpoint,
            finalize as sessions_finalize,
        )
        from backend.src.fi_kpi.api.internal import kpis
        from backend.src.fi_llm.api.internal import llm as internal_llm
        from backend.src.fi_transcription.api.internal import transcribe
        from backend.src.fi_workflow.api.internal import triage
        from backend.src.fi_timeline.api.internal import timeline as internal_timeline
        from backend.src.fi_coder.api.internal import fi_coder
        
        # Import public workflows router
        from backend.src.fi_assistant.api.public import workflows as public_workflows
EOF

echo "✓ New imports template created"
echo "⚠️  Manual update required for main.py - structure too complex for automated replacement"
echo ""
echo "Recommendation: This cutover requires careful manual editing of main.py"
echo "The file uses dynamic module access (internal.audit.router, public.workflows.router)"
echo "which doesn't map cleanly to the new flat structure."

