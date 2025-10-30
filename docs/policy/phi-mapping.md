# Axioma → Práctica: Mapeo Operativo

**Card**: FI-PHI-MAN-001
**Companion to**: `PHILOSOPHY_CORPUS.md`
**Date**: 2025-10-29

---

## Tabla de Mapeo

| Aforismo | Concepto Filosófico | Principio de Ingeniería | Implementación Concreta | Card de Referencia |
|----------|---------------------|------------------------|-------------------------|-------------------|
| **1. Materia = Glitch Elegante** | La imperfección es condición de lo real | Error Budgets & Chaos Engineering | SLO 99.9% (no 100%)<br>Append-only HDF5<br>SHA256 hashes inmutables<br>Audit logs obligatorios | FI-DATA-FEAT-002<br>FI-SEC-FEAT-003<br>FI-RELIABILITY-STR-001 |
| **2. Humano = App en Beta** | El usuario es aprendiz perpetuo | UX de Onboarding Continuo | Session replays en Timeline<br>Tooltips contextuales<br>Feedback loops en cada acción<br>Undo/Redo en todas las mutaciones | FI-UI-FEAT-100<br>FI-UX-STR-001<br>FI-UI-FEAT-103 |
| **3. Dios = Full-Stack del Cosmos** | Arquitectura emerge del dominio | Domain-Driven Design & Local-First | Hexagonal architecture<br>Policy-as-code (YAML)<br>LAN-only by default<br>Corpus como fuente de verdad | FI-CORE-FEAT-001<br>FI-SEC-FEAT-002<br>FI-POLICY-STR-001 |
| **4. Gnóstico/Alquimista = Tester OG** | Conocimiento por experimentación | Golden Sets & Property Testing | Golden datasets en tests/<br>Benchmark suites automáticos<br>Regression tests obligatorios<br>Performance p95/p99 tracking | FI-TEST-FEAT-009<br>FI-TEST-FEAT-010<br>FI-OBS-RES-001 |

---

## Decisiones de Diseño Derivadas

### De Axioma 1 (Materia = Glitch):
- **Decisión**: Almacenamiento append-only sin mutaciones
- **Rationale**: Si la materia es impermanente, sellamos lo que ya ocurrió (hashes) en lugar de pretender "corregir" el pasado
- **Card**: FI-DATA-FEAT-002

---

### De Axioma 2 (Humano = Beta):
- **Decisión**: Timeline con session replays detallados
- **Rationale**: Si el humano aprende iterativamente, necesitamos replay completo de su "debugging mental"
- **Card**: FI-UI-FEAT-100

---

### De Axioma 3 (Dios = Full-Stack):
- **Decisión**: Local-first, cloud-optional (NAS > AWS)
- **Rationale**: La arquitectura ideal respeta la soberanía del dominio (datos del usuario en su hardware, no en nube ajena)
- **Card**: FI-SEC-FEAT-002, FI-INFRA-FEAT-008

---

### De Axioma 4 (Gnóstico = Tester):
- **Decisión**: Golden datasets obligatorios antes de deployment
- **Rationale**: El conocimiento empírico (tests) precede la fe (deployment). No hay gnosis sin falsificación
- **Card**: FI-OBS-RES-001, FI-TEST-FEAT-011

---

## Anti-Patterns Filosóficos

| Anti-Pattern | Violación de Axioma | Consecuencia Técnica | Ejemplo Prohibido |
|-------------|---------------------|---------------------|------------------|
| **"100% uptime guaranteed"** | Materia = Glitch | Promesas imposibles → pérdida de confianza | SLO de 100% en docs |
| **"Interfaz intuitiva sin onboarding"** | Humano = Beta | Usuarios perdidos → abandono | UI sin tooltips ni help |
| **"Cloud-first architecture"** | Dios = Full-Stack | Dependencia externa → pérdida de soberanía | AWS como única opción |
| **"Deploy sin tests"** | Gnóstico = Tester | Bugs en producción → regression loops | PR merge sin CI pass |

---

## Uso del Mapeo

**Para decisiones de arquitectura:**
1. Identificar el aforismo relevante
2. Consultar principio de ingeniería asociado
3. Verificar si existe card de implementación
4. Si no existe, crear nueva card con tag filosófico

**Ejemplo**:
- Pregunta: _"¿Agregamos cache mutable para performance?"_
- Aforismo: Materia = Glitch (cache es glitch elegante, pero mutación viola append-only)
- Decisión: Cache read-only con invalidación por hash
- Card: FI-DATA-ENH-002 (si no existe, crearla)

---

## Referencias Cruzadas

- **Corpus Hermeticum**: `PHILOSOPHY_CORPUS.md`
- **Políticas Operativas**: `docs/policies/`
- **Sprint Rituals**: `docs/SPRINT_RITUALS.md`
- **Definition of Done**: Ver DoD en cada card

---

_"As above, so below. As in philosophy, so in code."_
