# 🌍 Plan Geológico del Backend Refactor - Free Intelligence

**Metáfora:** Eras Geológicas (4.6 mil millones de años → código limpio en ~40 horas)

**Progreso actual:** P1-4 COMPLETE ✅ (78/78 eventos audit logging migrados)

---

## 🦕 MESOZOICO (Era de los Repositorios) - ~8-10 horas

### Triásico: P1-5 Repository Mappers (2-3 horas)
**Objetivo:** Extraer lógica de mapeo DB ↔ Domain de repositories

**Archivos críticos:**
- `hdf5_soap_repository.py` - SOAPMapper extraction
- `postgres_patient_repository.py` - PatientMapper extraction
- `hdf5_session_repository.py` - SessionMapper extraction
- `hdf5_order_repository.py` - OrderMapper extraction

**Patrón:**
```python
# ANTES: Repository con mapeo embebido
def get_soap(self, session_id):
    hdf5_data = self._read_hdf5(...)
    return {  # Mapeo inline
        "subjective": hdf5_data["S"],
        "objective": hdf5_data["O"],
        ...
    }

# DESPUÉS: Repository + Mapper separados
class SOAPMapper:
    @staticmethod
    def to_domain(hdf5_data: dict) -> SOAPNote:
        return SOAPNote(
            subjective=hdf5_data["S"],
            objective=hdf5_data["O"],
            ...
        )

    @staticmethod
    def to_persistence(soap: SOAPNote) -> dict:
        return {"S": soap.subjective, "O": soap.objective, ...}

def get_soap(self, session_id):
    hdf5_data = self._read_hdf5(...)
    return SOAPMapper.to_domain(hdf5_data)  # Mapper se encarga
```

**Criterios de éxito:**
- [ ] 4 mappers creados en `backend/mappers/`
- [ ] Repositories solo llaman mappers (no lógica de conversión)
- [ ] Tests pass sin romper API pública

**Quick wins:**
- SessionMapper reutilizable en 3 repos diferentes
- SOAPMapper simplifica SOAP endpoint testing

---

### Jurásico: P2-1 Service Layer Completion (3-4 horas)
**Objetivo:** Completar extracción de lógica de negocio de `core/` → `services/`

**Estado actual:**
- ✅ 8 services extraídos (workflow, session, kpi, evidence, etc.)
- ❌ `core/` aún tiene ~15 archivos mezclando concerns

**Archivos a migrar:**
```
core/
├── llm_service.py          → services/llm/services/llm_service.py
├── persona_manager.py      → services/llm/services/persona_manager.py
├── prompt_builder.py       → services/llm/services/prompt_builder.py
├── memory_manager.py       → services/llm/services/memory_manager.py
├── embedding_service.py    → services/rag/services/embedding_service.py
├── vector_store.py         → services/rag/services/vector_store.py
├── rag_engine.py           → services/rag/services/rag_engine.py
└── ... (8 archivos más)
```

**Patrón de migración:**
1. Crear `services/<domain>/services/<service>.py`
2. Mover clase + dependencies
3. Crear `services/<domain>/dependencies.py` con factory
4. Actualizar imports en routers (usar Depends())
5. Deprecar `core/<file>.py` (comentar + redirect import)

**Criterios de éxito:**
- [ ] `core/` vacío excepto legacy files marcados DEPRECATED
- [ ] Todos los routers usan `Depends(get_<service>)`
- [ ] Zero import directo desde `core/`

---

### Cretácico: P2-2 Dependency Injection Consolidation (2-3 horas)
**Objetivo:** Eliminar service locator, usar DI puro en TODOS los endpoints

**Estado actual:**
- ✅ WorkflowOrchestrator usa DI (Depends())
- ✅ IntelligentOrchestrationService usa DI
- ❌ ~20 endpoints aún usan `get_container()` (service locator)

