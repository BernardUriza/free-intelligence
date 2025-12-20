#!/bin/bash

# Script to update import statements in backend/src/fi_*/ directories
# Based on SERVICES_MIGRATION_MAP.md and API_MIGRATION_MAP.md
# This script updates 'from backend.services.X' to 'from backend.src.fi_DOMAIN.services.X'
# and 'from backend.api.X' to 'from backend.src.fi_DOMAIN.api.X'

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting import statements update...${NC}"

# Define backup extension
BACKUP_EXT=".bak"

# Find all Python files in backend/src/fi_* directories
PYTHON_FILES=$(find backend/src/fi_* -name "*.py" -type f 2>/dev/null || true)

if [ -z "$PYTHON_FILES" ]; then
    echo -e "${YELLOW}No Python files found in backend/src/fi_* directories${NC}"
    exit 0
fi

# Count total files to process
TOTAL_FILES=$(echo "$PYTHON_FILES" | wc -l)
CURRENT_FILE_NUM=0

echo -e "${GREEN}Found $TOTAL_FILES files to process${NC}"

# Process each file
for file in $PYTHON_FILES; do
    ((CURRENT_FILE_NUM++))
    echo -ne "${YELLOW}Processing ($CURRENT_FILE_NUM/$TOTAL_FILES): $file ...${NC}\r"
    
    # Create a backup of the file
    cp "$file" "$file$BACKUP_EXT"
    
    # Update services imports
    # Using BSD sed syntax for macOS compatibility
    
    # Authentication & Management Domain
    sed -i '' 's/from backend\.services\.auth0_management/from backend.src.fi_auth.services.auth0_management/g' "$file"
    sed -i '' 's/from backend\.services\.gatekeeper/from backend.src.fi_auth.services.gatekeeper/g' "$file"
    
    # Storage & Corpus Domain
    sed -i '' 's/from backend\.services\.corpus_service/from backend.src.fi_storage.services.corpus_service/g' "$file"
    sed -i '' 's/from backend\.services\.checkpoint\.adapters\.hdf5_repository/from backend.src.fi_storage.services.adapters.hdf5_repository/g' "$file"
    sed -i '' 's/from backend\.services\.checkpoint\.ports\.audio_repository/from backend.src.fi_storage.services.ports.audio_repository/g' "$file"
    sed -i '' 's/from backend\.services\.checkpoint\.adapters\.ffmpeg_concatenator/from backend.src.fi_storage.services.adapters.ffmpeg_concatenator/g' "$file"
    sed -i '' 's/from backend\.services\.checkpoint\.ports\.audio_concatenator/from backend.src.fi_storage.services.ports.audio_concatenator/g' "$file"
    sed -i '' 's/from backend\.services\.trace_store/from backend.src.fi_storage.services.trace_store/g' "$file"
    
    # LLM & AI Domain
    sed -i '' 's/from backend\.services\.llm_model_service/from backend.src.fi_llm.services.llm_model_service/g' "$file"
    sed -i '' 's/from backend\.services\.llm\.conversation_memory/from backend.src.fi_llm.services.conversation_memory/g' "$file"
    sed -i '' 's/from backend\.services\.llm\.persona\.config/from backend.src.fi_llm.services.persona.config/g' "$file"
    sed -i '' 's/from backend\.services\.llm\.persona\.constants/from backend.src.fi_llm.services.persona.constants/g' "$file"
    sed -i '' 's/from backend\.services\.llm\.persona\.exceptions/from backend.src.fi_llm.services.persona.exceptions/g' "$file"
    sed -i '' 's/from backend\.services\.llm\.persona\.manager/from backend.src.fi_llm.services.persona.manager/g' "$file"
    sed -i '' 's/from backend\.services\.llm\.persona\.prompt_builder/from backend.src.fi_llm.services.persona.prompt_builder/g' "$file"
    sed -i '' 's/from backend\.services\.llm\.persona\.router/from backend.src.fi_llm.services.persona.router/g' "$file"
    sed -i '' 's/from backend\.services\.llm\.persona\.schemas/from backend.src.fi_llm.services.persona.schemas/g' "$file"
    sed -i '' 's/from backend\.services\.llm\.persona_manager/from backend.src.fi_llm.services.persona_manager/g' "$file"
    
    # Model Catalog Domain
    sed -i '' 's/from backend\.services\.model_catalog\.catalog_service/from backend.src.fi_model_catalog.services.catalog_service/g' "$file"
    sed -i '' 's/from backend\.services\.model_catalog\.sources\.base/from backend.src.fi_model_catalog.services.sources.base/g' "$file"
    sed -i '' 's/from backend\.services\.model_catalog\.sources\.gpt4all_source/from backend.src.fi_model_catalog.services.sources.gpt4all_source/g' "$file"
    sed -i '' 's/from backend\.services\.model_catalog\.sources\.huggingface_source/from backend.src.fi_model_catalog.services.sources.huggingface_source/g' "$file"
    sed -i '' 's/from backend\.services\.model_catalog\.sources\.ollama_source/from backend.src.fi_model_catalog.services.sources.ollama_source/g' "$file"
    
    # Transcription Domain
    sed -i '' 's/from backend\.services\.transcription_service/from backend.src.fi_transcription.services.transcription_service/g' "$file"
    sed -i '' 's/from backend\.services\.transcription\.service/from backend.src.fi_transcription.services.service/g' "$file"
    sed -i '' 's/from backend\.services\.transcription\.validators/from backend.src.fi_transcription.services.validators/g' "$file"
    sed -i '' 's/from backend\.services\.transcription\.whisper/from backend.src.fi_transcription.services.whisper/g' "$file"
    sed -i '' 's/from backend\.services\.deepgram_service/from backend.src.fi_transcription.services.deepgram_service/g' "$file"
    
    # SOAP Generation Domain
    sed -i '' 's/from backend\.services\.soap_generation\.USAGE_EXAMPLES/from backend.src.fi_soap_generation.services.USAGE_EXAMPLES/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.completeness/from backend.src.fi_soap_generation.services.completeness/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.complexity_analyzer/from backend.src.fi_soap_generation.services.complexity_analyzer/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.decisional_middleware/from backend.src.fi_soap_generation.services.decisional_middleware/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.defaults/from backend.src.fi_soap_generation.services.defaults/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.llm_client/from backend.src.fi_soap_generation.services.llm_client/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.prompt_builder/from backend.src.fi_soap_generation.services.prompt_builder/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.reader/from backend.src.fi_soap_generation.services.reader/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.response_parser/from backend.src.fi_soap_generation.services.response_parser/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.soap_builder/from backend.src.fi_soap_generation.services.soap_builder/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.soap_generation_service/from backend.src.fi_soap_generation.services.soap_generation_service/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.soap_models/from backend.src.fi_soap_generation.services.soap_models/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation\.tests/from backend.src.fi_soap_generation.services.tests/g' "$file"
    
    # Timeline Domain
    sed -i '' 's/from backend\.services\.timeline\.\_\_init\_\_/from backend.src.fi_timeline.services.timeline.__init__/g' "$file"
    sed -i '' 's/from backend\.services\.timeline\.api/from backend.src.fi_timeline.services.timeline.api/g' "$file"
    sed -i '' 's/from backend\.services\.timeline\.auto/from backend.src.fi_timeline.services.timeline.auto/g' "$file"
    sed -i '' 's/from backend\.services\.timeline\.demo/from backend.src.fi_timeline.services.timeline.demo/g' "$file"
    
    # Session Management Domain
    sed -i '' 's/from backend\.services\.session_service/from backend.src.fi_session.services.session_service/g' "$file"
    
    # TTS (Text-to-Speech) Domain
    sed -i '' 's/from backend\.services\.tts_openai/from backend.src.fi_tts.services.tts_openai/g' "$file"
    sed -i '' 's/from backend\.services\.tts_openai_steerable/from backend.src.fi_tts.services.tts_openai_steerable/g' "$file"
    sed -i '' 's/from backend\.services\.tts_service/from backend.src.fi_tts.services.tts_service/g' "$file"
    sed -i '' 's/from backend\.services\.tts_unified/from backend.src.fi_tts.services.tts_unified/g' "$file"
    
    # Workflow Management Domain
    sed -i '' 's/from backend\.services\.workflow_router/from backend.src.fi_workflow.services.workflow_router/g' "$file"
    sed -i '' 's/from backend\.services\.workflow_tracker/from backend.src.fi_workflow.services.workflow_tracker/g' "$file"
    sed -i '' 's/from backend\.services\.triage_service/from backend.src.fi_workflow.services.triage_service/g' "$file"
    
    # Checkpoint Management Domain
    sed -i '' 's/from backend\.services\.checkpoint\.usecases\.checkpoint_use_case/from backend.src.fi_checkpoint.services.usecases.checkpoint_use_case/g' "$file"
    
    # Common/Utility Services
    sed -i '' 's/from backend\.services\.chat_chunk_handler/from backend.src.fi_common.services.chat_chunk_handler/g' "$file"
    sed -i '' 's/from backend\.services\.chunk_handler/from backend.src.fi_common.services.chunk_handler/g' "$file"
    sed -i '' 's/from backend\.services\.chunk_handler_factory/from backend.src.fi_common.services.chunk_handler_factory/g' "$file"
    sed -i '' 's/from backend\.services\.medical_chunk_handler/from backend.src.fi_common.services.medical_chunk_handler/g' "$file"
    sed -i '' 's/from backend\.services\.notifications/from backend.src.fi_common.services.notifications/g' "$file"
    sed -i '' 's/from backend\.services\.export_service/from backend.src.fi_common.services.export_service/g' "$file"
    sed -i '' 's/from backend\.services\.evidence_service/from backend.src.fi_common.services.evidence_service/g' "$file"
    sed -i '' 's/from backend\.services\.checkin_conversation/from backend.src.fi_checkin.services.checkin_conversation/g' "$file"
    sed -i '' 's/from backend\.services\.audit_service/from backend.src.fi_audit.services.audit_service/g' "$file"
    sed -i '' 's/from backend\.services\.personas_metrics_service/from backend.src.fi_kpi.services.personas_metrics_service/g' "$file"
    sed -i '' 's/from backend\.services\.kpis_aggregator/from backend.src.fi_kpi.services.kpis_aggregator/g' "$file"
    sed -i '' 's/from backend\.services\.diagnostics_service/from backend.src.fi_common.services.diagnostics_service/g' "$file"
    sed -i '' 's/from backend\.services\.system_health_service/from backend.src.fi_system.services.system_health_service/g' "$file"
    
    # Update API imports
    # Public API mappings
    
    # Check-in domain
    sed -i '' 's/from backend\.api\.public\.checkin/from backend.src.fi_checkin.api.public.checkin/g' "$file"
    
    # TTS domain
    sed -i '' 's/from backend\.api\.public\.tts/from backend.src.fi_tts.api.public.tts/g' "$file"
    
    # Patient Management domain
    sed -i '' 's/from backend\.api\.public\.patients/from backend.src.fi_patient.api.public.patients/g' "$file"
    
    # Provider Management domain
    sed -i '' 's/from backend\.api\.public\.providers/from backend.src.fi_provider.api.public.providers/g' "$file"
    
    # Clinic Management domain
    sed -i '' 's/from backend\.api\.public\.clinics/from backend.src.fi_clinic.api.public.clinics/g' "$file"
    
    # User-Clinic Relations
    sed -i '' 's/from backend\.api\.public\.user_clinic/from backend.src.fi_user.api.public.user_clinic/g' "$file"
    
    # Payment Processing
    sed -i '' 's/from backend\.api\.public\.payments/from backend.src.fi_payment.api.public.payments/g' "$file"
    
    # Notification Service
    sed -i '' 's/from backend\.api\.public\.notifications/from backend.src.fi_common.api.public.notifications/g' "$file"
    
    # Policy Management
    sed -i '' 's/from backend\.api\.public\.policy/from backend.src.fi_policy.api.public.policy/g' "$file"
    
    # System Resources
    sed -i '' 's/from backend\.api\.public\.system_resources/from backend.src.fi_system.api.public.system_resources/g' "$file"
    
    # Audit Logging
    sed -i '' 's/from backend\.api\.public\.audit/from backend.src.fi_audit.api.public.audit/g' "$file"
    
    # Model Catalog Admin
    sed -i '' 's/from backend\.api\.public\.catalog_admin/from backend.src.fi_model_catalog.api.public.catalog_admin/g' "$file"
    
    # LLM Models Admin
    sed -i '' 's/from backend\.api\.public\.llm_models_admin/from backend.src.fi_llm.api.public.llm_models_admin/g' "$file"
    
    # Personas Admin
    sed -i '' 's/from backend\.api\.public\.personas_admin/from backend.src.fi_llm.api.public.personas_admin/g' "$file"
    
    # Workflows Subdomain
    sed -i '' 's/from backend\.api\.public\.workflows\.assistant/from backend.src.fi_assistant.api.public.assistant/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.assistant_schemas/from backend.src.fi_assistant.api.public.assistant_schemas/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.assistant_history/from backend.src.fi_assistant.api.public.assistant_history/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.assistant_websocket/from backend.src.fi_assistant.api.public.assistant_websocket/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.aurity_personas/from backend.src.fi_assistant.api.public.aurity_personas/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.clinic_media/from backend.src.fi_clinic.api.public.clinic_media/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.documents/from backend.src.fi_document.api.public.documents/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.emotional_analysis/from backend.src.fi_analysis.api.public.emotional_analysis/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.evidence/from backend.src.fi_evidence.api.public.evidence/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.kpis/from backend.src.fi_kpi.api.public.kpis/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.longitudinal_memory/from backend.src.fi_memory.api.public.longitudinal_memory/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.orders/from backend.src.fi_order.api.public.orders/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.sessions/from backend.src.fi_session.api.public.sessions/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.sessions_list/from backend.src.fi_session.api.public.sessions_list/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.soap/from backend.src.fi_soap_generation.api.public.soap/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.system/from backend.src.fi_system.api.public.system/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.timeline/from backend.src.fi_timeline.api.public.timeline/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.transcription/from backend.src.fi_transcription.api.public.transcription/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.tv_content_seeds/from backend.src.fi_content.api.public.tv_content_seeds/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.unified_timeline/from backend.src.fi_timeline.api.public.unified_timeline/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.waiting_room/from backend.src.fi_workflow.api.public.waiting_room/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.widget_configs/from backend.src.fi_widget.api.public.widget_configs/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.models/from backend.src.fi_common.api.public.models/g' "$file"
    sed -i '' 's/from backend\.api\.public\.workflows\.services/from backend.src.fi_workflow.api.public.services/g' "$file"
    
    # System Subdomain
    sed -i '' 's/from backend\.api\.public\.system\.router/from backend.src.fi_system.api.public.system.router/g' "$file"
    
    # Internal API mappings
    
    # Admin functions
    sed -i '' 's/from backend\.api\.internal\.admin/from backend.src.fi_admin.api.internal.admin/g' "$file"
    
    # Audit functions
    sed -i '' 's/from backend\.api\.internal\.audit/from backend.src.fi_audit.api.internal.audit/g' "$file"
    
    # Diarization functions
    sed -i '' 's/from backend\.api\.internal\.diarization/from backend.src.fi_transcription.api.internal.diarization/g' "$file"
    
    # Export functions
    sed -i '' 's/from backend\.api\.internal\.exports/from backend.src.fi_common.api.internal.exports/g' "$file"
    
    # Code generation functions
    sed -i '' 's/from backend\.api\.internal\.fi_coder/from backend.src.fi_coder.api.internal.fi_coder/g' "$file"
    
    # KPI functions
    sed -i '' 's/from backend\.api\.internal\.kpis/from backend.src.fi_kpi.api.internal.kpis/g' "$file"
    
    # LLM functions
    sed -i '' 's/from backend\.api\.internal\.llm/from backend.src.fi_llm.api.internal.llm/g' "$file"
    
    # Sessions functions
    sed -i '' 's/from backend\.api\.internal\.sessions/from backend.src.fi_session.api.internal.sessions/g' "$file"
    
    # Timeline functions
    sed -i '' 's/from backend\.api\.internal\.timeline/from backend.src.fi_timeline.api.internal.timeline/g' "$file"
    
    # Transcription functions
    sed -i '' 's/from backend\.api\.internal\.transcribe/from backend.src.fi_transcription.api.internal.transcribe/g' "$file"
    
    # Triage functions
    sed -i '' 's/from backend\.api\.internal\.triage/from backend.src.fi_workflow.api.internal.triage/g' "$file"
    
    # Additional specific service mappings that may have been missed
    # Common services
    sed -i '' 's/from backend\.services\./from backend.src.fi_common.services./g' "$file"

    # Handle generic backend.services.* to backend.src.fi_* imports
    # More specific patterns for remaining services
    sed -i '' 's/from backend\.services\.audio_processing/from backend.src.fi_transcription.services.audio_processing/g' "$file"
    sed -i '' 's/from backend\.services\.audio_utils/from backend.src.fi_transcription.services.audio_utils/g' "$file"
    sed -i '' 's/from backend\.services\.soap_generation/from backend.src.fi_soap_generation.services.soap_generation/g' "$file"
    sed -i '' 's/from backend\.services\.llm_client/from backend.src.fi_llm.services.llm_client/g' "$file"
    sed -i '' 's/from backend\.services\.model_manager/from backend.src.fi_model_catalog.services.model_manager/g' "$file"
    sed -i '' 's/from backend\.services\.cache_service/from backend.src.fi_common.services.cache_service/g' "$file"
    sed -i '' 's/from backend\.services\.logging_service/from backend.src.fi_common.services.logging_service/g' "$file"
    sed -i '' 's/from backend\.services\.error_handler/from backend.src.fi_common.services.error_handler/g' "$file"
    sed -i '' 's/from backend\.services\.validator/from backend.src.fi_common.services.validator/g' "$file"

    # Handle remaining backend.api.* imports with more specific patterns
    # More public API mappings that might have been missed
    sed -i '' 's/from backend\.api\.public\.auth/from backend.src.fi_auth.api.public.auth/g' "$file"
    sed -i '' 's/from backend\.api\.public\.health/from backend.src.fi_system.api.public.health/g' "$file"
    sed -i '' 's/from backend\.api\.public\.metrics/from backend.src.fi_kpi.api.public.metrics/g' "$file"
    sed -i '' 's/from backend\.api\.public\.media/from backend.src.fi_common.api.public.media/g' "$file"
    sed -i '' 's/from backend\.api\.public\.utils/from backend.src.fi_common.api.public.utils/g' "$file"
    sed -i '' 's/from backend\.api\.public\.debug/from backend.src.fi_devtools.api.public.debug/g' "$file"

    # More internal API mappings
    sed -i '' 's/from backend\.api\.internal\.storage/from backend.src.fi_storage.api.internal.storage/g' "$file"
    sed -i '' 's/from backend\.api\.internal\.auth/from backend.src.fi_auth.api.internal.auth/g' "$file"
    sed -i '' 's/from backend\.api\.internal\.cache/from backend.src.fi_common.api.internal.cache/g' "$file"
    sed -i '' 's/from backend\.api\.internal\.debug/from backend.src.fi_devtools.api.internal.debug/g' "$file"
    
    # After updating the file, remove the backup if no differences
    if cmp -s "$file" "$file$BACKUP_EXT"; then
        rm "$file$BACKUP_EXT"
    else
        echo -e "\n${GREEN}Updated:$file${NC}" 
    fi
done

echo -e "\n${GREEN}Import statements update completed!${NC}"

# Check for any remaining backend.services or backend.api references that weren't caught
echo -e "\n${YELLOW}Checking for remaining references:${NC}"
COUNT_SERVICES=$(grep -r "from backend\.services\." backend/src/fi_*/*.py 2>/dev/null | wc -l)
COUNT_API=$(grep -r "from backend\.api\." backend/src/fi_*/*.py 2>/dev/null | wc -l)

if [ "$COUNT_SERVICES" -gt 0 ]; then
    echo -e "${RED}$COUNT_SERVICES remaining backend.services references found${NC}"
    grep -r "from backend\.services\." backend/src/fi_*/*.py 2>/dev/null
else
    echo -e "${GREEN}No remaining backend.services references found${NC}"
fi

if [ "$COUNT_API" -gt 0 ]; then
    echo -e "${RED}$COUNT_API remaining backend.api references found${NC}"
    grep -r "from backend\.api\." backend/src/fi_*/*.py 2>/dev/null
else
    echo -e "${GREEN}No remaining backend.api references found${NC}"
fi

echo -e "\n${GREEN}Script completed.${NC}"