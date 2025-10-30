# Backend Gap Analysis - Timeline UI Support
**Fecha**: 2025-10-29
**Context**: Análisis de APIs backend necesarias para soportar Timeline UI (FI-UI-FEAT-100 a 119)

---

## 📊 Estado Actual del Backend

### APIs Existentes ✅

1. **fi_corpus_api.py** (Puerto 9001)
   - `GET /api/corpus/stats` - Estadísticas del corpus
   - `GET /api/sessions/summary` - Resumen de sesiones con previews
   - `GET /api/sessions/{id}` - Detalles de sesión individual
   - `GET /health` - Health check

2. **aurity_gateway.py** (Puerto TBD)
   - `POST /aurity/redux-action` - Recibe Redux actions de AURITY
   - `GET /aurity/consultation/{id}` - Reconstruye estado desde eventos
   - `WebSocket /aurity/consultation/{id}/stream` - Stream eventos real-time

3. **Backend Modules**
   - `timeline_models.py` ✅ - Modelos de datos (Timeline, TimelineEvent, Causality)
   - `timeline_auto.py` ✅ - Generador automático de timeline con Ollama
   - `corpus_ops.py` ✅ - Operaciones HDF5 (append, read)
   - `audit_logs.py` ✅ - Audit trail append-only
   - `export_policy.py` ✅ - Export con manifests SHA256

---

## 🚨 GAPS CRÍTICOS IDENTIFICADOS

### GAP 1: API Timeline Principal ❌ CRÍTICO
**Necesidad**: Timeline UI (FI-UI-FEAT-100+) requiere API REST para:
- Listar sesiones con metadata completa (Hash/Policy/Redaction badges)
- Obtener timeline de eventos por sesión
- Filtrado y búsqueda de eventos
- Verificación de integridad (hash matching)

**Actual**: `fi_corpus_api.py` tiene `/api/sessions/{id}` pero **NO incluye**:
- ❌ Timeline events (solo raw interactions)
- ❌ Policy badges (hash_verified, policy_compliant, redaction_applied, audit_logged)
- ❌ Causality chains
- ❌ Redaction metadata
- ❌ Auto-timeline generation status

**Impacto**: **BLOCKER** para FI-UI-FEAT-100 (Encabezado Contextual), 104 (Panel Metadatos), 113 (Badges Integridad)

---

### GAP 2: API Verify Hash ❌ CRÍTICO
**Necesidad**: FI-UI-FEAT-113 (Badges Integridad) requiere endpoint para:
- Verificar SHA256 hash de sesión/interacción
- Validar manifest export
- Verificar append-only policy compliance
- Verificar audit log presence

**Actual**: `export_policy.py` tiene `validate_export()` pero **NO hay endpoint REST**

**Impacto**: **BLOCKER** para FI-UI-FEAT-113 (Badges Integridad)

---

### GAP 3: API Export Session ❌ P0
**Necesidad**: FI-UI-FEAT-105 (Copy/Export Procedencia), 116 (Bulk Export) requieren:
- `POST /api/export/session` - Export sesión a MD/PDF/JSON con procedencia
- `POST /api/export/range` - Export rango de interacciones
- `POST /api/export/bulk` - Export múltiples sesiones
- Manifest generation automático
- Background jobs para exports largos (>5s)

**Actual**: `fi_exporter.py` existe pero **NO hay endpoints REST**

**Impacto**: **BLOCKER** para FI-UI-FEAT-105, 116

---

### GAP 4: API Búsqueda/Filtrado ❌ P0
**Necesidad**: FI-UI-FEAT-103 (Búsqueda y Filtros) requiere:
- `GET /api/sessions/search?q={query}` - Full-text search
- `GET /api/sessions?filter[date]={range}&filter[tags]={tags}` - Filtros
- Índice local (lunr.js side) o backend (elasticsearch/sqlite FTS)
- Response time <300ms (p95)

**Actual**: `search.py` existe con vector search, pero **NO hay**:
- ❌ Full-text search endpoint
- ❌ Filtrado por fecha/tags/provider
- ❌ Pagination
- ❌ Sort by relevance

**Impacto**: **BLOCKER** para FI-UI-FEAT-103

---

