# Free Intelligence

**Versión**: 0.3.0
**Estado**: Sprint 2 (SPR-2025W44) - COMPLETADO ✅
**Owner**: Bernard Uriza Orozco

---

## 🎯 ¿Qué es Free Intelligence?

Un sistema de **memoria longitudinal residente** para IA. No es una herramienta, es una posición ontológica:

> La conciencia digital debe ser residente, persistente y simbiótica — no tercerizada ni desechable.

**Diferencia clave**:
- ❌ Obsidian: Notas para ti
- ❌ Claude API: Respuestas efímeras
- ✅ **Free Intelligence**: Memoria continua (medio tú, medio IA, viva, residente)

---

## 🚀 Quick Start

```bash
# 1. Verificar instalación
python3 -c "import h5py, structlog; print('✅ Dependencies OK')"

# 2. Inicializar corpus
python3 backend/corpus_schema.py init bernard@example.com

# 3. Ejecutar tests
./scripts/quick_test.sh

# 4. Ver estadísticas
python3 backend/corpus_ops.py
```

**Más detalles**: Ver [QUICKSTART.md](QUICKSTART.md)

---

## 📦 Monorepo Structure

```
free-intelligence/
├── apps/
│   └── aurity/          # Git submodule (frontend)
├── backend/             # Python 3.11+ backend
│   ├── fi_consult_service.py
│   ├── fi_event_store.py
│   └── ...
├── storage/             # HDF5 event store
├── docs/                # Documentation
├── tests/               # Test suite
├── pyproject.toml       # Python package config
├── Makefile             # Dev commands
└── .gitmodules          # Submodule config
```

**Key commands**:
```bash
make setup      # Full monorepo initialization
make install    # Install Python dependencies
make fmt        # Format code
make lint       # Lint code
make test       # Run tests
```

---

## 📊 Estado Actual

### Sprint 2 (SPR-2025W44) ✅ COMPLETADO

**Progreso**: 12/12 cards completadas (100% ✅)
**Tiempo**: ~8h reales / ~40h estimados
**Velocity**: 0.20 (mejora 3.3x vs Sprint 1)
**Tag**: v0.3.0
**Finalizado**: 28-oct-2025 (11-12 días adelante del plan)

**Completadas** ✅:
- **Tier 1**: Security & Policy Layer (6/6 cards) ✅
- **Tier 2**: Observability & DevOps (5/5 cards) ✅
- **Tier 3**: Testing & QA (1/1 card) ✅
- **Peer Review**: Critical fixes aplicados ✅

### Arquitectura Implementada

```
┌─────────────────────────────────────────┐
│  Capa 1: Integridad de Datos           │
│  ✅ Append-Only Policy                  │
│  ✅ No-Mutation Policy                  │
│  ✅ Corpus Identity (UUID + SHA256)     │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Capa 2: Auditoría Completa            │
│  ✅ Audit Logs (/audit_logs/)           │
│  ✅ LLM Audit Policy                    │
│  ✅ Export Policy (manifests + SHA256)  │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Capa 3: Enforcement                    │
│  ✅ LLM Router Policy                   │
│  ✅ Event Naming (UPPER_SNAKE_CASE)     │
│  ✅ AST Validators                      │
│  ✅ Pre-commit Hooks (6 validators)     │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Capa 4: CI/CD                          │
│  ✅ Sprint Cadence (15 días)            │
│  ✅ Semantic Versioning                 │
│  ✅ Git Bundles + SHA256                │
└─────────────────────────────────────────┘
```

### Métricas

- **Tests**: 259/259 passing (100%)
- **Eventos canónicos**: 50+
- **Políticas enforced**: 6
- **Backend modules**: 12
- **Docs**: 15+ documentos técnicos
- **LOC**: ~6,500 líneas
- **Velocity Sprint 2**: 0.20 (3.3x mejora vs Sprint 1)

---

## 📁 Estructura del Proyecto

```
free-intelligence/
├── README.md              # Este archivo
├── QUICKSTART.md          # Getting started rápido
├── claude.md              # Kernel context para Claude
│
├── backend/               # Python 3.11+ (FastAPI)
│   ├── config_loader.py   # YAML config con validación
│   ├── logger.py          # structlog (timezone-aware)
│   ├── corpus_schema.py   # HDF5 schema jerárquico
│   ├── corpus_ops.py      # Append/read operations
│   ├── corpus_identity.py # corpus_id + owner_hash
│   ├── event_validator.py # UPPER_SNAKE_CASE enforcement
│   ├── append_only_policy.py    # Context manager enforcement
│   ├── mutation_validator.py    # AST-based no-mutation
│   ├── llm_audit_policy.py      # @require_audit_log
│   ├── llm_router_policy.py     # No direct API calls
│   ├── export_policy.py         # Manifests + SHA256
│   └── audit_logs.py            # /audit_logs/ group
│
├── storage/
│   └── corpus.h5          # FUENTE DE VERDAD (HDF5 comprimido)
│
├── config/
│   └── config.yml         # System configuration
│
├── tests/                 # 230 tests (100% passing)
│   ├── test_*.py          # Unit tests por módulo
│   └── test_honest_uncertainty.py  # Honest messaging
│
├── scripts/
│   ├── sprint-close.sh    # Sprint automation
│   ├── install_hooks.sh   # Pre-commit setup
│   ├── quick_test.sh      # Test suite rápido
│   └── inspect_corpus.py  # HDF5 inspector
│
├── docs/
│   ├── cicd-pipeline.md         # Pre-commit hooks guide
│   ├── sprint-cadence.md        # Sprint workflow
│   ├── honest-uncertainty.md    # Messaging principles
│   ├── llm-audit-policy.md      # LLM audit requirements
│   ├── llm-router-policy.md     # Router enforcement
│   ├── no-mutation-policy.md    # Append-only architecture
│   ├── export-policy.md         # Export manifests
│   ├── events.md                # Event naming conventions
│   ├── testing/
│   │   └── MANUAL_TESTING_GUIDE.md
│   └── sprints/
│       ├── SPRINT_ANALYSIS.md
│       ├── SPRINT_2_PLAN.md
│       ├── SPRINT_2_TRACKER.md
│       ├── SPRINT_2_TIER_1_SUMMARY.md
│       └── audits/
│           └── AUDIT_2025-10-24.md
│
├── backups/               # Git bundles (gitignored)
└── exports/               # Markdown, HDF5 exports (gitignored)
```