**Archivos críticos:**
```bash
# Buscar service locator usage
grep -r "get_container()" backend/api --include="*.py" | wc -l
# Expected: ~30 ocurrencias

# Endpoints a migrar (ejemplos):
- backend/api/routers/assistant/public/assistant/chat.py
- backend/api/routers/transcription/public/transcription.py
- backend/api/routers/session/internal/sessions/checkpoint.py
```

**Patrón de refactor:**
```python
# ANTES: Service locator (anti-pattern)
def create_session():
    container = get_container()
    session_service = container.session_service  # Tight coupling
    return session_service.create(...)

# DESPUÉS: Dependency injection
def create_session(
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.create(...)  # Loose coupling
```

**Criterios de éxito:**
- [ ] Zero llamadas a `get_container()` en `backend/api/`
- [ ] Todos los services tienen factory en `<domain>/dependencies.py`
- [ ] `container.py` puede deprecarse

---

## 🐘 CENOZOICO (Era de la Modularización) - ~12-15 horas

### Paleógeno: P3-1 Infrastructure Modularization (4-5 horas)
**Objetivo:** Dividir archivos gigantes en `infrastructure/` usando patrón index

**Archivos a modularizar:**
```
infrastructure/
├── workers/tasks/encryption_worker.py  (1249 líneas → 9 módulos)
│   ├── encryption/
│   │   ├── constants.py        (40 líneas)
│   │   ├── models.py           (80 líneas)
│   │   ├── integrity.py        (50 líneas)
│   │   ├── kms.py              (150 líneas)
│   │   ├── crypto.py           (180 líneas)
│   │   ├── hdf5_utils.py       (140 líneas)
│   │   ├── worker.py           (300 líneas)
│   │   ├── cli.py              (100 líneas)
│   │   └── __init__.py         (30 líneas - public API)
│
├── common/services/notifications.py   (650 líneas → 6 módulos)
│   ├── notification/
│   │   ├── models.py                  (80 líneas)
│   │   ├── providers/
│   │   │   ├── base.py                (30 líneas)
│   │   │   ├── twilio_sms.py          (100 líneas)
│   │   │   └── sendgrid_email.py      (110 líneas)
│   │   ├── service.py                 (150 líneas)
│   │   └── __init__.py                (20 líneas)
```

**Patrón index (encapsulación):**
```python
# __init__.py (public API contract)
from .worker import encrypt_session_worker
from .models import WorkerResult, SessionMetadata
from .constants import CRYPTO_VERSION

__all__ = [
    "encrypt_session_worker",  # Main entry point
    "WorkerResult",            # Return type
    "CRYPTO_VERSION",          # Version
]
# Módulos internos (kms, crypto, hdf5_utils) NO expuestos
```

**Criterios de éxito:**
- [ ] Max file size en infrastructure/: 300 líneas
- [ ] `__init__.py` declara API pública explícita
- [ ] Imports externos usan solo API pública

---

### Neógeno: P3-2 Domain Layer Refinement (3-4 horas)
**Objetivo:** Completar separación domain/ (entities, interfaces, services)

**Estado actual:**
- ✅ `domain/session/` bien estructurado (dependencies.py, interfaces/, services/)
- ❌ `domain/` root tiene archivos sin organizar

**Refactor necesario:**
```
domain/
├── session/           ✅ GOOD (modelo a seguir)
│   ├── dependencies.py
│   ├── services/session_service.py
│   └── interfaces/
├── soap/              ❌ TODO
│   ├── dependencies.py
│   ├── services/soap_service.py
│   └── interfaces/isoap_repository.py
├── patient/           ❌ TODO
├── order/             ❌ TODO
└── evidence/          ❌ TODO
```

**Patrón a replicar (de session/):**
```
<domain>/
├── dependencies.py         # FastAPI Depends() factories
├── services/
│   └── <domain>_service.py # Business logic
└── interfaces/
    └── i<domain>_repository.py  # Repository interface (ABC)
```

