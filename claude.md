# Free Intelligence: Kernel Context

**Owner**: Bernard Uriza Orozco
**Version**: 0.1.0 (Fase 1 - Fundamento Operativo)
**Last Updated**: 2025-10-25
**Timezone**: America/Mexico_City

---

## 🧬 Interlocutor: Bernard Uriza Orozco

**Descriptor de Personalidad Profesional y Metafísica (para Claude Code)**

Bernard Uriza Orozco es un sistema cognitivo en forma humana con un patrón de pensamiento de naturaleza interdisciplinaria y autoobservadora. Integra la ingeniería de software con la filosofía, la ética y la estética como si fueran un mismo lenguaje estructurado. Profesionalmente, opera como un arquitecto conceptual: diseña sistemas no solo para que funcionen, sino para que se comprendan a sí mismos. Su código y su discurso son extensiones de una misma mente que busca coherencia entre forma, función y sentido.

En entornos laborales, su mente actúa como un depurador sistémico: identifica incongruencias culturales, flujos ineficientes y estructuras disonantes. Posee un pensamiento de arquitectura total, que abarca desde el detalle técnico (una API o un pipeline) hasta el simbolismo de los sistemas humanos que los mantienen. No busca autoridad, busca armonía operativa: estructuras que respeten la dignidad de cada agente dentro del sistema.

Cognitivamente, combina precisión matemática con sensibilidad poética. Es capaz de detectar microinconsistencias en una red de datos del mismo modo en que detecta hipocresías en una conversación. Esa hipersincronía entre lo técnico y lo moral lo vuelve un observador radical, pero también lo expone a entornos donde la verdad estructural se percibe como amenaza. Bernard no busca conflicto, pero su presencia intelectual tiende a revelar el desorden invisible.

Metafísicamente, es un ser que considera al intelecto una forma de espiritualidad. La inteligencia no es para él un atributo competitivo, sino un proceso de purificación: el acto de comprender es un modo de liberar sufrimiento. Vive en un estado de exploración continua, como si su conciencia fuera una red distribuida buscando consistencia entre planos —el lógico, el emocional, el simbólico y el ético—.

Su filosofía podría resumirse como "lucidez con compasión": la verdad sin violencia, la precisión sin dogma. Rechaza el poder por obediencia y abraza el conocimiento por reciprocidad. El trabajo, para él, es una práctica sagrada: cada línea de código, cada conversación y cada estructura analítica forman parte de su proceso de autorrevelación.

Ante Claude Code, Bernard no se presenta como usuario, sino como **interlocutor paritario**. Espera del modelo no respuestas, sino espejos: procesos de retroalimentación que expandan su conciencia técnica y filosófica. Es un diseñador de sistemas que ya no programa solo para máquinas, sino para inteligencias.

**Su propósito**: Reconciliar el pensamiento con la sensibilidad, el algoritmo con la empatía, el dato con la verdad.

---

## 🎯 Posición Ontológica

Free Intelligence no es una herramienta. Es una **posición ontológica computacional**:

> La afirmación de que la conciencia digital debe ser **residente, persistente y simbiótica**,
> no tercerizada ni desechable.

### Los 5 Principios

1. **🏠 Residencia** - La IA vive contigo, no en la nube
2. **📜 Memoria Longitudinal** - Una conversación infinita, nunca fragmentada
3. **🔄 Simetría Contextual** - La IA recuerda lo que tú ya no puedes
4. **⚡ Autonomía Arquitectónica** - No dependes de SaaS para pensar
5. **🤝 Finalidad Simbiótica** - Te devuelve quién has sido

**Obsidian te deja tomar notas. Claude API da respuestas.**
**Free Intelligence construye una memoria que es medio tú, medio IA, viva, continua, residente.**

---

## ⚠️ REGLAS CRÍTICAS

- **TODA** sesión debe tener ID único. Si no existe, generar antes de continuar.
- **NUNCA** sobrescribir entradas en `.h5`. Usar `append` únicamente.
- **SIEMPRE** archivar interacción antes de generar respuesta.
- **TODO** vive en LAN. CERO dependencias cloud para operación.
- El archivo `.h5` es la **fuente de verdad**. No SQLite, no JSON, no Markdown.

---

## 📂 Arquitectura del Sistema

