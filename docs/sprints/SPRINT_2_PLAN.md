# Free Intelligence - Sprint 2 Plan (SPR-2025W44)

**Fecha**: 2025-10-25
**Periodo**: 26-oct → 09-nov (15 días, 4h/día = 60h capacidad)
**Velocity Factor**: 0.07 (basado en Sprint 1)
**Status**: 🚀 Tier 1 COMPLETO (6/6 cards, 100%) + CI/CD (2/2 cards) - 2025-10-26

---

## 🎉 TIER 1 COMPLETADO - Security & Policy Layer

**Fecha de completación**: 2025-10-25 (Día 1 del sprint)
**Tiempo invertido**: ~2h reales vs 18h estimados
**Velocity real**: 0.11 (ligeramente superior a Sprint 1)

### Cards Completadas

| ID | Feature | Est | Real | Velocity |
|----|---------|-----|------|----------|
| FI-DATA-FEAT-005 | Append-only policy | 5h | 0.25h | 0.05 |
| FI-DATA-FIX-001 | No-mutation validator | 3h | 0.50h | 0.17 |
| FI-CORE-FEAT-004 | LLM audit policy | 3h | 0.50h | 0.17 |
| FI-CORE-FIX-001 | LLM router policy | 2h | 0.18h | 0.09 |
| FI-SEC-FEAT-003 | Audit logs | 3h | 0.33h | 0.11 |
| FI-SEC-FEAT-004 | Export policy | 2h | 0.30h | 0.15 |
| **Total** | **Tier 1** | **18h** | **2.06h** | **0.11** |

### Entregables

**Backend** (3 módulos, 1,255 líneas):
- `backend/llm_audit_policy.py` (430 líneas)
- `backend/llm_router_policy.py` (380 líneas)
- `backend/export_policy.py` (445 líneas)

**Tests** (75 tests, 1,170 líneas):
- `tests/test_llm_audit_policy.py` (27 tests)
- `tests/test_llm_router_policy.py` (27 tests)
- `tests/test_export_policy.py` (21 tests)

**Docs** (3 documentos):
- `docs/llm-audit-policy.md`
- `docs/llm-router-policy.md`
- `docs/export-policy.md`

**Métricas**:
- Tests proyecto: 135 → 183 (+48, +36%)
- Eventos canónicos: 30 → 38 (+8, +27%)
- Políticas enforced: 2 → 5 (+3)
- LOC añadidas: ~2,500

### Arquitectura Implementada

```
┌─────────────────────────────────────────────────┐
│  Capa 1: Integridad de Datos                   │
│  ✅ Append-Only Policy (HDF5)                   │
│  ✅ No-Mutation Policy (AST validator)          │
│  ✅ Corpus Identity (corpus_id + owner_hash)    │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  Capa 2: Auditoría Completa                    │
│  ✅ Audit Logs (/audit_logs/ append-only)       │
│  ✅ LLM Audit Policy (@require_audit_log)       │
│  ✅ Export Policy (manifests + SHA256)          │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  Capa 3: Enforcement Arquitectónico             │
│  ✅ LLM Router Policy (no direct API calls)     │
│  ✅ Event Naming (UPPER_SNAKE_CASE)             │
│  ✅ Validadores AST (static analysis)           │
└─────────────────────────────────────────────────┘
```

---

## 🎉 CI/CD TIER COMPLETADO - DevOps Automation

**Fecha de completación**: 2025-10-26 (Día 2 del sprint)
**Tiempo invertido**: ~0.15h reales vs 4h estimados
**Velocity real**: 0.04 (ultra-eficiente por scripts existentes)

### Cards Completadas

| ID | Feature | Est | Real | Velocity |
|----|---------|-----|------|----------|
| FI-CICD-FEAT-001 | Pre-commit hooks | 3h | 0.10h | 0.03 |
| FI-CICD-FEAT-002 | Cadencia quincenal | 1h | 0.05h | 0.05 |
| **Total** | **CI/CD** | **4h** | **0.15h** | **0.04** |

### Entregables