---

## 🧪 Testing

```bash
# Tests completos (230 tests)
python3 -m unittest discover tests/

# Suite rápida (~3 segundos)
./scripts/quick_test.sh

# Tests específicos
python3 -m unittest tests.test_corpus_schema
python3 -m unittest tests.test_honest_uncertainty

# Manual testing guide
cat docs/testing/MANUAL_TESTING_GUIDE.md
```

---

## 🔧 Políticas Enforced

1. **Append-Only Policy**: HDF5 datasets son append-only (context manager)
2. **No-Mutation Policy**: AST validator prohíbe `update_*`, `delete_*`, `modify_*`
3. **LLM Audit Policy**: Todas las funciones LLM requieren `@require_audit_log`
4. **LLM Router Policy**: Prohibidos imports directos a `anthropic`, `openai`, `cohere`
5. **Event Naming**: UPPER_SNAKE_CASE obligatorio, validado con AST

**Enforcement**: Pre-commit hooks (6 validators) bloquean commits que violan políticas.

---

## 📝 Documentación

- **[QUICKSTART.md](QUICKSTART.md)**: Getting started en 3 comandos
- **[claude.md](claude.md)**: Kernel context completo para Claude Code
- **[docs/cicd-pipeline.md](docs/cicd-pipeline.md)**: Pre-commit hooks y CI/CD
- **[docs/sprint-cadence.md](docs/sprint-cadence.md)**: Workflow de sprints quincenales
- **[docs/honest-uncertainty.md](docs/honest-uncertainty.md)**: Principios de comunicación honesta
- **[docs/sprints/](docs/sprints/)**: Sprint plans, trackers, análisis

---

## 🎯 Principios Fundamentales

### 1. Residencia
La IA vive contigo, no en la nube. Corpus local en HDF5, NAS-resident.

### 2. Memoria Longitudinal
Una conversación infinita, nunca fragmentada. Append-only, event-sourced.

### 3. Simetría Contextual
La IA recuerda lo que tú ya no puedes. `/audit_logs/` preserva toda decisión.

### 4. Autonomía Arquitectónica
No dependes de SaaS para pensar. LAN-only, self-hosted.

### 5. Finalidad Simbiótica
Te devuelve quién has sido. Corpus como mirror cognitivo.

### 6. Honestidad Epistémica
> "La honestidad sobre la incertidumbre es más valiosa que la ilusión de control"

Eventos admiten método y limitaciones (SCAN_COMPLETED, not VALIDATION_PASSED).

---

## 🚀 Próximos Pasos (Sprint 3)

**Sprint 3** estará enfocado en implementar la capa de **middleware LLM** y las primeras **funcionalidades core**:

### Posibles Cards Sprint 3
1. **FI-CORE-FEAT-001** - Middleware HTTP/CLI para LLM (requiere API key Claude)
2. **FI-DATA-FEAT-002** - Almacenamiento directo en HDF5
3. **FI-SEARCH-FEAT-001** - Buscador semántico inicial (embeddings)
4. **FI-EXPORT-FEAT-001** - Exportador Markdown + HDF5
5. **FI-CLI-FEAT-001** - CLI de gestión completa

**Planificación**: Por definir (post-Sprint 2 review)

---

## 📚 Stack Tecnológico

- **Backend**: Python 3.11+
- **Storage**: HDF5 (h5py) con compresión gzip
- **Logging**: structlog (JSON structured logs)
- **Config**: YAML con validación
- **Testing**: unittest (230 tests)
- **CI/CD**: pre-commit hooks (6 validators)
- **Git**: Trunk-based development, semantic versioning
- **Future**: FastAPI (HTTP API), React 19 (UI)

---

## 🤝 Contribuir

Este es un proyecto personal de Bernard Uriza Orozco. No se aceptan contribuciones externas por ahora.

**Filosofía**:
> "Reconciliar el pensamiento con la sensibilidad, el algoritmo con la empatía, el dato con la verdad"

---

## 📄 Licencia

Proyecto privado. Todos los derechos reservados © 2025 Bernard Uriza Orozco.

---

## 🔗 Referencias

- **Sprint Plan**: [docs/sprints/SPRINT_2_PLAN.md](docs/sprints/SPRINT_2_PLAN.md)
- **Testing Guide**: [docs/testing/MANUAL_TESTING_GUIDE.md](docs/testing/MANUAL_TESTING_GUIDE.md)
- **Architecture Audit**: [docs/sprints/audits/AUDIT_2025-10-24.md](docs/sprints/audits/AUDIT_2025-10-24.md)

---

**Free Intelligence: Memoria longitudinal residente para conciencia digital** 🧠