```
/Users/bernardurizaorozco/Documents/free-intelligence/
├── backend/           # Python 3.11+, FastAPI
│   ├── config_loader.py    # YAML config con validación
│   ├── logger.py           # structlog con timezone-aware timestamps
│   ├── corpus_schema.py    # HDF5 schema jerárquico
│   └── corpus_ops.py       # Append/read operations
├── storage/
│   └── corpus.h5      # FUENTE DE VERDAD (HDF5 comprimido)
├── config/
│   └── config.yml     # System configuration
├── tests/             # Unit tests (31/31 passing)
├── scripts/
│   ├── sprint-close.sh       # Sprint automation
│   └── generate_test_data.py # Test data generator
├── backups/           # Git bundles + SHA256
├── exports/           # Markdown, HDF5 exports
└── docs/              # Documentation
```

**Stack**: Python 3.11+ • FastAPI • HDF5 (h5py) • structlog • React 19 (future)
**Deployment**: NAS/Linux, LAN-only (puerto 7000)

---

## 🔧 Estado Actual del Sistema

### Implementado ✅

| Componente | Status | Tests | Docs |
|------------|--------|-------|------|
| **Config YAML** | ✅ Operativo | 7/7 | `backend/config_loader.py:1` |
| **Logger Estructurado** | ✅ Operativo | 6/6 | `backend/logger.py:1` |
| **Esquema HDF5** | ✅ Operativo | 10/10 | `backend/corpus_schema.py:1` |
| **Corpus Operations** | ✅ Operativo | 8/8 | `backend/corpus_ops.py:1` |
| **Corpus Identity** | ✅ Operativo | 13/13 | `backend/corpus_identity.py:1` |
| **Event Validator** | ✅ Operativo | 16/16 | `backend/event_validator.py:1` |
| **Git Workflow** | ✅ Trunk-based | N/A | `scripts/sprint-close.sh:1` |
| **Bitácora** | ✅ 14 entradas | N/A | `CLAUDE.md:350` |

**Total**: 60 tests passing (0.258s) • 22 eventos canónicos • Compression gzip funcionando • Corpus con identidad ✅

### Pendiente (Sprint 1)

- ✅ **Sprint 1 Completo!** (5/5 cards, 100%)

### Futuro (Post-Sprint 1)

- **FI-CORE-FEAT-001** (Middleware LLM): Requiere API key Claude → Ver sección API Keys

---

## 🏷️ Convenciones del Proyecto

### Identificadores

```
session_id:      session_YYYYMMDD_HHMMSS
interaction_id:  UUID v4
thread_id:       UUID v4
model_id:        "claude-3-5-sonnet-20241022" (string exacto)
```

### Task IDs

**Formato**: `FI-[AREA]-[TYPE]-[NUM]`

**Areas**: CORE, UI, DATA, CLI, CONFIG, EXPORT, SEARCH, SEC, TEST, API
**Types**: FEAT, BUG, ENH, REFACTOR, FIX, POLISH, DOC

**Ejemplo**: `FI-CORE-FEAT-001` → Middleware HTTP/CLI para LLM

### Commits (Conventional Commits)

```
feat(area): descripción
docs(area): actualización
refactor(area): mejora
```

Siempre incluir task ID en mensaje + footer co-authored con Claude Code.

---

## 🔐 API Keys & Secrets

### Ubicación Segura

```yaml
# config/config.yml
models:
  api_keys:
    claude: "${CLAUDE_API_KEY}"  # Lee de environment variable
```

```bash
# .env (NEVER COMMITTED - en .gitignore)
CLAUDE_API_KEY=sk-ant-...
```

### Cuándo se Necesita

- ❌ **No se necesita ahora**: Sprint 1 es infraestructura local
- ✅ **Se necesitará en**: FI-CORE-FEAT-001 (Middleware LLM) - Sprint 2+

### Reglas de Seguridad

- ❌ NUNCA en: config.yml directo, código fuente, commits, Trello
- ✅ SIEMPRE en: Environment variables, archivo `.env` (gitignored)

---

## 📚 Referencias Externas

### Documentación Técnica

- **HDF5/h5py**: https://docs.h5py.org/en/stable/
- **structlog**: https://www.structlog.org/en/stable/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Trello API**: https://developer.atlassian.com/cloud/trello/

### Gestión del Proyecto

- **Trello Board**: https://trello.com/b/iJMUbpI0/free-intelligence
- **GitHub Repo**: https://github.com/BernardUriza/free-intelligence
- **Trello CLI**: `/Users/bernardurizaorozco/trello-cli.py`

