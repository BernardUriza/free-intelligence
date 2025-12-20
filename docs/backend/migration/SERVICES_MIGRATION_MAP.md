# Backend Services Migration Map (P0)

This document outlines the planned migration of services from `backend/services/` to the new modular structure `backend/src/fi_DOMAIN/services/`.

## Current Services Classification

Based on analysis of the backend/services/ directory, services have been classified by domain/functionality:

### Authentication & Management Domain
- `auth0_management.py` → `backend/src/fi_auth/services/auth0_management.py`
- `gatekeeper.py` → `backend/src/fi_auth/services/gatekeeper.py`

### Storage & Corpus Domain
- `corpus_service.py` → `backend/src/fi_storage/services/corpus_service.py`
- `checkpoint/adapters/hdf5_repository.py` → `backend/src/fi_storage/services/adapters/hdf5_repository.py`
- `checkpoint/ports/audio_repository.py` → `backend/src/fi_storage/services/ports/audio_repository.py`
- `checkpoint/adapters/ffmpeg_concatenator.py` → `backend/src/fi_storage/services/adapters/ffmpeg_concatenator.py`
- `checkpoint/ports/audio_concatenator.py` → `backend/src/fi_storage/services/ports/audio_concatenator.py`
- `trace_store.py` → `backend/src/fi_storage/services/trace_store.py`

### LLM & AI Domain
- `llm_model_service.py` → `backend/src/fi_llm/services/llm_model_service.py`
- `llm/conversation_memory.py` → `backend/src/fi_llm/services/conversation_memory.py`
- `llm/persona/config.py` → `backend/src/fi_llm/services/persona/config.py`
- `llm/persona/constants.py` → `backend/src/fi_llm/services/persona/constants.py`
- `llm/persona/exceptions.py` → `backend/src/fi_llm/services/persona/exceptions.py`
- `llm/persona/manager.py` → `backend/src/fi_llm/services/persona/manager.py`
- `llm/persona/prompt_builder.py` → `backend/src/fi_llm/services/persona/prompt_builder.py`
- `llm/persona/router.py` → `backend/src/fi_llm/services/persona/router.py`
- `llm/persona/schemas.py` → `backend/src/fi_llm/services/persona/schemas.py`
- `llm/persona_manager.py` → `backend/src/fi_llm/services/persona_manager.py`

### Model Catalog Domain
- `model_catalog/catalog_service.py` → `backend/src/fi_model_catalog/services/catalog_service.py`
- `model_catalog/sources/base.py` → `backend/src/fi_model_catalog/services/sources/base.py`
- `model_catalog/sources/gpt4all_source.py` → `backend/src/fi_model_catalog/services/sources/gpt4all_source.py`
- `model_catalog/sources/huggingface_source.py` → `backend/src/fi_model_catalog/services/sources/huggingface_source.py`
- `model_catalog/sources/ollama_source.py` → `backend/src/fi_model_catalog/services/sources/ollama_source.py`

### Transcription Domain
- `transcription_service.py` → `backend/src/fi_transcription/services/transcription_service.py`
- `transcription/service.py` → `backend/src/fi_transcription/services/service.py`
- `transcription/validators.py` → `backend/src/fi_transcription/services/validators.py`
- `transcription/whisper.py` → `backend/src/fi_transcription/services/whisper.py`
- `deepgram_service.py` → `backend/src/fi_transcription/services/deepgram_service.py`