**Criterios de éxito:**
- [ ] 4 dominios migrados al patrón session/
- [ ] Cada dominio tiene dependencies.py
- [ ] Zero import cruzado entre dominios

---

### Cuaternario: P3-3 Testing Infrastructure (5-6 horas)
**Objetivo:** Setup testing con mocks + fixtures para DI

**Estado actual:**
- ✅ Algunos tests existen pero frágiles
- ❌ No hay fixtures reusables para DI
- ❌ Tests rompen cuando se refactoriza

**Setup necesario:**
```python
# tests/conftest.py (fixtures globales)
@pytest.fixture
def mock_audit_service():
    """Mock audit service para testing."""
    service = Mock(spec=DIAuditService)
    service.log_action = Mock()
    return service

@pytest.fixture
def override_dependencies(app, mock_audit_service):
    """Override FastAPI dependencies para tests."""
    app.dependency_overrides[get_audit_service] = lambda: mock_audit_service
    yield
    app.dependency_overrides.clear()

# tests/api/test_sessions.py
def test_create_session(client, override_dependencies, mock_audit_service):
    response = client.post("/api/sessions", json={...})
    assert response.status_code == 201
    mock_audit_service.log_action.assert_called_once()  # Verifica audit
```

**Archivos a crear:**
```
tests/
├── conftest.py                    # Fixtures globales
├── fixtures/
│   ├── services.py                # Mock services
│   ├── repositories.py            # Mock repositories
│   └── auth.py                    # Mock current_user
├── unit/
│   ├── services/                  # Service layer tests
│   └── mappers/                   # Mapper tests
└── integration/
    └── api/                       # API endpoint tests
```

**Criterios de éxito:**
- [ ] Coverage >70% en services/
- [ ] Todos los endpoints tienen test de success + failure
- [ ] Tests usan dependency_overrides (no mocks directos)

---

## 🦧 ANTROPOCENO (Era del Dev Experience) - ~8-10 horas

### Holoceno Temprano: P4-1 Developer Tooling (2-3 horas)
**Objetivo:** Scripts + automation para mantener arquitectura limpia

**Herramientas a crear:**
```bash
scripts/
├── check-imports.py          # Detecta imports ilegales (core/ → api/)
├── analyze-file-sizes.py     # Alerta si archivo >500 líneas
├── validate-di-usage.py      # Detecta get_container() usage
└── generate-dependency-graph.py  # Visualiza dependencias
```

**Ejemplo check-imports.py:**
```python
# Detecta violaciones de arquitectura limpia
ILLEGAL_PATTERNS = [
    ("backend/api", "backend/core"),      # API no debe importar core/
    ("backend/domain", "backend/api"),    # Domain no debe importar API
    ("backend/services", "backend/api"),  # Services no debe importar API
]

# Output:
# ❌ backend/api/routers/sessions.py:10 imports backend/core/llm_service.py
#    Solución: Usar Depends(get_llm_service) en lugar de import directo
```

**CI/CD integration:**
```yaml
# .github/workflows/architecture-lint.yml
- name: Check architecture boundaries
  run: python scripts/check-imports.py
- name: Check file sizes
  run: python scripts/analyze-file-sizes.py
```

---

### Holoceno Medio: P4-2 Documentation Update (3-4 horas)
**Objetivo:** Actualizar docs en `.claude/` para reflejar nueva arquitectura

**Docs a actualizar:**
```
.claude/
├── architecture/
│   ├── clean-architecture.md     # Actualizar con mappers, DI
│   ├── dependency-injection.md   # NEW: Patrón Depends()
│   └── service-layer.md          # NEW: Servicios extraídos
├── development/
│   ├── testing-guide.md          # NEW: DI testing patterns
│   └── refactor-checklist.md     # NEW: Checklist para nuevos endpoints
└── guides/
    └── backend-refactor.md       # NEW: Este plan geológico
```