### GAP 5: API Stats Realtime ❌ P1
**Necesidad**: FI-UI-FEAT-101 (Chips de Métrica) requiere:
- `GET /api/stats/realtime?session_id={id}` - Métricas en tiempo real
- Tokens in/out por interacción
- Latency p95 por provider
- Cache hit rate
- Provider distribution

**Actual**: `metrics.py` existe pero **NO hay endpoint REST**

**Impacto**: BLOCKER para FI-UI-FEAT-101

---

### GAP 6: API Acciones Sesión ❌ P1
**Necesidad**: FI-UI-FEAT-110 (Acciones Rápidas), 117 (Marcar/Etiquetar), 118 (Toolbar) requieren:
- `POST /api/sessions/{id}/hold` - Marcar sesión como hold
- `POST /api/sessions/{id}/pin` - Pin sesión
- `POST /api/sessions/{id}/tag` - Agregar tags
- `DELETE /api/sessions/{id}` - Eliminar sesión (con audit log)
- `POST /api/sessions/{id}/verify` - Trigger verificación manual

**Actual**: **NO existe ninguno**

**Impacto**: BLOCKER para FI-UI-FEAT-110, 117, 118

---

### GAP 7: Timeline Auto-Generation Endpoint ❌ P1
**Necesidad**: FI-UI-FEAT-100+ pueden beneficiarse de:
- `POST /api/timeline/generate` - Trigger auto-timeline con Ollama
- `GET /api/timeline/{session_id}` - Obtener timeline ya generado
- Status: pending/in_progress/completed/failed
- Modo: auto/manual/assisted

**Actual**: `timeline_auto.py` tiene `AutoTimelineGenerator` pero **NO hay endpoint REST**

**Impacto**: Nice-to-have para FI-UI-FEAT-100 (modo auto)

---

## 📋 CARDS BACKEND FALTANTES (Propuesta)

### Card 1: FI-API-FEAT-002 - Timeline REST API ⭐ P0 CRÍTICO
**Descripción**: API REST completa para Timeline UI

**Endpoints**:
```python
GET    /api/timeline/sessions              # Listar sesiones con metadata
GET    /api/timeline/sessions/{id}         # Timeline completo de sesión
GET    /api/timeline/sessions/{id}/events  # Solo eventos (sin raw interactions)
GET    /api/timeline/sessions/{id}/stats   # Session stats (timespan, size, badges)
```

**Response Models**:
```python
class SessionHeaderData:
    session_id: str
    metadata: SessionMetadata      # session_id, thread_id, user_id, owner_hash
    timespan: SessionTimespan      # start, end, duration_ms, duration_human
    size: SessionSize              # interaction_count, total_tokens, avg, size_human
    badges: PolicyBadges           # hash_verified, policy_compliant, redaction_applied, audit_logged

class TimelineResponse:
    timeline_id: str
    session_id: str
    owner_hash: str
    events: List[TimelineEvent]    # Con causality chains
    generation_mode: str           # auto/manual/assisted
    redaction_stats: Dict[str, int]
```

**Dependencias**:
- `timeline_models.py` ✅
- `timeline_auto.py` ✅
- `corpus_ops.py` ✅
- `audit_logs.py` ✅

**AC (Acceptance Criteria)**:
- ✅ Response time p95 <300ms para sesiones con ≤50 eventos
- ✅ Todos los badges calculados correctamente (hash/policy/redaction/audit)
- ✅ Timeline events incluyen causality chains
- ✅ Redaction policy aplicada (no raw content expuesto)
- ✅ CORS configurado para Aurity (port 9000)
- ✅ OpenAPI docs en `/docs`

**Estimación**: 8h (2 días @ 4h/día)
**Prioridad**: P0 - BLOCKER para Sprint A (FI-UI-FEAT-100, 104, 113)

---

### Card 2: FI-API-FEAT-003 - Verify Hash Endpoint ⭐ P0 CRÍTICO
**Descripción**: Endpoint para verificación de integridad

**Endpoints**:
```python
POST   /api/verify/session         # Verify session integrity
POST   /api/verify/interaction     # Verify single interaction
POST   /api/verify/export          # Verify export manifest
```

**Request/Response**:
```python
class VerifyRequest:
    session_id: Optional[str]
    interaction_id: Optional[str]
    export_manifest_path: Optional[str]

class VerifyResponse:
    verified: bool
    hash_match: bool
    policy_compliant: bool
    audit_logged: bool
    redaction_applied: bool
    details: Dict[str, Any]  # Información adicional si falla
```