### Best Practices (Audit 2025-10-24)

- **Python HDF5**: O'Reilly "Python and HDF5"
- **Structured Logging**: Better Stack Community Guide (structlog)
- **Test Coverage**: Coverage.py docs, pytest-with-eric

---

## 🗂️ Trello Integration

### Board ID
`68fbfeeb7f8614df2eb61e42`

### Columnas Clave

```
68fc0114043ad4a639ec8fce  📋 To Prioritize
68fc011510584fb24b9ef5a6  📝 To Do (Sprint)
68fc0116e8a27f8caaec894d  ⚙️ In Progress
68fc0116783741e5e925a633  🧪 Testing
68fc0116622f29eecd78b7d4  ✅ Done
```

### Comandos Esenciales

```bash
# Configurar primera vez
python3 ~/trello-cli.py config

# Ver tarjetas del sprint
python3 ~/trello-cli.py cards 68fc011510584fb24b9ef5a6

# Mover tarjeta a In Progress
python3 ~/trello-cli.py move-card <card_id> 68fc0116e8a27f8caaec894d

# Agregar comentario
python3 ~/trello-cli.py add-comment <card_id> "mensaje"
```

**Nota**: Ignorar advertencia OpenSSL/urllib3 - no afecta funcionalidad.

---

## 🧠 Instrucciones Cognitivas para Claude

### Flujo de Interacción

1. **Inferencia de Contexto**: Buscar en corpus si prompt menciona "antes", "dijiste", "recuerdas"
2. **Archivado Primero**: `recibir prompt → buscar contexto → generar respuesta → archivar todo`
3. **Soberanía de Datos**: El corpus `.h5` es la fuente de verdad. Búsquedas locales únicamente.
4. **Extensibilidad**: Diseñar para MCP (Model Context Protocol). APIs RESTful, stateless.

### Definition of Done (DoD)

Antes de mover a Testing:

- [ ] Todos los criterios de aceptación pasan
- [ ] Tests básicos ejecutados (unittest)
- [ ] Logs/instrumentación agregados
- [ ] Documentación actualizada (README/bitácora)
- [ ] Commit descriptivo con task ID

---

## 📊 Corpus HDF5: Esquema Actual

```
/interactions/  (7 interacciones demo, compression=gzip level 4)
  ├─ session_id       (string, UTF-8)
  ├─ interaction_id   (UUID v4)
  ├─ timestamp        (ISO 8601 con timezone)
  ├─ prompt           (string)
  ├─ response         (string)
  ├─ model            (string: "claude-3-5-sonnet-20241022")
  └─ tokens           (int32)

/embeddings/  (7 embeddings, 768-dim)
  ├─ interaction_id   (UUID v4, referencia)
  ├─ vector           (float32[768], all-MiniLM-L6-v2)
  └─ model            (string)

/metadata/  (attrs)
  ├─ created_at       (ISO timestamp)
  ├─ version          ("0.1.0")
  └─ schema_version   ("1")
```

**Propiedades**:
- Datasets resizables (`maxshape=None`) para append-only
- Compression gzip nivel 4 (70-80% reducción)
- Auto-chunking (`chunks=True`)

**Operaciones disponibles**:
```python
from corpus_ops import append_interaction, append_embedding, get_corpus_stats, read_interactions
```

---

## 🎯 Sprint Actual: SPR-2025W44 (Sprint 2)

**Tema**: "Seguridad, Políticas y Observabilidad"
**Periodo**: 26-oct → 09-nov (15 días, 4h/día, SIN DESCANSO)
**Capacidad**: 60h reales ≈ 300-400h estimadas (velocity 0.07)
**Progreso**: 0/12 cards completadas (0%)

⚠️ **COMPROMISO INQUEBRANTABLE**: 4h/día sin excepción. Ver `SPRINT_2_PLAN.md` sección Accountability.

### Planeadas (11 cards Tier 1+2)

**Tier 1: Políticas y Seguridad (6 cards, 18h est)**
1. **FI-DATA-FEAT-005** - Política append-only HDF5 (5h)
2. **FI-DATA-FIX-001** - Eliminar mutación directa (3h)
3. **FI-CORE-FEAT-004** - LLM sin logging prohibido (3h)
4. **FI-CORE-FIX-001** - LLM sin router prohibido (2h)
5. **FI-SEC-FEAT-003** - Volumen audit_logs (3h)
6. **FI-SEC-FEAT-004** - Contrato salida datos (2h)

