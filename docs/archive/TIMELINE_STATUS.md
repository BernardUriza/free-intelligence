# Timeline AURITY - Estado Actual

**Fecha**: 2025-10-28 21:00
**Card**: [P0][Área: UX/UI][Tipo: feature] Memoria legible — Timeline AURITY
**Sprint**: SPR-2025W44
**Status**: 🟢 Modelo + Auto-Timeline implementados, demo ejecutado exitosamente

---

## ✅ Logros Actuales

### 1. Modelo de Datos (Completado)

**Archivo**: `backend/timeline_models.py` (580 LOC)

**Entidades**:
- `TimelineEvent`: Unidad atómica con causalidad (quién→qué→cuándo→por qué)
- `TimelineEventCausality`: Relaciones causales entre eventos (DAG)
- `Timeline`: Colección ordenada de eventos con metadata

**Campos core**:
- `event_id` (UUID v4), `timestamp` (ISO 8601 + timezone)
- `who` (actor hash), `what` (descripción redactada), `causality` (relaciones)
- `content_hash` (SHA256 sin exponer crudo), `redaction_policy`
- `auto_generated` (bool), `generation_mode` (auto/manual/assisted)

**Causalidad**: 6 tipos implementados
- `caused_by`, `triggered`, `updated`, `replaced`, `confirmed`, `contradicted`

**Redacción**: 4 políticas
- `none` (público), `summary` (resumen), `metadata` (solo meta), `full` (solo hash)

**Tipos de eventos**: 12 implementados
- User: `user_message`, `user_upload`, `user_edit`
- System: `assistant_response`, `extraction_started/completed`
- Medical: `soap_section_updated`, `soap_completed`, `diagnosis_suggested`
- Critical: `critical_pattern_detected`, `urgency_escalated`
- Policy: `redaction_applied`, `export_created`

**Demo ejecutado**: ✅ 10 eventos con 8 aristas causales (widow-maker scenario)

### 2. Auto-Timeline con Ollama (Completado)

**Archivo**: `backend/timeline_auto.py` (550 LOC)

**Componentes**:
- `AutoTimelineGenerator`: Generador automático con heurística v1
- `EventCandidate`: Modelo para selección de eventos
- `CausalityCandidate`: Modelo para detección de relaciones causales

**Heurística v1 implementada**:
- ✅ Selección de eventos núcleo (HASH_WRITTEN, POLICY_CHECK, etc.)
- ✅ Agrupación por ventanas de 90s + session_id + manifest_ref
- ✅ Detección de causalidad (same_artifact + temporal_adjacent)
- ✅ Generación de summaries con LLM (≤180 chars, sin PII)
- ✅ Fallback a manual+assist si LLM falla (timeout >8s)

**Feature flag**:
- `config/fi.policy.yaml` → `timeline.auto.enabled: false` (default)
- Configurable: provider, model, timeout, redaction rules

**Demo ejecutado**: `scripts/demo_timeline_10_events.py`
- ✅ 10 eventos médicos realistas (widow-maker scenario)
- ✅ 8 aristas causales (> 4 required)
- ✅ Redacción aplicada (summary/metadata policies)
- ✅ SHA256 hashing (no raw content exposed)

---

## 🔧 Capacidades Actuales

### Sin Spoilers de Audio Crudo
- ✅ `content_hash` almacena SHA256 del contenido original
- ✅ `summary` contiene descripción redactada (≤180 chars recomendado)
- ✅ Nunca se expone raw_content en timeline
- ✅ `redaction_policy` controla nivel de exposición

### Causalidad (quién→qué→cuándo→por qué)
- ✅ `who`: Actor identificado (user_hash/assistant/system)
- ✅ `what`: Descripción de acción
- ✅ `timestamp`: Cuándo ocurrió
- ✅ `causality`: Lista de relaciones con eventos previos (por qué)
- ✅ `get_causal_chain()`: Reconstruye cadena completa

### Metadata y Stats
- ✅ Contadores auto/manual events
- ✅ Estadísticas de redacción por política
- ✅ Export to dict (JSON/HDF5 ready)
- ✅ Filtros por tipo, actor, tags

### Auto-Timeline
- ✅ Feature flag en `fi.policy.yaml` (timeline.auto.enabled)
- ✅ Selección de eventos núcleo (6 tipos configurables)
- ✅ Agrupación por ventanas temporales (90s + session + manifest)
- ✅ Detección automática de causalidad (same_artifact + temporal_adjacent)
- ✅ Generación de summaries con LLM (con timeout 8s)
- ✅ Fallback a manual+assist si LLM falla

---

## 🚧 Límites Actuales