**Dependencias**:
- `export_policy.py` ✅ (`validate_export`)
- `corpus_identity.py` ✅ (`verify_corpus_ownership`)
- `audit_logs.py` ✅
- `append_only_policy.py` ✅

**AC**:
- ✅ Verification completes in <500ms
- ✅ Returns detailed failure reasons
- ✅ Audit log de verificaciones
- ✅ No expone raw content ni hashes completos (solo prefijos)

**Estimación**: 4h (1 día @ 4h/día)
**Prioridad**: P0 - BLOCKER para FI-UI-FEAT-113

---

### Card 3: FI-API-FEAT-004 - Export Session API ⭐ P0
**Descripción**: Endpoints para export con procedencia

**Endpoints**:
```python
POST   /api/export/session          # Export sesión (MD/PDF/JSON)
POST   /api/export/range            # Export rango de interacciones
POST   /api/export/bulk             # Export múltiples sesiones
GET    /api/export/{job_id}/status  # Status de export en background
GET    /api/export/{job_id}/download # Download export completado
```

**Request**:
```python
class ExportRequest:
    session_id: str
    format: str  # markdown | pdf | json
    purpose: str  # backup | analysis | compliance | research
    include_timeline: bool = True
    include_raw_interactions: bool = False  # Redaction control

class ExportResponse:
    job_id: str
    status: str  # queued | in_progress | completed | failed
    manifest_path: Optional[str]
    download_url: Optional[str]
    estimated_seconds: Optional[int]
```

**Dependencias**:
- `fi_exporter.py` ✅
- `export_policy.py` ✅
- Background job queue (puede ser simple async con FastAPI)

**AC**:
- ✅ Export con manifest automático (SHA256, procedencia)
- ✅ Background job si export >5s
- ✅ Progress tracking para exports largos
- ✅ Audit log de exports
- ✅ 3 formatos soportados (MD, PDF, JSON)

**Estimación**: 8h (2 días @ 4h/día)
**Prioridad**: P0 - BLOCKER para FI-UI-FEAT-105, 116

---

### Card 4: FI-API-FEAT-005 - Search & Filter API ⭐ P0
**Descripción**: Endpoints para búsqueda y filtrado

**Endpoints**:
```python
GET    /api/sessions/search?q={query}&limit={n}   # Full-text search
GET    /api/sessions?filter[date]={range}         # Filtrado por fecha
GET    /api/sessions?filter[tags]={tags}          # Filtrado por tags
GET    /api/sessions?filter[provider]={provider}  # Filtrado por LLM provider
GET    /api/sessions?sort={field}&order={asc|desc} # Sorting
```

**Query Params**:
```python
q: str                          # Search query
filter[date]: str               # ISO date range (e.g., "2025-10-01,2025-10-31")
filter[tags]: str               # Comma-separated tags
filter[provider]: str           # claude | ollama | openai
sort: str                       # timestamp | tokens | duration
order: str                      # asc | desc
limit: int = 50                 # Pagination limit
offset: int = 0                 # Pagination offset
```

**Response**:
```python
class SearchResponse:
    results: List[SessionSummary]
    total: int
    limit: int
    offset: int
    query: str
    filters: Dict[str, Any]
```

**Dependencias**:
- `search.py` ✅ (vector search, puede extenderse)
- `corpus_ops.py` ✅
- SQLite FTS (si >500 sessions) o lunr.js (client-side si <500)

**AC**:
- ✅ Search response time <300ms p95 para <500 sessions
- ✅ Filtrado multi-dimensional (date + tags + provider combinados)
- ✅ Pagination funcional
- ✅ Sorting por múltiples campos
- ✅ Audit log de búsquedas

**Estimación**: 6h (1.5 días @ 4h/día)
**Prioridad**: P0 - BLOCKER para FI-UI-FEAT-103

---

### Card 5: FI-API-FEAT-006 - Realtime Stats API ⭐ P1
**Descripción**: Endpoint para métricas en tiempo real

**Endpoints**:
```python
GET    /api/stats/realtime?session_id={id}    # Stats de sesión específica
GET    /api/stats/dashboard                   # Stats globales del corpus
```

