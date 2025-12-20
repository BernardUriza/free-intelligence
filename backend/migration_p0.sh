#!/bin/bash

# Free Intelligence Backend Migration Script (Phase 0)
# This script automates the migration of backend services and APIs
# from the old structure to the new modular structure.

set -e  # Exit immediately if a command exits with a non-zero status

echo "Starting Free Intelligence Backend Migration (Phase 0)"
echo "====================================================="

# Define source directories
SERVICES_SRC_DIR="./backend/services"
API_SRC_DIR="./backend/api"

# Define target directory
TARGET_BASE_DIR="./backend/src"

# Function to create directory if it doesn't exist
create_dir() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        echo "Created directory: $1"
    fi
}

# Function to copy file with directory creation
copy_file() {
    local src="$1"
    local dest="$2"
    
    # Create destination directory if needed
    local dest_dir=$(dirname "$dest")
    create_dir "$dest_dir"
    
    # Copy the file
    cp "$src" "$dest"
    echo "Copied: $src -> $dest"
}

# Function to copy directory recursively
copy_dir() {
    local src="$1"
    local dest="$2"
    
    create_dir "$dest"
    cp -r "$src"/* "$dest/"
    echo "Copied directory: $src -> $dest"
}

# Function to update import statements in files
update_imports() {
    local dir="$1"
    echo "Updating import statements in: $dir"
    
    # Find all Python files in the directory and update import paths
    find "$dir" -name "*.py" -exec sed -i.bak -E \
    's/from backend\.services\.(.*) import/from fi_\1.services import/g; \
     s/import backend\.services\.(.*)/import fi_\1.services/g; \
     s/from backend\.api\.(public|internal)\.(.*) import/from fi_\2.api.\1 import/g; \
     s/import backend\.api\.(public|internal)\.(.*)/import fi_\2.api.\1/g' {} \;
    
    # Remove backup files created by sed
    find "$dir" -name "*.py.bak" -delete
}

# Confirmation prompt
read -p "This script will migrate backend services and APIs to a new structure. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

echo "Creating target directory structure..."
create_dir "$TARGET_BASE_DIR"

# SERVICES MIGRATION
echo
echo "Migrating services..."

# Mapping individual services to domains (partial list - full mapping would be extensive)
# Authentication & Management
create_dir "$TARGET_BASE_DIR/fi_auth/services"
copy_file "$SERVICES_SRC_DIR/auth0_management.py" "$TARGET_BASE_DIR/fi_auth/services/auth0_management.py"
copy_file "$SERVICES_SRC_DIR/gatekeeper.py" "$TARGET_BASE_DIR/fi_auth/services/gatekeeper.py"

# Storage & Corpus
create_dir "$TARGET_BASE_DIR/fi_storage/services"
create_dir "$TARGET_BASE_DIR/fi_storage/services/adapters"
create_dir "$TARGET_BASE_DIR/fi_storage/services/ports"
copy_file "$SERVICES_SRC_DIR/corpus_service.py" "$TARGET_BASE_DIR/fi_storage/services/corpus_service.py"
copy_file "$SERVICES_SRC_DIR/trace_store.py" "$TARGET_BASE_DIR/fi_storage/services/trace_store.py"
copy_file "$SERVICES_SRC_DIR/checkpoint/adapters/hdf5_repository.py" "$TARGET_BASE_DIR/fi_storage/services/adapters/hdf5_repository.py"
copy_file "$SERVICES_SRC_DIR/checkpoint/ports/audio_repository.py" "$TARGET_BASE_DIR/fi_storage/services/ports/audio_repository.py"
copy_file "$SERVICES_SRC_DIR/checkpoint/adapters/ffmpeg_concatenator.py" "$TARGET_BASE_DIR/fi_storage/services/adapters/ffmpeg_concatenator.py"
copy_file "$SERVICES_SRC_DIR/checkpoint/ports/audio_concatenator.py" "$TARGET_BASE_DIR/fi_storage/services/ports/audio_concatenator.py"

# LLM & AI
create_dir "$TARGET_BASE_DIR/fi_llm/services"
create_dir "$TARGET_BASE_DIR/fi_llm/services/persona"
copy_file "$SERVICES_SRC_DIR/llm_model_service.py" "$TARGET_BASE_DIR/fi_llm/services/llm_model_service.py"
copy_file "$SERVICES_SRC_DIR/llm/conversation_memory.py" "$TARGET_BASE_DIR/fi_llm/services/conversation_memory.py"
copy_file "$SERVICES_SRC_DIR/llm/persona_manager.py" "$TARGET_BASE_DIR/fi_llm/services/persona_manager.py"
copy_file "$SERVICES_SRC_DIR/llm/persona/config.py" "$TARGET_BASE_DIR/fi_llm/services/persona/config.py"
copy_file "$SERVICES_SRC_DIR/llm/persona/constants.py" "$TARGET_BASE_DIR/fi_llm/services/persona/constants.py"
copy_file "$SERVICES_SRC_DIR/llm/persona/exceptions.py" "$TARGET_BASE_DIR/fi_llm/services/persona/exceptions.py"
copy_file "$SERVICES_SRC_DIR/llm/persona/manager.py" "$TARGET_BASE_DIR/fi_llm/services/persona/manager.py"
copy_file "$SERVICES_SRC_DIR/llm/persona/prompt_builder.py" "$TARGET_BASE_DIR/fi_llm/services/persona/prompt_builder.py"
copy_file "$SERVICES_SRC_DIR/llm/persona/router.py" "$TARGET_BASE_DIR/fi_llm/services/persona/router.py"
copy_file "$SERVICES_SRC_DIR/llm/persona/schemas.py" "$TARGET_BASE_DIR/fi_llm/services/persona/schemas.py"

# Model Catalog
create_dir "$TARGET_BASE_DIR/fi_model_catalog/services"
create_dir "$TARGET_BASE_DIR/fi_model_catalog/services/sources"
copy_file "$SERVICES_SRC_DIR/model_catalog/catalog_service.py" "$TARGET_BASE_DIR/fi_model_catalog/services/catalog_service.py"
copy_file "$SERVICES_SRC_DIR/model_catalog/sources/base.py" "$TARGET_BASE_DIR/fi_model_catalog/services/sources/base.py"
copy_file "$SERVICES_SRC_DIR/model_catalog/sources/gpt4all_source.py" "$TARGET_BASE_DIR/fi_model_catalog/services/sources/gpt4all_source.py"
copy_file "$SERVICES_SRC_DIR/model_catalog/sources/huggingface_source.py" "$TARGET_BASE_DIR/fi_model_catalog/services/sources/huggingface_source.py"
copy_file "$SERVICES_SRC_DIR/model_catalog/sources/ollama_source.py" "$TARGET_BASE_DIR/fi_model_catalog/services/sources/ollama_source.py"

# Transcription
create_dir "$TARGET_BASE_DIR/fi_transcription/services"
copy_file "$SERVICES_SRC_DIR/transcription_service.py" "$TARGET_BASE_DIR/fi_transcription/services/transcription_service.py"
copy_file "$SERVICES_SRC_DIR/transcription/service.py" "$TARGET_BASE_DIR/fi_transcription/services/service.py"
copy_file "$SERVICES_SRC_DIR/transcription/validators.py" "$TARGET_BASE_DIR/fi_transcription/services/validators.py"
copy_file "$SERVICES_SRC_DIR/transcription/whisper.py" "$TARGET_BASE_DIR/fi_transcription/services/whisper.py"
copy_file "$SERVICES_SRC_DIR/deepgram_service.py" "$TARGET_BASE_DIR/fi_transcription/services/deepgram_service.py"

# SOAP Generation
create_dir "$TARGET_BASE_DIR/fi_soap_generation/services"
copy_file "$SERVICES_SRC_DIR/soap_generation/USAGE_EXAMPLES.py" "$TARGET_BASE_DIR/fi_soap_generation/services/USAGE_EXAMPLES.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/completeness.py" "$TARGET_BASE_DIR/fi_soap_generation/services/completeness.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/complexity_analyzer.py" "$TARGET_BASE_DIR/fi_soap_generation/services/complexity_analyzer.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/decisional_middleware.py" "$TARGET_BASE_DIR/fi_soap_generation/services/decisional_middleware.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/defaults.py" "$TARGET_BASE_DIR/fi_soap_generation/services/defaults.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/llm_client.py" "$TARGET_BASE_DIR/fi_soap_generation/services/llm_client.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/prompt_builder.py" "$TARGET_BASE_DIR/fi_soap_generation/services/prompt_builder.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/reader.py" "$TARGET_BASE_DIR/fi_soap_generation/services/reader.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/response_parser.py" "$TARGET_BASE_DIR/fi_soap_generation/services/response_parser.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/soap_builder.py" "$TARGET_BASE_DIR/fi_soap_generation/services/soap_builder.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/soap_generation_service.py" "$TARGET_BASE_DIR/fi_soap_generation/services/soap_generation_service.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/soap_models.py" "$TARGET_BASE_DIR/fi_soap_generation/services/soap_models.py"
copy_file "$SERVICES_SRC_DIR/soap_generation/tests.py" "$TARGET_BASE_DIR/fi_soap_generation/services/tests.py"

# Timeline
create_dir "$TARGET_BASE_DIR/fi_timeline/services"
copy_file "$SERVICES_SRC_DIR/timeline/api.py" "$TARGET_BASE_DIR/fi_timeline/services/timeline/api.py"
copy_file "$SERVICES_SRC_DIR/timeline/auto.py" "$TARGET_BASE_DIR/fi_timeline/services/timeline/auto.py"
copy_file "$SERVICES_SRC_DIR/timeline/demo.py" "$TARGET_BASE_DIR/fi_timeline/services/timeline/demo.py"

# Session Management
create_dir "$TARGET_BASE_DIR/fi_session/services"
copy_file "$SERVICES_SRC_DIR/session_service.py" "$TARGET_BASE_DIR/fi_session/services/session_service.py"

# TTS (Text-to-Speech)
create_dir "$TARGET_BASE_DIR/fi_tts/services"
copy_file "$SERVICES_SRC_DIR/tts_service.py" "$TARGET_BASE_DIR/fi_tts/services/tts_service.py"
copy_file "$SERVICES_SRC_DIR/tts_openai.py" "$TARGET_BASE_DIR/fi_tts/services/tts_openai.py"
copy_file "$SERVICES_SRC_DIR/tts_openai_steerable.py" "$TARGET_BASE_DIR/fi_tts/services/tts_openai_steerable.py"
copy_file "$SERVICES_SRC_DIR/tts_unified.py" "$TARGET_BASE_DIR/fi_tts/services/tts_unified.py"

# Workflow Management
create_dir "$TARGET_BASE_DIR/fi_workflow/services"
copy_file "$SERVICES_SRC_DIR/workflow_router.py" "$TARGET_BASE_DIR/fi_workflow/services/workflow_router.py"
copy_file "$SERVICES_SRC_DIR/workflow_tracker.py" "$TARGET_BASE_DIR/fi_workflow/services/workflow_tracker.py"
copy_file "$SERVICES_SRC_DIR/triage_service.py" "$TARGET_BASE_DIR/fi_workflow/services/triage_service.py"

# Checkpoint Management
create_dir "$TARGET_BASE_DIR/fi_checkpoint/services/usecases"
copy_file "$SERVICES_SRC_DIR/checkpoint/usecases/checkpoint_use_case.py" "$TARGET_BASE_DIR/fi_checkpoint/services/usecases/checkpoint_use_case.py"

# Common/Utility Services
create_dir "$TARGET_BASE_DIR/fi_common/services"
copy_file "$SERVICES_SRC_DIR/__init__.py" "$TARGET_BASE_DIR/fi_common/services/__init__.py"
copy_file "$SERVICES_SRC_DIR/chat_chunk_handler.py" "$TARGET_BASE_DIR/fi_common/services/chat_chunk_handler.py"
copy_file "$SERVICES_SRC_DIR/chunk_handler.py" "$TARGET_BASE_DIR/fi_common/services/chunk_handler.py"
copy_file "$SERVICES_SRC_DIR/chunk_handler_factory.py" "$TARGET_BASE_DIR/fi_common/services/chunk_handler_factory.py"
copy_file "$SERVICES_SRC_DIR/medical_chunk_handler.py" "$TARGET_BASE_DIR/fi_common/services/medical_chunk_handler.py"
copy_file "$SERVICES_SRC_DIR/notifications.py" "$TARGET_BASE_DIR/fi_common/services/notifications.py"
copy_file "$SERVICES_SRC_DIR/export_service.py" "$TARGET_BASE_DIR/fi_common/services/export_service.py"
copy_file "$SERVICES_SRC_DIR/evidence_service.py" "$TARGET_BASE_DIR/fi_common/services/evidence_service.py"
copy_file "$SERVICES_SRC_DIR/diagnostics_service.py" "$TARGET_BASE_DIR/fi_common/services/diagnostics_service.py"

# Domain-Specific Services
create_dir "$TARGET_BASE_DIR/fi_checkin/services"
copy_file "$SERVICES_SRC_DIR/checkin_conversation.py" "$TARGET_BASE_DIR/fi_checkin/services/checkin_conversation.py"

create_dir "$TARGET_BASE_DIR/fi_audit/services"
copy_file "$SERVICES_SRC_DIR/audit_service.py" "$TARGET_BASE_DIR/fi_audit/services/audit_service.py"

create_dir "$TARGET_BASE_DIR/fi_kpi/services"
copy_file "$SERVICES_SRC_DIR/persona_metrics_service.py" "$TARGET_BASE_DIR/fi_kpi/services/persona_metrics_service.py"
copy_file "$SERVICES_SRC_DIR/kpis_aggregator.py" "$TARGET_BASE_DIR/fi_kpi/services/kpis_aggregator.py"

create_dir "$TARGET_BASE_DIR/fi_system/services"
copy_file "$SERVICES_SRC_DIR/system_health_service.py" "$TARGET_BASE_DIR/fi_system/services/system_health_service.py"

# API MIGRATION
echo
echo "Migrating API endpoints..."

# Public APIs
create_dir "$TARGET_BASE_DIR/fi_checkin/api/public"
copy_file "$API_SRC_DIR/public/checkin.py" "$TARGET_BASE_DIR/fi_checkin/api/public/checkin.py"

create_dir "$TARGET_BASE_DIR/fi_tts/api/public"
copy_file "$API_SRC_DIR/public/tts.py" "$TARGET_BASE_DIR/fi_tts/api/public/tts.py"

create_dir "$TARGET_BASE_DIR/fi_patient/api/public"
copy_file "$API_SRC_DIR/public/patients.py" "$TARGET_BASE_DIR/fi_patient/api/public/patients.py"

create_dir "$TARGET_BASE_DIR/fi_provider/api/public"
copy_file "$API_SRC_DIR/public/providers.py" "$TARGET_BASE_DIR/fi_provider/api/public/providers.py"

create_dir "$TARGET_BASE_DIR/fi_clinic/api/public"
copy_file "$API_SRC_DIR/public/clinics.py" "$TARGET_BASE_DIR/fi_clinic/api/public/clinics.py"

create_dir "$TARGET_BASE_DIR/fi_user/api/public"
copy_file "$API_SRC_DIR/public/user_clinic.py" "$TARGET_BASE_DIR/fi_user/api/public/user_clinic.py"

create_dir "$TARGET_BASE_DIR/fi_payment/api/public"
copy_file "$API_SRC_DIR/public/payments.py" "$TARGET_BASE_DIR/fi_payment/api/public/payments.py"

create_dir "$TARGET_BASE_DIR/fi_common/api/public"
copy_file "$API_SRC_DIR/public/notifications.py" "$TARGET_BASE_DIR/fi_common/api/public/notifications.py"

create_dir "$TARGET_BASE_DIR/fi_policy/api/public"
copy_file "$API_SRC_DIR/public/policy.py" "$TARGET_BASE_DIR/fi_policy/api/public/policy.py"

create_dir "$TARGET_BASE_DIR/fi_system/api/public"
copy_file "$API_SRC_DIR/public/system_resources.py" "$TARGET_BASE_DIR/fi_system/api/public/system_resources.py"
copy_file "$API_SRC_DIR/public/system/router.py" "$TARGET_BASE_DIR/fi_system/api/public/system/router.py"

create_dir "$TARGET_BASE_DIR/fi_audit/api/public"
copy_file "$API_SRC_DIR/public/audit.py" "$TARGET_BASE_DIR/fi_audit/api/public/audit.py"

create_dir "$TARGET_BASE_DIR/fi_model_catalog/api/public"
copy_file "$API_SRC_DIR/public/catalog_admin.py" "$TARGET_BASE_DIR/fi_model_catalog/api/public/catalog_admin.py"
copy_file "$API_SRC_DIR/public/llm_models_admin.py" "$TARGET_BASE_DIR/fi_model_catalog/api/public/llm_models_admin.py"

create_dir "$TARGET_BASE_DIR/fi_llm/api/public"
copy_file "$API_SRC_DIR/public/personas_admin.py" "$TARGET_BASE_DIR/fi_llm/api/public/personas_admin.py"

# Workflows subdomain (partial mapping due to complexity)
create_dir "$TARGET_BASE_DIR/fi_assistant/api/public"
copy_file "$API_SRC_DIR/public/workflows/assistant.py" "$TARGET_BASE_DIR/fi_assistant/api/public/assistant.py"
copy_file "$API_SRC_DIR/public/workflows/assistant_schemas.py" "$TARGET_BASE_DIR/fi_assistant/api/public/assistant_schemas.py"
copy_file "$API_SRC_DIR/public/workflows/assistant_history.py" "$TARGET_BASE_DIR/fi_assistant/api/public/assistant_history.py"
copy_file "$API_SRC_DIR/public/workflows/assistant_websocket.py" "$TARGET_BASE_DIR/fi_assistant/api/public/assistant_websocket.py"
copy_file "$API_SRC_DIR/public/workflows/aurity_personas.py" "$TARGET_BASE_DIR/fi_assistant/api/public/aurity_personas.py"

create_dir "$TARGET_BASE_DIR/fi_clinic/api/public"
copy_file "$API_SRC_DIR/public/workflows/clinic_media.py" "$TARGET_BASE_DIR/fi_clinic/api/public/clinic_media.py"

create_dir "$TARGET_BASE_DIR/fi_document/api/public"
copy_file "$API_SRC_DIR/public/workflows/documents.py" "$TARGET_BASE_DIR/fi_document/api/public/documents.py"

create_dir "$TARGET_BASE_DIR/fi_analysis/api/public"
copy_file "$API_SRC_DIR/public/workflows/emotional_analysis.py" "$TARGET_BASE_DIR/fi_analysis/api/public/emotional_analysis.py"

create_dir "$TARGET_BASE_DIR/fi_evidence/api/public"
copy_file "$API_SRC_DIR/public/workflows/evidence.py" "$TARGET_BASE_DIR/fi_evidence/api/public/evidence.py"

create_dir "$TARGET_BASE_DIR/fi_kpi/api/public"
copy_file "$API_SRC_DIR/public/workflows/kpis.py" "$TARGET_BASE_DIR/fi_kpi/api/public/kpis.py"

create_dir "$TARGET_BASE_DIR/fi_memory/api/public"
copy_file "$API_SRC_DIR/public/workflows/longitudinal_memory.py" "$TARGET_BASE_DIR/fi_memory/api/public/longitudinal_memory.py"

create_dir "$TARGET_BASE_DIR/fi_order/api/public"
copy_file "$API_SRC_DIR/public/workflows/orders.py" "$TARGET_BASE_DIR/fi_order/api/public/orders.py"

create_dir "$TARGET_BASE_DIR/fi_session/api/public"
copy_file "$API_SRC_DIR/public/workflows/sessions.py" "$TARGET_BASE_DIR/fi_session/api/public/sessions.py"
copy_file "$API_SRC_DIR/public/workflows/sessions_list.py" "$TARGET_BASE_DIR/fi_session/api/public/sessions_list.py"

create_dir "$TARGET_BASE_DIR/fi_soap_generation/api/public"
copy_file "$API_SRC_DIR/public/workflows/soap.py" "$TARGET_BASE_DIR/fi_soap_generation/api/public/soap.py"

create_dir "$TARGET_BASE_DIR/fi_system/api/public"
copy_file "$API_SRC_DIR/public/workflows/system.py" "$TARGET_BASE_DIR/fi_system/api/public/system.py"

create_dir "$TARGET_BASE_DIR/fi_timeline/api/public"
copy_file "$API_SRC_DIR/public/workflows/timeline.py" "$TARGET_BASE_DIR/fi_timeline/api/public/timeline.py"

create_dir "$TARGET_BASE_DIR/fi_transcription/api/public"
copy_file "$API_SRC_DIR/public/workflows/transcription.py" "$TARGET_BASE_DIR/fi_transcription/api/public/transcription.py"

create_dir "$TARGET_BASE_DIR/fi_content/api/public"
copy_file "$API_SRC_DIR/public/workflows/tv_content_seeds.py" "$TARGET_BASE_DIR/fi_content/api/public/tv_content_seeds.py"

create_dir "$TARGET_BASE_DIR/fi_workflow/api/public"
copy_file "$API_SRC_DIR/public/workflows/waiting_room.py" "$TARGET_BASE_DIR/fi_workflow/api/public/waiting_room.py"

create_dir "$TARGET_BASE_DIR/fi_widget/api/public"
copy_file "$API_SRC_DIR/public/workflows/widget_configs.py" "$TARGET_BASE_DIR/fi_widget/api/public/widget_configs.py"

# Copy workflows subdirectories
create_dir "$TARGET_BASE_DIR/fi_assistant/api/public/assistant"
copy_dir "$API_SRC_DIR/public/workflows/assistant" "$TARGET_BASE_DIR/fi_assistant/api/public/assistant"

create_dir "$TARGET_BASE_DIR/fi_session/api/public/sessions_pkg"
copy_dir "$API_SRC_DIR/public/workflows/sessions_pkg" "$TARGET_BASE_DIR/fi_session/api/public/sessions_pkg"

create_dir "$TARGET_BASE_DIR/fi_common/api/public/models"
copy_dir "$API_SRC_DIR/public/workflows/models" "$TARGET_BASE_DIR/fi_common/api/public/models"

create_dir "$TARGET_BASE_DIR/fi_workflow/api/public/services"
copy_dir "$API_SRC_DIR/public/workflows/services" "$TARGET_BASE_DIR/fi_workflow/api/public/services"

# Internal APIs
create_dir "$TARGET_BASE_DIR/fi_admin/api/internal/admin"
copy_dir "$API_SRC_DIR/internal/admin" "$TARGET_BASE_DIR/fi_admin/api/internal/admin"

create_dir "$TARGET_BASE_DIR/fi_audit/api/internal/audit"
copy_dir "$API_SRC_DIR/internal/audit" "$TARGET_BASE_DIR/fi_audit/api/internal/audit"

create_dir "$TARGET_BASE_DIR/fi_transcription/api/internal/diarization"
copy_dir "$API_SRC_DIR/internal/diarization" "$TARGET_BASE_DIR/fi_transcription/api/internal/diarization"

create_dir "$TARGET_BASE_DIR/fi_common/api/internal/exports"
copy_dir "$API_SRC_DIR/internal/exports" "$TARGET_BASE_DIR/fi_common/api/internal/exports"

create_dir "$TARGET_BASE_DIR/fi_coder/api/internal/fi_coder"
copy_dir "$API_SRC_DIR/internal/fi_coder" "$TARGET_BASE_DIR/fi_coder/api/internal/fi_coder"

create_dir "$TARGET_BASE_DIR/fi_kpi/api/internal/kpis"
copy_dir "$API_SRC_DIR/internal/kpis" "$TARGET_BASE_DIR/fi_kpi/api/internal/kpis"

create_dir "$TARGET_BASE_DIR/fi_llm/api/internal/llm"
copy_dir "$API_SRC_DIR/internal/llm" "$TARGET_BASE_DIR/fi_llm/api/internal/llm"

create_dir "$TARGET_BASE_DIR/fi_session/api/internal/sessions"
copy_dir "$API_SRC_DIR/internal/sessions" "$TARGET_BASE_DIR/fi_session/api/internal/sessions"

create_dir "$TARGET_BASE_DIR/fi_timeline/api/internal/timeline"
copy_dir "$API_SRC_DIR/internal/timeline" "$TARGET_BASE_DIR/fi_timeline/api/internal/timeline"

create_dir "$TARGET_BASE_DIR/fi_transcription/api/internal/transcribe"
copy_dir "$API_SRC_DIR/internal/transcribe" "$TARGET_BASE_DIR/fi_transcription/api/internal/transcribe"

create_dir "$TARGET_BASE_DIR/fi_workflow/api/internal/triage"
copy_dir "$API_SRC_DIR/internal/triage" "$TARGET_BASE_DIR/fi_workflow/api/internal/triage"

# Update import statements in all migrated files
echo
echo "Updating import statements in migrated files..."
update_imports "$TARGET_BASE_DIR"

echo
echo "Migration completed!"
echo "====================="
echo "Summary:"
echo "- Services migrated from $SERVICES_SRC_DIR to $TARGET_BASE_DIR/*/services/"
echo "- APIs migrated from $API_SRC_DIR to $TARGET_BASE_DIR/*/api/(public|internal)/"
echo "- Import statements updated to reflect new module paths"
echo ""
echo "Next steps:"
echo "1. Verify all files have been correctly moved"
echo "2. Run tests to ensure functionality remains intact"
echo "3. Update any remaining hardcoded paths in configuration files"
echo "4. Update documentation with new structure"
echo "5. Update CI/CD pipelines to reference new locations"
echo ""
echo "Note: This migration moved files but preserved functionality."
echo "Review and test thoroughly before deploying to production."