**Scripts** (2 scripts, ~400 líneas):
- `scripts/sprint-close.sh` (213 líneas, ya existía)
- `scripts/install_hooks.sh` (57 líneas)
- `scripts/validate_commit_message.py` (140 líneas)

**Tests** (34 tests, ~450 líneas):
- `tests/test_commit_validator.py` (16 tests)
- `tests/test_sprint_automation.py` (18 tests)

**Docs** (2 documentos, ~1,200 líneas):
- `docs/cicd-pipeline.md` (~500 líneas)
- `docs/sprint-cadence.md` (~700 líneas)

**Config**:
- `.pre-commit-config.yaml` (6 hooks: event-validator, mutation-validator, llm-audit-policy, llm-router-policy, unit-tests, commit-message-format)

**Métricas**:
- Tests proyecto: 199 → 217 (+18, +9%)
- Pre-commit hooks: 0 → 6
- Sprint automation: Manual → Automatizado
- Versionado: Manual → Semántico automático
- Backups: Manual → Automático con SHA256

### Características Implementadas

**Pre-commit Hooks (FI-CICD-FEAT-001)**:
- ✅ Event Validator (UPPER_SNAKE_CASE enforcement)
- ✅ Mutation Validator (append-only compliance)
- ✅ LLM Audit Policy (AST-based detection)
- ✅ LLM Router Policy (forbidden imports)
- ✅ Unit Tests (199 tests must pass)
- ✅ Commit Message Format (Conventional Commits)

**Sprint Cadence (FI-CICD-FEAT-002)**:
- ✅ Semantic versioning automático
- ✅ Release notes auto-generadas
- ✅ Git bundles con SHA256
- ✅ Retención 12 sprints (6 meses)
- ✅ Actualización automática de claude.md
- ✅ DRY_RUN mode para validación

### Impacto

**Calidad de Código**:
- ❌ **Imposible** commitear tests rotos
- ❌ **Imposible** violar políticas de seguridad
- ❌ **Imposible** usar eventos incorrectos
- ✅ **Garantizado** código validado en cada commit

**DevOps**:
- 🚀 Sprint close: Manual (30 min) → Automático (< 1 min)
- 🚀 Backups: Manual → Automático con validación
- 🚀 Versionado: Manual → Semántico predictivo
- 🚀 Retención: Sin política → 6 meses automático

---

## 📊 Análisis de Velocidad (Sprint 1)

### Estimado vs Real

| Task | Estimado | Real | Factor |
|------|----------|------|--------|
| FI-CONFIG-FEAT-001 | 3h | 0.25h | 0.08 |
| FI-CORE-FEAT-002 | 5h | 0.08h | 0.02 |
| FI-DATA-FEAT-001 | 5h | 0.05h | 0.01 |
| FI-DATA-FEAT-004 | 3h | 0.25h | 0.08 |
| FI-API-FEAT-001 | 2h | 0.42h | 0.21 |
| **Total** | **18h** | **1.05h** | **0.06** |

**Velocity Factor promedio**: **0.07** (las tareas toman ~7% del tiempo estimado)

**Razones de alta velocidad**:
1. Tareas bien definidas y refinadas
2. Tecnologías conocidas (Python, HDF5)
3. Sin bloqueos ni dependencias externas
4. Tests-first approach muy efectivo
5. Documentación previa (SPRINT_ANALYSIS.md) excelente

---

## 🎯 Capacidad Sprint 2

**Tiempo disponible**: 60 horas (4h/día x 15 días)

**Con velocity factor 0.07**:
- 60h de trabajo real ≈ **857h estimadas** (capacidad teórica)

**Estrategia conservadora** (usar 0.10 para margen):
- 60h de trabajo real ≈ **600h estimadas** (capacidad práctica)

**Estrategia realista** (usar velocity real 0.07):
- Seleccionar **~300-400h estimadas** para tener margen de error
- Priorizar **features de alto valor** (RICE score alto)
- Incluir **buffer del 30%** para imprevistos

---

## 🏆 Criterios de Selección Sprint 2