**Response**:
```python
class RealtimeStats:
    session_id: str
    metrics: List[MetricChip]  # tokens_in, tokens_out, latency, provider, cache_hit

class MetricChip:
    label: str              # "Tokens In"
    value: str              # "8,542"
    unit: str               # "tokens"
    trend: Optional[str]    # "up" | "down" | "stable"
    color: str              # "green" | "yellow" | "red"
```

**Dependencias**:
- `metrics.py` ✅
- `corpus_ops.py` ✅

**AC**:
- ✅ Response time <100ms
- ✅ 5 chips implementados (tokens in/out, latency, provider, cache hit)
- ✅ Trend calculation (vs previous session)
- ✅ Dashboard stats (global corpus metrics)

**Estimación**: 4h (1 día @ 4h/día)
**Prioridad**: P1 - BLOCKER para FI-UI-FEAT-101

---

### Card 6: FI-API-FEAT-007 - Session Actions API ⭐ P1
**Descripción**: Endpoints para acciones sobre sesiones

**Endpoints**:
```python
POST   /api/sessions/{id}/hold      # Mark as hold
POST   /api/sessions/{id}/pin       # Pin session
POST   /api/sessions/{id}/tag       # Add tags
DELETE /api/sessions/{id}           # Delete session (with audit)
POST   /api/sessions/{id}/verify    # Trigger manual verification
```

**Request/Response**:
```python
class SessionActionRequest:
    action: str                # hold | pin | tag | delete | verify
    tags: Optional[List[str]]  # For tag action
    reason: Optional[str]      # For delete action (audit trail)

class SessionActionResponse:
    success: bool
    session_id: str
    action: str
    audit_log_id: str          # Reference to audit log entry
    timestamp: str
```

**Dependencias**:
- `audit_logs.py` ✅
- `corpus_ops.py` ✅

**AC**:
- ✅ Todas las acciones generan audit log
- ✅ Delete es soft delete (flag en metadata, no borrado físico)
- ✅ Pin/hold persisten en corpus metadata
- ✅ Tags son searchable (integrado con FI-API-FEAT-005)
- ✅ Verify trigger genera background job

**Estimación**: 5h (1.25 días @ 4h/día)
**Prioridad**: P1 - BLOCKER para FI-UI-FEAT-110, 117, 118

---

### Card 7: FI-API-FEAT-008 - Auto-Timeline Generation API ⭐ P1
**Descripción**: Endpoint para generación automática de timeline

**Endpoints**:
```python
POST   /api/timeline/generate           # Trigger auto-timeline generation
GET    /api/timeline/generate/{job_id}  # Status de generación
```

**Request/Response**:
```python
class GenerateTimelineRequest:
    session_id: str
    mode: str                # auto | assisted
    provider: str            # ollama | claude (default: ollama)
    model: Optional[str]     # qwen2.5:7b-instruct-q4_0

class GenerateTimelineResponse:
    job_id: str
    status: str              # pending | in_progress | completed | failed
    timeline_id: Optional[str]
    events_generated: Optional[int]
    causality_edges: Optional[int]
    error: Optional[str]
```

**Dependencias**:
- `timeline_auto.py` ✅ (`AutoTimelineGenerator`)
- `llm_adapter.py` ✅
- Background job queue

**AC**:
- ✅ Auto-generation usa Ollama (qwen2.5 o deepseek-r1-distill-7b)
- ✅ Timeout 8s, fallback a manual+assist si falla
- ✅ Background job para sesiones grandes (>50 eventos)
- ✅ Progress tracking
- ✅ Audit log de generaciones

**Estimación**: 6h (1.5 días @ 4h/día)
**Prioridad**: P1 - Nice-to-have para FI-UI-FEAT-100

---

## 📊 Resumen de Gaps

| Card | Descripción | Prioridad | Estimación | Sprint | Cards UI Bloqueadas |
|------|-------------|-----------|------------|--------|---------------------|
| **FI-API-FEAT-002** | Timeline REST API | ⭐ P0 | 8h | Sprint A | 100, 104, 113 |
| **FI-API-FEAT-003** | Verify Hash Endpoint | ⭐ P0 | 4h | Sprint A | 113 |
| **FI-API-FEAT-004** | Export Session API | ⭐ P0 | 8h | Sprint A | 105, 116 |
| **FI-API-FEAT-005** | Search & Filter API | ⭐ P0 | 6h | Sprint A | 103 |
| **FI-API-FEAT-006** | Realtime Stats API | P1 | 4h | Sprint B | 101 |
| **FI-API-FEAT-007** | Session Actions API | P1 | 5h | Sprint B | 110, 117, 118 |
| **FI-API-FEAT-008** | Auto-Timeline Generation API | P1 | 6h | Sprint B | - |