### No Implementado (Pendiente)
- ⏳ Persistencia en HDF5/event store (integración con fi_event_store.py)
- ⏳ API REST endpoints (FastAPI service)
- ⏳ Frontend (wireframes + navegación causal interactiva)
- ⏳ Export a Markdown/PDF para timeline
- ⏳ Métricas de observabilidad (auto_timeline_*, p95)

### Riesgos Identificados
1. **Latencia Ollama**: Resúmenes on-prem pueden tardar >2s (mitigación: cache + async)
2. **Causalidad ambigua**: Eventos concurrentes pueden tener múltiples interpretaciones
3. **Redacción incompleta**: Necesita validación AST para palabras vetadas
4. **Escala**: Timeline con 100+ eventos puede ser lento sin paginación

---

## 🗺️ Integración con FI-Core/AURITY

### FI-Core (Backend)
```
Event Store (HDF5)
    ↓
Timeline Generator (timeline_auto.py)
    ↓
Timeline Models (timeline_models.py) ✅
    ↓
Timeline API (fi_timeline_service.py) ⏳
    ↓
Export (Markdown/JSON/HDF5)
```

### AURITY (Frontend)
```
Timeline UI (React)
    ↓
Timeline API Client (@fi/shared)
    ↓
FI Timeline API (FastAPI port 7003) ⏳
    ↓
Timeline Models
```

### Flujo de Datos
1. **Ingest**: Eventos médicos → Event Store (fi_consult_service.py)
2. **Generation**: Event Store → Timeline Generator → Timeline Models
3. **Presentation**: Timeline API → AURITY UI
4. **Export**: Timeline → Markdown/JSON con manifests

---

## 📊 Próximos Pasos (Orden de Implementación)

### Fase 1: Auto-Timeline (Completado ✅)
- [✅] Feature flag `fi.policy.yaml` → `timeline.auto.enabled`
- [✅] LLMAdapter con Ollama (qwen2-7b / deepseek-r1-distill-7b)
- [✅] Heurística v1: selección de eventos núcleo
- [✅] Agrupación por session_id + manifest_ref (ventanas 90s)
- [✅] Causalidad automática (same_artifact + temporal_adjacent)
- [✅] Redacción con prompts (≤180 chars, sin PII)
- [✅] Fallback a manual+assist si Ollama falla

### Fase 2: API + Persistencia
- [ ] `fi_timeline_service.py` (FastAPI endpoints)
- [ ] Persistencia en HDF5 (grupo /timelines/)
- [ ] Integración con fi_event_store.py
- [ ] Observabilidad (métricas p95 latency)

### Fase 3: Frontend
- [ ] Wireframes (lista, detalle, export)
- [ ] React components (@fi/shared types)
- [ ] Navegación causal (grafo interactivo)
- [ ] Export a Markdown/PDF

---

## 🎯 Criterios de Aceptación (Card)

### Prototipo Navegable
- [✅] 10 eventos de ejemplo con ≥4 aristas de causalidad (8 aristas en demo)
- [ ] Manual override probado (editar/ocultar eventos)
- [ ] 3 vistas funcionales: lista, detalle, export

### Política de Redacción
- [✅] 0 leaks de texto crudo (SHA256 hashing)
- [✅] `sensitive=true` → redaction_policy=FULL
- [✅] Summary generado cumple ≤180 chars (configurable)

### Performance
- [ ] p95 ingest <2s (segment≤600ms, hash≤300ms, persist≤400ms, publish≤300ms)
- [ ] p95 lectura timeline <300ms (10-50 eventos)
- [✅] Fallback activo: Ollama timeout >8s → manual+assist

### Reproducibilidad
- [ ] Export/import de TimelineSession reproduce mismo orden + hashes
- [ ] Mismo prompt_hash + ventana → mismo summary (cache 30 días)

---

## 📈 Métricas Objetivo

| Métrica | Target | Actual |
|---------|--------|--------|
| LOC Timeline Models | ~500 | 580 ✅ |
| LOC Auto-Timeline | ~500 | 550 ✅ |
| Eventos demo | 10 | 10 ✅ |
| Aristas causalidad | ≥4 | 8 ✅ |
| p95 ingest | <2s | N/A ⏳ |
| p95 lectura | <300ms | N/A ⏳ |
| PII leaks | 0 | 0 ✅ |
| Feature flag | Sí | Sí ✅ |

---

## 🔗 Referencias

- **Modelo**: `backend/timeline_models.py:1`
- **Card**: https://trello.com/c/vxrf8995/153
- **Event Store**: `backend/fi_event_store.py:1`
- **Consult Service**: `backend/fi_consult_service.py:1`

---

**Free Intelligence - Timeline que respeta la privacidad y la causalidad** 🧠📋