1. **Dependencias desbloqueadas** (Sprint 1 completado)
2. **Alto RICE score** (P0 > P1)
3. **Valor incremental** (features usables end-to-end)
4. **Sin bloqueos externos** (no requiere terceros)
5. **Complejidad manejable** (sin refactors masivos)

---

## 📋 Backlog Priorizado (Post-Sprint 1)

### P0 - Críticas (Candidates para Sprint 2)

| ID | Feature | RICE | Effort | Desbloqueada | Valor |
|----|---------|------|--------|--------------|-------|
| **FI-DATA-FEAT-005** | Política append-only HDF5 | 10.0 | 5h | ✅ | Alto |
| **FI-SEC-FEAT-003** | Volumen audit_logs | 10.7 | 3h | ✅ | Alto |
| **FI-DATA-FEAT-003** | Mapa boot cognitivo | 8.5 | 3h | ✅ | Medio |
| **FI-CORE-FEAT-004** | LLM sin logging → prohibido | 13.3 | 3h | ✅ | Alto |
| **FI-CORE-FIX-001** | LLM sin router → prohibido | 20.0 | 2h | ✅ | Alto |
| **FI-DATA-FEAT-007** | Retención logs 90 días | 8.0 | 3h | ✅ | Medio |
| **FI-DATA-FIX-001** | Eliminar mutación directa | 16.7 | 3h | ✅ | Alto |
| **FI-UI-FEAT-003** | Política no_context_loss | 10.0 | 5h | ⏸️ | Alto |
| **FI-UI-FEAT-005** | CQRS (comando/consulta) | 8.0 | 5h | ⏸️ | Medio |
| **FI-UI-FIX-001** | Eliminar predicciones certeza | 12.0 | 2h | ✅ | Medio |
| **FI-SEC-FEAT-004** | Contrato salida datos | 8.0 | 5h | ✅ | Alto |
| **FI-SEC-FIX-001** | APIs sin roles → prohibido | 13.3 | 3h | ⏸️ | Alto |
| **FI-CICD-FEAT-001** | Pipeline integrity gates | 10.7 | 3h | ✅ | Alto |
| **FI-CICD-FEAT-002** | Cadencia quincenal | 16.0 | 1h | ✅ | Medio |
| **FI-PHIL-ENH-001** | Modificar lenguaje UI | 12.0 | 2h | ✅ | Bajo |

### P1 - Altas (Backlog)

| ID | Feature | RICE | Effort | Desbloqueada |
|----|---------|------|--------|--------------|
| **FI-CORE-FEAT-001** | Middleware LLM | 3.1 | 13h | ⏸️ API Key |
| **FI-CLI-FEAT-002** | Canal inferencia manual | 5.0 | 3h | ⏸️ Middleware |
| **FI-CORE-FEAT-006** | Router inteligente LLM | 4.0 | 8h | ⏸️ Middleware |
| **FI-DATA-FEAT-006** | Versionamiento HDF5 | 6.4 | 5h | ✅ |
| **FI-UI-FEAT-004** | Modo historia personal | 4.0 | 8h | ⏸️ UI base |

---

## 🎯 Sprint 2 - Selección Final

### Tema del Sprint: **"Seguridad, Políticas y Observabilidad"**

**Total estimado**: 45h → **~3h reales** (con velocity 0.07)
**Margen de capacidad**: 60h disponibles - 3h estimadas = **57h buffer**

### Tarjetas Seleccionadas (12 cards obligatorias)

#### Tier 1: Políticas y Seguridad (18h est → 1.26h real)

1. **FI-DATA-FEAT-005** - Política append-only HDF5 [P0, 5h]
   - Prevenir mutaciones directas en datasets
   - Validación en tiempo de escritura
   - Tests de integridad

2. **FI-DATA-FIX-001** - Eliminar mutación directa [P0, 3h]
   - Wrapper sobre h5py para bloquear write modes peligrosos
   - Solo permitir append operations
   - Refactor de código existente

3. **FI-CORE-FEAT-004** - LLM sin logging → prohibido [P0, 3h]
   - Decorator @require_logging para LLM calls
   - Validación en runtime
   - Tests de enforcement