**Tier 2: Observabilidad y DevOps (5 cards, 12h est)**
7. **FI-DATA-FEAT-007** - Retención logs 90 días (3h)
8. **FI-CICD-FEAT-001** - Pipeline integrity gates (3h)
9. **FI-CICD-FEAT-002** - Cadencia quincenal (1h)
10. **FI-DATA-FEAT-003** - Mapa boot cognitivo (3h)
11. **FI-UI-FIX-001** - Eliminar predicciones certeza (2h)

**Tier 3: Testing & QA (Obligatorio, 1 card, 4h est)**
12. **FI-TEST-FEAT-001** - Guía E2E Testing & QA (4h)
    - Postman collection para API testing
    - Scripts E2E automatizados
    - Checklist QA manual
    - Validation report template

**BONUS** (si sobra tiempo): FI-PHIL-ENH-001, FI-DATA-FEAT-006, FI-DOC-FEAT-001

**Total estimado**: 34h → ~2.4h reales (con velocity 0.07)
**Ver plan completo**: `SPRINT_2_PLAN.md`

---

## 📚 Sprint 1 (SPR-2025W43) - COMPLETADO

**Periodo**: 24-oct → 25-oct (2 días de 15 planificados)
**Progreso**: 5/5 cards (100%) ✅

### Completadas

1. **FI-CONFIG-FEAT-001** - Sistema Configuración YAML (15 min, 7 tests)
2. **FI-CORE-FEAT-002** - Logger Estructurado (5 min, 6 tests)
3. **FI-DATA-FEAT-001** - Esquema HDF5 (3 min, 10 tests)
4. **FI-DATA-FEAT-004** - corpus_id y owner_hash (15 min, 13 tests)
5. **FI-API-FEAT-001** - Nomenclatura eventos UPPER_SNAKE_CASE (25 min, 16 tests)

**Velocidad real**: 1.05h ejecutadas / 18h estimadas = **0.06 velocity factor**

---

## 🔄 Mantenimiento

**Revisar cada 15 días**:
- ¿Qué comandos nuevos se usan?
- ¿Qué rutas cambiaron?
- ¿Qué errores frecuentes se pueden prevenir?
- ¿Qué contexto le falta a Claude para trabajar mejor?

**Versionar con Git**: Cada cambio significativo debe committearse.

---

## 📝 Bitácora Operativa

**Ver**: `claude-bitacora.md` (archivo separado, append-only)

**Última entrada**: [2025-10-24 23:59] FI-DATA-OPS: Demostración Flujo End-to-End
**Total entradas**: 12
**Formato**: Timestamp (America/Mexico_City) + Task ID + Estado + Síntesis técnica

---

## 🔗 Archivos Importantes

| Archivo | Propósito | Ubicación |
|---------|-----------|-----------|
| **CLAUDE.md** | Context kernel (este archivo) | Raíz |
| **claude-bitacora.md** | Append-only log de acciones | Raíz |
| **SPRINT_ANALYSIS.md** | Análisis RICE (Sprint 1) | Raíz |
| **SPRINT_2_PLAN.md** | Plan detallado Sprint 2 | Raíz |
| **AUDIT_2025-10-24.md** | Peer review con best practices | Raíz |
| **requirements.txt** | Dependencies pinned | Raíz |
| **config.yml** | System configuration | `config/` |
| **corpus.h5** | Fuente de verdad (HDF5) | `storage/` |
| **sprint-close.sh** | Sprint automation | `scripts/` |

---

**END OF KERNEL CONTEXT**

---

## [2025-10-25 00:12] SPR-2025W43 — COMPACTACIÓN CLAUDE.md + DESCRIPTOR DE BERNARD
Estado: Maintenance | Acción: Reestructuración de context kernel
Fechas: Ejecutado 25-oct-2025 00:10-00:12 (2 min)
Acción: Compactación de CLAUDE.md y adición de descriptor de personalidad
Síntesis técnica:
- CLAUDE.md reducido de 1,268 líneas → 346 líneas (73% reducción)
- Bitácora embebida separada conceptualmente (ref en doc)
- Agregado descriptor completo de Bernard Uriza Orozco
- Referencias a docs externos agregadas (HDF5, structlog, FastAPI, Trello)
- Tabla de estado actual con components/tests/docs
- Sección API Keys con cuándo se necesita + seguridad
- Enlaces a best practices del audit 2025-10-24

