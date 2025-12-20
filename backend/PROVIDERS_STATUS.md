# backend/providers/ - Estado Actual

## ❌ NO ELIMINAR (Tiene dependencias activas)

### Archivos en providers/ (7 total)
```
backend/providers/
├── __init__.py
├── adapters.py      # Redux adapters
├── diarization.py   # Diarization providers
├── llm.py          # LLM multi-provider abstraction
├── models.py       # Consultation models
├── retry.py        # Circuit breaker & retry logic
└── stt.py          # Speech-to-text providers
```

### Imports Activos (~20 ubicaciones)

**App Core (3):**
- backend/app/gateways/aurity.py (2 imports)
- backend/cli/fi_test.py (1 import)

**Workers (3):**
- backend/workers/tasks/transcription_worker.py
- backend/workers/tasks/emotion_worker.py
- backend/workers/tasks/diarization_worker.py

**Schemas (1):**
- backend/schemas/fi_event_store.py

**Tests (12+):**
- backend/tests/test_ollama_retry.py (8 imports)
- backend/tests/integration/test_concurrent_h5_writes.py
- backend/tests/test_presets.py
- (más tests...)

**New Packages (3):**
- backend/src/fi_llm/api/internal/llm/chat.py
- backend/src/fi_llm/api/internal/llm/structured.py
- backend/src/fi_llm/api/public/personas_admin.py

**Debug (1):**
- backend/debug/debug_provider.py

### ¿Por qué existe providers/?

**Propósito:** Capa de abstracción para proveedores externos
- LLM providers (Claude, Ollama, OpenAI)
- STT providers (Deepgram, Whisper)
- Diarization providers (Azure, custom)

**Diferencia con services/:**
- `services/` = Lógica de negocio (ELIMINADO ✅)
- `providers/` = Adapters para APIs externas (ACTIVO ⚠️)

### ¿Debería migrarse?

**Opción A: Migrar a fi_common/providers/** (Recomendado)
```
backend/src/fi_common/
├── providers/
│   ├── llm.py
│   ├── stt.py
│   └── diarization.py
```
- Providers son infraestructura compartida
- fi_common es el lugar correcto

**Opción B: Distribuir por dominio**
```
backend/src/fi_llm/providers/llm.py
backend/src/fi_transcription/providers/stt.py
backend/src/fi_session/providers/diarization.py
```
- Más modular
- Puede causar dependencias circulares

**Opción C: Dejar como está**
- Providers son cross-cutting concerns
- No necesariamente parte de un dominio específico
- Puede vivir en backend/providers/

### Recomendación

**NO migrar ahora** - Providers son una capa de infraestructura estable que:
1. No es parte de la lógica de negocio
2. Es compartida entre múltiples dominios
3. Tiene muchas dependencias activas
4. Puede causar breaking changes innecesarios

Si se migra, hacerlo en **P2** después de:
1. Completar P1 (eliminar backend/api/)
2. Validar que toda la arquitectura fi_* funciona
3. Decidir estrategia (fi_common vs distribuido)

### Estado Actual

- ✅ backend/services/ ELIMINADO
- ⏸️ backend/api/ (P1 en progreso)
- ✅ backend/providers/ PERMANECE (no es parte de P0/P1)

---
**Fecha:** 2025-12-19
**Estado:** ACTIVO - NO ELIMINAR
**Imports activos:** ~20
**Plan:** Dejar en backend/providers/ (cross-cutting concern)