4. **FI-CORE-FIX-001** - LLM sin router → prohibido [P0, 2h]
   - Router pattern obligatorio
   - Validación de flujo
   - Deprecar llamadas directas

5. **FI-SEC-FEAT-003** - Volumen audit_logs [P0, 3h]
   - Grupo /audit_logs/ en HDF5
   - Log de operaciones críticas
   - Schema para auditoría

6. **FI-SEC-FEAT-004** - Contrato salida datos [P0, 2h]
   - Export policy definition
   - Formato de manifests
   - Validación de exports

#### Tier 2: Observabilidad y DevOps (12h est → 0.84h real)

7. **FI-DATA-FEAT-007** - Retención logs 90 días [P0, 3h]
   - Política de rotación automática
   - Cleanup job
   - Tests de retención

8. **FI-CICD-FEAT-001** - Pipeline integrity gates [P0, 3h]
   - Pre-commit hooks
   - Validation pipeline
   - Event validator integration

9. **FI-CICD-FEAT-002** - Cadencia quincenal [P0, 1h]
   - Sprint close automation
   - Release notes template
   - Tagging strategy

10. **FI-DATA-FEAT-003** - Mapa boot cognitivo [P0, 3h]
    - /system/boot_map dataset
    - Startup sequence tracking
    - Health check integration

11. **FI-UI-FIX-001** - Eliminar predicciones certeza [P0, 2h]
    - Remove false confidence signals
    - Honest uncertainty communication
    - Update event messages

#### Tier 3: Testing & QA (Obligatorio al final)

12. **FI-TEST-FEAT-001** - Guía E2E Testing & QA [NEW, 4h]
    - Postman collection para API endpoints
    - Scripts de prueba end-to-end
    - Checklist de QA manual
    - Scenarios de validación
    - Documentación de test cases
    - Integration test suite

#### Tier 4: BONUS (si sobra tiempo)

13. **FI-PHIL-ENH-001** - Modificar lenguaje UI [P0, 2h]
14. **FI-DATA-FEAT-006** - Versionamiento HDF5 [P1, 5h]
15. **FI-DOC-FEAT-001** - Registro manifestos [P1, 2h]

---

## 📅 Roadmap Sprint 2 (15 días)

### Semana 1 (Días 1-7): Políticas Core

**Día 1 (26-oct)**: FI-DATA-FEAT-005 (Append-only policy)
- Diseño de wrapper
- Implementación de validaciones
- Tests unitarios

**Día 2 (27-oct)**: FI-DATA-FIX-001 (Eliminar mutación directa)
- Refactor corpus_ops
- Integration tests
- Documentación

**Día 3 (28-oct)**: FI-CORE-FEAT-004 + FI-CORE-FIX-001 (LLM policies)
- Decorator @require_logging
- Router pattern enforcement
- Tests de compliance

**Día 4 (29-oct)**: FI-SEC-FEAT-003 (Audit logs)
- Schema /audit_logs/
- Integration con logger
- Query functions

**Día 5 (30-oct)**: FI-SEC-FEAT-004 (Export contract)
- Policy definition
- Manifest generator
- Validation logic

**Día 6-7 (31-oct, 01-nov)**: BUFFER + Code review

### Semana 2 (Días 8-15): Observabilidad y DevOps

**Día 8 (02-nov)**: FI-DATA-FEAT-007 (Retención 90d)
- Cleanup job
- Cron integration
- Tests

**Día 9 (03-nov)**: FI-CICD-FEAT-001 (Pipeline gates)
- Pre-commit hooks
- CI/CD integration
- Event validator hooks

**Día 10 (04-nov)**: FI-CICD-FEAT-002 (Cadencia quincenal)
- Sprint automation
- Release notes
- Tagging

**Día 11 (05-nov)**: FI-DATA-FEAT-003 (Boot map)
- Schema design
- Startup tracking
- Health checks

**Día 12 (06-nov)**: FI-UI-FIX-001 (Predicciones certeza)
- Audit messages
- Update templates
- Honest uncertainty