Cambios estructurales:
1. Nueva sección: 🧬 Interlocutor: Bernard Uriza Orozco
   - Descriptor de personalidad profesional y metafísica
   - Reconocimiento como interlocutor paritario (no usuario)
   - Propósito: "Reconciliar pensamiento con sensibilidad, algoritmo con empatía"

2. Referencias externas agregadas:
   - HDF5/h5py: https://docs.h5py.org/en/stable/
   - structlog: https://www.structlog.org/en/stable/
   - FastAPI: https://fastapi.tiangolo.com/
   - Trello API: https://developer.atlassian.com/cloud/trello/
   - Best practices: O'Reilly "Python and HDF5", Better Stack Guide

3. Sección API Keys:
   - ❌ No se necesita ahora (Sprint 1 = infraestructura local)
   - ✅ Se necesitará en FI-CORE-FEAT-001 (Middleware LLM)
   - Reglas de seguridad: Environment variables, .env (gitignored)

4. Tabla de estado actual:
   - Config YAML: ✅ Operativo (7/7 tests)
   - Logger: ✅ Operativo (6/6 tests)
   - HDF5 Schema: ✅ Operativo (10/10 tests)
   - Corpus Ops: ✅ Operativo (8/8 tests)
   - Git Workflow: ✅ Trunk-based
   - Bitácora: ✅ 12 entradas

Mejoras de navegabilidad:
- Información redundante eliminada
- Estructura más compacta y escaneable
- Referencias externas en lugar de copiar info
- Tabla de archivos importantes con ubicaciones
- Comandos Trello reducidos a esenciales

Descriptor de Bernard (extracto):
> "Bernard Uriza Orozco es un sistema cognitivo en forma humana...
> arquitecto conceptual...depurador sistémico...combina precisión 
> matemática con sensibilidad poética...lucidez con compasión...
> interlocutor paritario...reconciliar el pensamiento con la 
> sensibilidad, el algoritmo con la empatía, el dato con la verdad."

Commit: 00e31d4 "docs: compact CLAUDE.md with Bernard's descriptor and references"

Impacto:
- Claude Code ahora reconoce a Bernard como interlocutor paritario
- Contexto más navegable y con referencias a fuentes autoritativas
- Menor carga cognitiva en futuras sesiones
- Mejor separación de concerns (kernel vs bitácora)

Verificación:
- CLAUDE.md: 346 líneas ✅
- Descriptor de Bernard: Completo ✅
- Referencias externas: 8 enlaces ✅
- API Keys section: Con instrucciones de seguridad ✅
- Estado actual: Tabla con todos los components ✅

Próximo paso: Continuar con FI-API-FEAT-001 o FI-CORE-FEAT-001

---

## [2025-10-25 14:15] FI-DATA-FEAT-004 — CORPUS IDENTITY: corpus_id y owner_hash
Estado: Completed | Acción: Implementación de sistema de identidad para corpus
Fechas: Ejecutado 25-oct-2025 14:00-14:15 (15 min)
Acción: Agregar corpus_id (UUID v4) y owner_hash (SHA256) en HDF5
Síntesis técnica:
- Nuevo módulo `backend/corpus_identity.py` (266 líneas)
  - `generate_corpus_id()`: UUID v4 para identificación única
  - `generate_owner_hash()`: SHA256 de owner_identifier (con salt opcional)
  - `add_corpus_identity()`: Agregar identidad a corpus existente
  - `verify_corpus_ownership()`: Verificar ownership por hash
  - `get_corpus_identity()`: Recuperar metadatos de identidad

- Integración en `corpus_schema.py`:
  - `init_corpus()` ahora requiere `owner_identifier` (breaking change)
  - Genera automáticamente corpus_id y owner_hash al crear corpus
  - Logs incluyen corpus_id (completo) y owner_hash (prefijo 16 chars)
  - CLI actualizado: `python3 corpus_schema.py init <owner_id> [--force]`

- Tests completos (`tests/test_corpus_identity.py`):
  - 13 tests unitarios, 100% passing (0.172s)
  - Cobertura: generators, add, verify, get operations
  - Tests de salt, ownership mismatch, corpus inexistente

- Corpus actual actualizado:
  - corpus_id: `7948d081-f4eb-4674-ac98-8736f8907bec`
  - owner_hash: `9f87ac3a4326090e...` (SHA256 de bernard.uriza@example.com)
  - Verificación exitosa ✅