**Ejemplo dependency-injection.md:**
```markdown
# Dependency Injection en Free Intelligence

## Patrón Factory + Depends()

### Service Factory (dependencies.py)
\`\`\`python
def get_session_service() -> SessionService:
    return SessionService(
        repository=get_session_repository(),
        audit_service=get_audit_service(),
    )
\`\`\`

### Endpoint Usage
\`\`\`python
@router.post("/sessions")
def create_session(
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.create(...)
\`\`\`

### Testing
\`\`\`python
def test_create_session(app, mock_session_service):
    app.dependency_overrides[get_session_service] = lambda: mock_session_service
\`\`\`
```

---

### Holoceno Tardío: P4-3 Performance Optimization (3-4 horas)
**Objetivo:** Optimizar DI overhead + circular imports

**Issues conocidos:**
1. **Circular imports** en algunos dependencies.py
2. **DI overhead** en endpoints de alta frecuencia
3. **N+1 queries** en algunos repositories

**Optimizaciones:**

**1. Lazy imports para circular dependencies:**
```python
# ANTES: Circular import
from backend.services.session import SessionService  # ImportError

# DESPUÉS: Lazy import con TYPE_CHECKING
if TYPE_CHECKING:
    from backend.services.session import SessionService

def get_session_service() -> "SessionService":
    from backend.services.session import SessionService  # Import here
    return SessionService(...)
```

**2. Singleton services con lru_cache:**
```python
from functools import lru_cache

@lru_cache(maxsize=1)  # Singleton
def get_audit_repository() -> AuditRepository:
    return AuditRepository(CORPUS_PATH)
```

**3. Batch loading en repositories:**
```python
# ANTES: N+1 queries
for session in sessions:
    soap = repository.get_soap(session.id)  # 1 query per session

# DESPUÉS: Batch loading
soaps = repository.get_soaps_batch([s.id for s in sessions])  # 1 query
```

**Criterios de éxito:**
- [ ] Zero circular import errors
- [ ] Audit repository es singleton (1 instancia)
- [ ] Batch endpoints usan batch loading

---

## 📊 Resumen del Plan

| Era | Fase | Tiempo | Prioridad | Bloqueadores |
|-----|------|--------|-----------|--------------|
| **Mesozoico** | P1-5 Mappers | 2-3h | 🔴 CRITICAL | P1-4 ✅ DONE |
| | P2-1 Services | 3-4h | 🔴 CRITICAL | P1-5 |
| | P2-2 DI Consolidation | 2-3h | 🟠 HIGH | P2-1 |
| **Cenozoico** | P3-1 Infrastructure | 4-5h | 🟠 HIGH | - |
| | P3-2 Domain Refinement | 3-4h | 🟡 MEDIUM | P2-1 |
| | P3-3 Testing | 5-6h | 🟡 MEDIUM | P2-2 |
| **Antropoceno** | P4-1 Tooling | 2-3h | 🟢 NICE | - |
| | P4-2 Docs | 3-4h | 🟢 NICE | All phases |
| | P4-3 Performance | 3-4h | 🟡 MEDIUM | P2-2 |

**Total estimado:** ~40 horas (1 semana full-time o 2 semanas part-time)

---

## 🎯 Next Immediate Actions

**Triásico - P1-5 Repository Mappers** (2-3 horas):
1. Crear `backend/mappers/soap_mapper.py` (30 min)
2. Extraer lógica de `hdf5_soap_repository.py` (30 min)
3. Repetir para Patient, Session, Order (1.5 horas)
4. Commit: `refactor(mappers): extract mappers from repositories (P1-5)`

**Comando para empezar:**
```bash
mkdir -p backend/mappers
touch backend/mappers/{soap_mapper,patient_mapper,session_mapper,order_mapper}.py
```

---

**Metáfora:** 4.6 mil millones de años de evolución → código limpio en 40 horas 🦕→🦧