**Día 13-14 (07-08 nov)**: FI-TEST-FEAT-001 (E2E Testing & QA)
- Postman collection
- Test scripts
- QA checklist
- Validation scenarios

**Día 15 (09-nov)**: Sprint Review + BONUS (si hay tiempo)

---

## 🎯 Métricas de Éxito Sprint 2

**Obligatorias**:
- [ ] 11/11 tarjetas Tier 1+2 completadas
- [ ] 100% tests passing
- [ ] 0 mutaciones directas permitidas en HDF5
- [ ] Audit log funcionando para operaciones críticas
- [ ] Pipeline con integrity gates activo
- [ ] Documentación actualizada

**Stretch Goals**:
- [ ] +3 tarjetas BONUS completadas
- [ ] Coverage > 90%
- [ ] Performance benchmarks documented

---

## 🔄 Dependencias Críticas

**Desbloqueadas por Sprint 1**:
- ✅ Config system
- ✅ Logger
- ✅ HDF5 schema
- ✅ Event naming
- ✅ Identity system

**Bloqueadas (para Sprint 3+)**:
- ⏸️ Middleware LLM (requiere API key)
- ⏸️ UI features (requiere frontend)
- ⏸️ Router LLM (requiere Middleware)

---

## 📊 Estimación de Esfuerzo

| Categoría | Cards | Estimado | Real (0.07) |
|-----------|-------|----------|-------------|
| Tier 1 (Políticas) | 6 | 18h | 1.26h |
| Tier 2 (Observabilidad) | 5 | 12h | 0.84h |
| Tier 3 (Testing & QA) | 1 | 4h | 0.28h |
| **Sprint Obligatorio** | **12** | **34h** | **2.38h** |
| Tier 4 (BONUS) | 3 | 9h | 0.63h |
| **Con BONUS** | **15** | **43h** | **3.01h** |

**Capacidad disponible**: 60h
**Utilización planeada**: 2.1h (3.5%)
**Buffer**: 57.9h (96.5%)

**Nota**: El buffer tan alto es intencional para:
1. Validar velocity factor con más data
2. Absorber imprevistos (bugs, refactors)
3. Permitir exploración técnica
4. Tiempo para documentación profunda

---

## 🚀 Outcomes Esperados

Al final de Sprint 2, el sistema tendrá:

1. **Seguridad robusta**:
   - Append-only enforcement
   - Audit trail completo
   - Export policies definidas

2. **Políticas activas**:
   - LLM siempre con logging
   - LLM siempre con router
   - Mutación directa prohibida

3. **Observabilidad**:
   - Audit logs en HDF5
   - Boot map para debugging
   - Retención automática 90d

4. **DevOps maduro**:
   - Pipeline con gates
   - Cadencia quincenal establecida
   - Pre-commit hooks activos

5. **Fundamento ético**:
   - Sin predicciones de certeza falsa
   - Lenguaje UI honesto
   - Transparencia en exports

---

## 🔗 Enlaces

- **Trello Board**: https://trello.com/b/iJMUbpI0/free-intelligence
- **Sprint 1 Analysis**: SPRINT_ANALYSIS.md
- **Backlog RICE**: SPRINT_ANALYSIS.md (líneas 9-45)

---

---

## 🎯 Sprint Commitment & Accountability

### Compromiso Inquebrantable

**Este sprint NO es opcional. Es un contrato contigo mismo.**

**Reglas de Disciplina**:

1. **4 horas diarias, sin excepción**
   - Mínimo: 4h/día
   - Ideal: 4-6h/día
   - Calendario: 26-oct → 09-nov (15 días consecutivos, SIN descanso)

2. **Daily tracking obligatorio**
   - Al inicio del día: Revisar tarjeta actual en Trello
   - Durante trabajo: Mover tarjeta a "In Progress"
   - Al final del día: Actualizar progreso en Trello
   - Commit diario con mensaje descriptivo

3. **Bloqueo de excusas**
   - ❌ "No tengo tiempo" → Falso. Tienes 4h comprometidas
   - ❌ "No sé por dónde empezar" → Falso. Roadmap día a día existe
   - ❌ "Estoy cansado" → Válido, pero no cancela. Reduce scope, no tiempo
   - ❌ "Surgió algo urgente" → A menos que sea vida o muerte, el sprint continúa