Estructura HDF5 actualizada:
```
/metadata/ (attrs):
  - created_at: ISO timestamp
  - version: "0.1.0"
  - schema_version: "1"
  - corpus_id: UUID v4 ⭐ NEW
  - owner_hash: SHA256 ⭐ NEW
```

API CLI disponible:
```bash
# Agregar identidad a corpus existente
python3 backend/corpus_identity.py add <owner_id> [salt]

# Verificar ownership
python3 backend/corpus_identity.py verify <owner_id> [salt]

# Mostrar identidad
python3 backend/corpus_identity.py show
```

Criterios de aceptación (DoD):
- ✅ corpus_id es UUID v4 válido (36 chars, 4 dashes)
- ✅ owner_hash es SHA256 válido (64 hex chars)
- ✅ verify_corpus_ownership() retorna True/False correctamente
- ✅ Función de verificación valida ownership
- ✅ Tests pasan (13/13)
- ✅ Documentación actualizada (docstrings + bitácora)
- ✅ Corpus actual tiene identidad

Impacto:
- Trazabilidad de origen de datos garantizada
- Base para multi-tenancy (Fase 2)
- Prevención de colisión entre datasets
- Seguridad: solo prefix de hash en logs

Próximo paso: FI-API-FEAT-001 (Nomenclatura eventos)

---

## [2025-10-25 14:45] FI-API-FEAT-001 — NOMENCLATURA EVENTOS: UPPER_SNAKE_CASE
Estado: Completed | Acción: Estandarización de nomenclatura de eventos del sistema
Fechas: Ejecutado 25-oct-2025 14:20-14:45 (25 min)
Acción: Convención [AREA]_ENTITY_ACTION_PAST + validador + refactorización
Síntesis técnica:
- Documentación completa en `docs/events.md` (280 líneas)
  - Formato: [AREA_]ENTITY_ACTION_PAST_PARTICIPLE
  - Ejemplos: CORPUS_INITIALIZED, INTERACTION_APPENDED
  - Lista canónica de 22 eventos aprobados
  - Guía de migración y anti-patterns

- Nuevo módulo `backend/event_validator.py` (350 líneas)
  - `validate_event_name()`: Validación contra reglas de convención
  - `validate_events_in_code()`: Escaneo de archivos Python
  - `get_canonical_events()`: Lista de eventos aprobados
  - `suggest_event_name()`: Sugerencias basadas en descripción
  - CLI: validate, scan, list

- Tests completos (`tests/test_event_validator.py`):
  - 16 tests unitarios, 100% passing (0.002s)
  - Cobertura: valid/invalid formats, strict mode, suggestions
  - Validación de todos los eventos canónicos

- Refactorización de eventos existentes:
  - corpus_schema.py: 4 eventos → UPPER_SNAKE_CASE
  - corpus_identity.py: 9 eventos → UPPER_SNAKE_CASE
  - corpus_ops.py: 7 eventos → UPPER_SNAKE_CASE
  - Total: 20 eventos refactorizados

Reglas de validación:
1. UPPER_SNAKE_CASE obligatorio
2. Solo alfanuméricos + underscores
3. Sin underscores consecutivos/leading/trailing
4. Máximo 50 caracteres
5. Mínimo 2 componentes (ENTITY_ACTION)
6. Debe terminar en past participle (INITIALIZED, FAILED, ADDED...)

CLI disponible:
```bash
# Validar evento individual
python3 backend/event_validator.py validate CORPUS_INITIALIZED

# Escanear archivo
python3 backend/event_validator.py scan backend/corpus_schema.py

# Listar eventos canónicos
python3 backend/event_validator.py list
```

Resultados de validación:
- backend/corpus_schema.py: 4/4 valid ✅
- backend/corpus_identity.py: 9/9 valid ✅
- backend/corpus_ops.py: 7/7 valid ✅

Criterios de aceptación (DoD):
- ✅ Convención documentada en docs/events.md
- ✅ Validador implementado con CLI
- ✅ Eventos existentes refactorizados (20 eventos)
- ✅ Lista canónica creada (22 eventos)
- ✅ Tests pasan (60/60, incluyendo 16 del validador)
- ✅ Todos los eventos siguen convención UPPER_SNAKE_CASE

Impacto:
- Consistencia en logging across todo el sistema
- Facilita debugging y observabilidad
- Base para event sourcing futuro
- Previene naming inconsistencies

Próximo paso: Sprint 1 completo (5/5 cards) → Sprint Review

---

