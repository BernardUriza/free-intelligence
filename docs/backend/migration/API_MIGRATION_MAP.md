# Backend API Migration Map (P0)

This document outlines the planned migration of API endpoints from `backend/api/` to the new modular structure.

## Current API Structure

### Public API (CORS-enabled)
Located in: `backend/api/public/`

Current modules and classification:
- `checkin.py` (Check-in domain) → `backend/src/fi_checkin/api/public/checkin.py`
- `tts.py` (TTS domain) → `backend/src/fi_tts/api/public/tts.py`
- `patients.py` (Patient Management domain) → `backend/src/fi_patient/api/public/patients.py`
- `providers.py` (Provider Management domain) → `backend/src/fi_provider/api/public/providers.py`
- `clinics.py` (Clinic Management domain) → `backend/src/fi_clinic/api/public/clinics.py`
- `user_clinic.py` (User-Clinic Relations) → `backend/src/fi_user/api/public/user_clinic.py`
- `payments.py` (Payment Processing) → `backend/src/fi_payment/api/public/payments.py`
- `notifications.py` (Notification Service) → `backend/src/fi_common/api/public/notifications.py`
- `policy.py` (Policy Management) → `backend/src/fi_policy/api/public/policy.py`
- `system_resources.py` (System Resources) → `backend/src/fi_system/api/public/system_resources.py`
- `audit.py` (Audit Logging) → `backend/src/fi_audit/api/public/audit.py`
- `catalog_admin.py` (Catalog Admin) → `backend/src/fi_model_catalog/api/public/catalog_admin.py`
- `llm_models_admin.py` (LLM Models Admin) → `backend/src/fi_llm/api/public/llm_models_admin.py`
- `personas_admin.py` (Personas Admin) → `backend/src/fi_llm/api/public/personas_admin.py`

#### Workflows Subdomain (Complex - contains multiple services)
Located in: `backend/api/public/workflows/`
- `assistant.py` (Assistant functionality) → `backend/src/fi_assistant/api/public/assistant.py`
- `assistant/` subdirectory (Assistant components) → `backend/src/fi_assistant/api/public/assistant/`
- `assistant_schemas.py` → `backend/src/fi_assistant/api/public/assistant_schemas.py`
- `assistant_history.py` → `backend/src/fi_assistant/api/public/assistant_history.py`
- `assistant_websocket.py` → `backend/src/fi_assistant/api/public/assistant_websocket.py`
- `aurity_personas.py` → `backend/src/fi_assistant/api/public/aurity_personas.py`
- `clinic_media.py` → `backend/src/fi_clinic/api/public/clinic_media.py`
- `documents.py` → `backend/src/fi_document/api/public/documents.py`
- `emotional_analysis.py` → `backend/src/fi_analysis/api/public/emotional_analysis.py`
- `evidence.py` → `backend/src/fi_evidence/api/public/evidence.py`
- `kpis.py` → `backend/src/fi_kpi/api/public/kpis.py`
- `longitudinal_memory.py` → `backend/src/fi_memory/api/public/longitudinal_memory.py`
- `orders.py` → `backend/src/fi_order/api/public/orders.py`
- `sessions.py` → `backend/src/fi_session/api/public/sessions.py`
- `sessions_list.py` → `backend/src/fi_session/api/public/sessions_list.py`
- `sessions_pkg/` → `backend/src/fi_session/api/public/sessions_pkg/`
- `soap.py` → `backend/src/fi_soap_generation/api/public/soap.py`
- `system.py` → `backend/src/fi_system/api/public/system.py`
- `timeline.py` → `backend/src/fi_timeline/api/public/timeline.py`
- `transcription.py` → `backend/src/fi_transcription/api/public/transcription.py`
- `tv_content_seeds.py` → `backend/src/fi_content/api/public/tv_content_seeds.py`
- `unified_timeline.py` → `backend/src/fi_timeline/api/public/unified_timeline.py`
- `waiting_room.py` → `backend/src/fi_workflow/api/public/waiting_room.py`
- `widget_configs.py` → `backend/src/fi_widget/api/public/widget_configs.py`
- `models/` → `backend/src/fi_common/api/public/models/` (shared models)
- `services/` → `backend/src/fi_workflow/api/public/services/` (workflow services)

#### System Subdomain
Located in: `backend/api/public/system/`
- `router.py` → `backend/src/fi_system/api/public/system/router.py`

### Internal API (Localhost-only in production)
Located in: `backend/api/internal/`

Current modules and classification:
- `/admin` (Admin functions) → `backend/src/fi_admin/api/internal/admin/`
- `/audit` (Audit functions) → `backend/src/fi_audit/api/internal/audit/`
- `/diarization` (Diarization functions) → `backend/src/fi_transcription/api/internal/diarization/`
- `/exports` (Export functions) → `backend/src/fi_common/api/internal/exports/`
- `/fi_coder` (Code generation functions) → `backend/src/fi_coder/api/internal/fi_coder/`
- `/kpis` (KPI functions) → `backend/src/fi_kpi/api/internal/kpis/`
- `/llm` (LLM functions) → `backend/src/fi_llm/api/internal/llm/`
- `/sessions` (Session functions) → `backend/src/fi_session/api/internal/sessions/`
- `/timeline` (Timeline functions) → `backend/src/fi_timeline/api/internal/timeline/`
- `/transcribe` (Transcription functions) → `backend/src/fi_transcription/api/internal/transcribe/`
- `/triage` (Triage functions) → `backend/src/fi_workflow/api/internal/triage/`

## Migration Classification Summary

### Public API Mappings:
- Patient Management → `fi_patient`
- Provider Management → `fi_provider`
- Clinic Management → `fi_clinic`
- LLM/Assistant → `fi_llm`/`fi_assistant`
- Transcription → `fi_transcription`
- SOAP Generation → `fi_soap_generation`
- Timeline → `fi_timeline`
- KPIs → `fi_kpi`
- Memory/Evidence → `fi_memory`/`fi_evidence`
- Check-in → `fi_checkin`
- Workflow → `fi_workflow`
- System → `fi_system`
- User Management → `fi_user`
- Payments → `fi_payment`
- Model Catalog → `fi_model_catalog`
- Session Management → `fi_session`
- TTS → `fi_tts`
- Content → `fi_content`
- Widget → `fi_widget`

### Internal API Mappings:
- Audit → `fi_audit`
- Diarization → `fi_transcription`
- Export → `fi_common`
- LLM → `fi_llm`
- Sessions → `fi_session`
- Timeline → `fi_timeline`
- Admin → `fi_admin`

## Migration Strategy

### Phase 1: Foundational APIs
1. Common API components
2. Authentication/Authorization endpoints
3. Shared models and utilities

### Phase 2: Core Service APIs
1. Patient, Provider, Clinic management
2. Session and Check-in flows
3. LLM and Assistant services

### Phase 3: Domain-specific APIs
1. Transcription, SOAP, Timeline
2. Analysis and Evidence systems
3. TTS and Workflow handling

### Phase 4: Administrative APIs
1. Internal monitoring and diagnostics
2. Model catalog and KPI endpoints
3. Export and administrative functions

Each phase should maintain backward compatibility until final cutover.