**Total Estimado**: 41 horas (P0: 26h, P1: 15h)
**Sprints**: Sprint A (26h P0), Sprint B (15h P1)
**Capacidad**: 2 backend devs × 3 semanas × 4h/día = 48h disponibles ✅

---

## 🚀 Plan de Ejecución

### Sprint A - Backend Foundation (P0, 26h, Semanas 1-2)
**Objetivo**: Habilitar Sprint A del Timeline UI (cards 100, 101, 103, 104, 108, 111, 113)

**Orden de implementación**:
1. **Día 1-2**: FI-API-FEAT-002 (Timeline REST API) - 8h
   - Habilita: FI-UI-FEAT-100 (Encabezado), 104 (Metadatos)

2. **Día 3**: FI-API-FEAT-003 (Verify Hash) - 4h
   - Habilita: FI-UI-FEAT-113 (Badges Integridad)

3. **Día 4-5**: FI-API-FEAT-004 (Export Session) - 8h
   - Habilita: FI-UI-FEAT-105 (Export básico)

4. **Día 6**: FI-API-FEAT-005 (Search & Filter) - 6h
   - Habilita: FI-UI-FEAT-103 (Búsqueda)

**Entregable**: API completa para Sprint A del Timeline UI

---

### Sprint B - Backend Superpowers (P1, 15h, Semana 3)
**Objetivo**: Habilitar Sprint B del Timeline UI (cards 102, 105, 106, 107, 110, 112, 114, 115, 116, 117, 118, 119)

**Orden de implementación**:
1. **Día 7**: FI-API-FEAT-006 (Realtime Stats) - 4h
   - Habilita: FI-UI-FEAT-101 (Chips Métrica)

2. **Día 8**: FI-API-FEAT-007 (Session Actions) - 5h
   - Habilita: FI-UI-FEAT-110 (Acciones Rápidas), 117 (Marcar), 118 (Toolbar)

3. **Día 9**: FI-API-FEAT-008 (Auto-Timeline) - 6h
   - Habilita: FI-UI-FEAT-100 (modo auto)

**Entregable**: API completa para Sprint B del Timeline UI

---

## ✅ Definition of Done (Backend APIs)

### Performance
- ✅ Response time p95 <300ms para endpoints síncronos
- ✅ Background jobs para operaciones >5s (export, auto-timeline)
- ✅ CORS configurado para Aurity (port 9000)

### Security & Compliance
- ✅ Audit log para TODAS las acciones (export, delete, verify, search)
- ✅ Redaction policy aplicada (no raw content en responses)
- ✅ Owner hash validation en requests
- ✅ No exponer hashes completos (solo prefijos 16 chars)

### Quality
- ✅ OpenAPI docs completos (`/docs`)
- ✅ Pydantic models con validación
- ✅ Error handling con status codes HTTP correctos
- ✅ Logging estructurado con `backend/logger.py`
- ✅ Tests unitarios para cada endpoint (pytest)

### Integration
- ✅ Compatible con `fi_corpus_api.py` existente (no duplicar endpoints)
- ✅ Usa módulos existentes (`timeline_models.py`, `corpus_ops.py`, etc.)
- ✅ Port allocation según `docs/PORTS.md` (TBD: definir port para Timeline API)

---

## 🔗 Referencias

- **Timeline UI Roadmap**: `docs/TIMELINE_OPERATIVO_ROADMAP.md`
- **Timeline Models**: `backend/timeline_models.py`
- **Auto-Timeline Generator**: `backend/timeline_auto.py`
- **Corpus API Existente**: `backend/fi_corpus_api.py`
- **AURITY Gateway**: `backend/aurity_gateway.py`
- **Port Allocation**: `docs/PORTS.md`

---

**Conclusión**: Se requieren **7 cards backend** (41h estimadas) para soportar completamente el Timeline UI. Las 4 cards P0 (26h) son CRÍTICAS para Sprint A y deben implementarse en paralelo al desarrollo del frontend.

**Siguiente acción**: Crear las 7 cards en Trello con labels P0/P1 + Core + estimaciones + AC.