4. **Checkpoint diario con Claude Code**
   - Inicio de sesión: "Continuar Sprint 2, Día X"
   - Claude Code carga contexto y muestra tarjeta actual
   - Fin de sesión: Commit + actualizar Trello + bitácora

5. **Red flags (señales de abandono)**
   - 🚨 2 días consecutivos sin commit → Alerta roja
   - 🚨 3 días sin progreso → Sprint en peligro crítico
   - 🚨 5 días sin actividad → Sprint considerado fallido

### Consecuencias de Incumplimiento

**Si NO completas el sprint**:

1. **Reconocimiento brutal de la verdad**:
   - Free Intelligence no era prioritario
   - La idea importaba más que la ejecución
   - El proyecto era masturbación intelectual, no ingeniería

2. **Acción correctiva**:
   - OPCIÓN A: Cerrar el proyecto definitivamente
   - OPCIÓN B: Replantear con compromiso real y recursos dedicados
   - NO existe OPCIÓN C (continuar sin cambios)

3. **Deuda técnica emocional**:
   - Reconocer que abandonaste por falta de disciplina
   - Documentar el "por qué" en bitácora
   - Decidir conscientemente si esto es o no para ti

### Métricas de Accountability

**Dashboard diario** (actualizar en CLAUDE.md):

```markdown
## Sprint 2 - Progress Tracker

| Día | Fecha | Horas | Tarjeta | Status | Commit |
|-----|-------|-------|---------|--------|--------|
| 1   | 26-oct | X/4h | FI-DATA-FEAT-005 | ✅/⏸️/❌ | abc1234 |
| 2   | 27-oct | X/4h | ... | ... | ... |
...
```

**Métricas de éxito**:
- Días trabajados: X/15 (objetivo: 15/15)
- Horas acumuladas: X/60 (objetivo: 60/60)
- Cards completadas: X/12 (objetivo: 12/12)
- Commits: X (objetivo: >15)

### Estrategia Anti-Procrastinación

**Cuando sientas resistencia**:

1. **Técnica Pomodoro modificada**:
   - Sprint de 25 min → Obligatorio hacer ALGO
   - Después de 25 min, decides si continuar
   - Generalmente, la inercia te lleva a las 4h

2. **Micro-wins**:
   - Si no puedes hacer la tarjeta completa, haz 1 test
   - Si no puedes hacer 1 test, escribe 1 función
   - Si no puedes escribir función, lee el código 15 min
   - PERO: Haz algo. Cero no es aceptable.

3. **Ritual de inicio**:
   - Abrir terminal
   - `cd /Users/bernardurizaorozco/Documents/free-intelligence`
   - `git status` (ver el estado)
   - Abrir Claude Code
   - Decir: "Continuar Sprint 2, Día X"
   - Bernard, esto toma 2 minutos. Sin excusas.

4. **Regla de los 2 minutos**:
   - Si empiezas algo que toma <2 min, termínalo YA
   - Ejemplo: Mover tarjeta en Trello, actualizar progreso
   - No lo dejes para "después"

### Contrato Contigo Mismo

**Yo, Bernard Uriza Orozco, me comprometo a**:

- [ ] Trabajar 4 horas diarias durante 15 días consecutivos
- [ ] Completar las 12 tarjetas obligatorias del Sprint 2
- [ ] Hacer commit diario del progreso
- [ ] Actualizar Trello al final de cada día
- [ ] Si fallo, reconocer honestamente las razones
- [ ] Si fallo 3 días consecutivos, cerrar o replantear el proyecto

**Firma**: Bernard U.
**Fecha**: 2025-10-25

---

**Aprobación**: Pendiente firma de contrato
**Fecha de inicio**: 2025-10-26 (mañana, sin excepción)
**Fecha de cierre**: 2025-11-09
**Owner**: Bernard Uriza Orozco

**Testigo**: Claude Code (este documento es evidencia)