### SOAP Generation Domain
- `soap_generation/USAGE_EXAMPLES.py` → `backend/src/fi_soap_generation/services/USAGE_EXAMPLES.py`
- `soap_generation/completeness.py` → `backend/src/fi_soap_generation/services/completeness.py`
- `soap_generation/complexity_analyzer.py` → `backend/src/fi_soap_generation/services/complexity_analyzer.py`
- `soap_generation/decisional_middleware.py` → `backend/src/fi_soap_generation/services/decisional_middleware.py`
- `soap_generation/defaults.py` → `backend/src/fi_soap_generation/services/defaults.py`
- `soap_generation/llm_client.py` → `backend/src/fi_soap_generation/services/llm_client.py`
- `soap_generation/prompt_builder.py` → `backend/src/fi_soap_generation/services/prompt_builder.py`
- `soap_generation/reader.py` → `backend/src/fi_soap_generation/services/reader.py`
- `soap_generation/response_parser.py` → `backend/src/fi_soap_generation/services/response_parser.py`
- `soap_generation/soap_builder.py` → `backend/src/fi_soap_generation/services/soap_builder.py`
- `soap_generation/soap_generation_service.py` → `backend/src/fi_soap_generation/services/soap_generation_service.py`
- `soap_generation/soap_models.py` → `backend/src/fi_soap_generation/services/soap_models.py`
- `soap_generation/tests.py` → `backend/src/fi_soap_generation/services/tests.py`

### Timeline Domain
- `timeline/__init__.py` → `backend/src/fi_timeline/services/timeline/__init__.py`
- `timeline/api.py` → `backend/src/fi_timeline/services/timeline/api.py`
- `timeline/auto.py` → `backend/src/fi_timeline/services/timeline/auto.py`
- `timeline/demo.py` → `backend/src/fi_timeline/services/timeline/demo.py`

### Session Management Domain
- `session_service.py` → `backend/src/fi_session/services/session_service.py`

### TTS (Text-to-Speech) Domain
- `tts_openai.py` → `backend/src/fi_tts/services/tts_openai.py`
- `tts_openai_steerable.py` → `backend/src/fi_tts/services/tts_openai_steerable.py`
- `tts_service.py` → `backend/src/fi_tts/services/tts_service.py`
- `tts_unified.py` → `backend/src/fi_tts/services/tts_unified.py`

### Workflow Management Domain
- `workflow_router.py` → `backend/src/fi_workflow/services/workflow_router.py`
- `workflow_tracker.py` → `backend/src/fi_workflow/services/workflow_tracker.py`
- `triage_service.py` → `backend/src/fi_workflow/services/triage_service.py`

### Checkpoint Management Domain
- `checkpoint/usecases/checkpoint_use_case.py` → `backend/src/fi_checkpoint/services/usecases/checkpoint_use_case.py`

### Common/Utility Services
- `chat_chunk_handler.py` → `backend/src/fi_common/services/chat_chunk_handler.py`
- `chunk_handler.py` → `backend/src/fi_common/services/chunk_handler.py`
- `chunk_handler_factory.py` → `backend/src/fi_common/services/chunk_handler_factory.py`
- `medical_chunk_handler.py` → `backend/src/fi_common/services/medical_chunk_handler.py`
- `notifications.py` → `backend/src/fi_common/services/notifications.py`
- `export_service.py` → `backend/src/fi_common/services/export_service.py`
- `evidence_service.py` → `backend/src/fi_common/services/evidence_service.py`
- `checkin_conversation.py` → `backend/src/fi_checkin/services/checkin_conversation.py`
- `audit_service.py` → `backend/src/fi_audit/services/audit_service.py`
- `personas_metrics_service.py` → `backend/src/fi_kpi/services/personas_metrics_service.py`
- `kpis_aggregator.py` → `backend/src/fi_kpi/services/kpis_aggregator.py`
- `diagnostics_service.py` → `backend/src/fi_common/services/diagnostics_service.py`
- `system_health_service.py` → `backend/src/fi_system/services/system_health_service.py`

### Initialization
- `__init__.py` → `backend/src/fi_common/services/__init__.py` (or distributed as appropriate)

## Migration Dependencies

1. Core Infrastructure (fi_common, fi_storage, fi_auth)
2. Foundation Services (fi_model_catalog, fi_llm)
3. Domain Services (fi_transcription, fi_soap_generation, fi_timeline, fi_session, etc.)
4. Application Logic (fi_workflow, fi_checkin, fi_kpi)

## Migration Steps

1. Create new directory structure under `backend/src/fi_*/services/`
2. Move services with updates to imports and references
3. Update all cross-service dependencies
4. Verify functionality after each migration
5. Update tests and documentation