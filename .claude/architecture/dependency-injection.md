# Dependency Injection en Free Intelligence

**Última actualización:** 2026-02-02 (P4-2 Documentation Update)
**Patrón implementado:** FastAPI Depends() + Factory Functions

---

## 🎯 Principios

### Service Locator ❌ → Dependency Injection ✅

```python
# ❌ ANTI-PATTERN: Service Locator (deprecado)
def create_session():
    container = get_container()  # Tight coupling
    session_service = container.session_service
    return session_service.create(...)

# ✅ PATRÓN CORRECTO: Dependency Injection
def create_session(
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.create(...)  # Loose coupling
```

**Beneficios:**
- ✅ **Testeable:** Mock dependencies vía `app.dependency_overrides`
- ✅ **Type-safe:** IDE autocomplete + type checking
- ✅ **Explicit:** Dependencies declaradas en signature
- ✅ **Loose coupling:** Service no conoce cómo se construye

---

## 📁 Estructura de Dependencies

### Patrón por Dominio

```
backend/domain/<domain>/
├── dependencies.py         # ← Factory functions
├── services/
│   └── <domain>_service.py
└── interfaces/
    └── i<domain>_repository.py
```

### Ejemplo: Session Domain

**backend/domain/session/dependencies.py:**
```python
from backend.domain.session.services.session_service import SessionService
from backend.repositories.hdf5_session_repository import HDF5SessionRepository
from backend.config import CORPUS_PATH

def get_session_repository() -> HDF5SessionRepository:
    """Factory: Crea instancia de SessionRepository.

    Singleton pattern via functools.lru_cache si es necesario.
    """
    return HDF5SessionRepository(hdf5_path=CORPUS_PATH)

def get_session_service(
    repository: HDF5SessionRepository = Depends(get_session_repository)
) -> SessionService:
    """Factory: Crea SessionService con dependencies inyectadas.

    Note: El repository se inyecta automáticamente vía Depends().
    """
    return SessionService(repository=repository)
```

**backend/api/routers/session/router.py:**
```python
from fastapi import APIRouter, Depends
from backend.domain.session.services.session_service import SessionService
from backend.domain.session.dependencies import get_session_service

router = APIRouter()

@router.post("/sessions")
def create_session(
    data: CreateSessionRequest,
    session_service: SessionService = Depends(get_session_service)
):
    """Endpoint con DI: session_service inyectado automáticamente."""
    session = session_service.create(
        patient_id=data.patient_id,
        doctor_id=data.doctor_id
    )
    return {"session_id": session.session_id}
```

---

## 🔗 Dependency Chain

FastAPI resuelve dependencies recursivamente:

```
Endpoint
  ↓ Depends(get_session_service)
SessionService
  ↓ Depends(get_session_repository)
SessionRepository
  ↓ Depends(get_audit_service)
AuditService
  ↓ Depends(get_audit_repository)
AuditRepository
```

**Ventaja:** Solo declares el dependency de más alto nivel, FastAPI resuelve el resto.

---

## 🧪 Testing con DI

### Pattern: dependency_overrides

**backend/tests/integration/api/test_sessions.py:**
```python
def test_create_session(app, client, mock_session_service):
    """Test endpoint con mock service."""
    from backend.domain.session.dependencies import get_session_service

    # Override dependency
    app.dependency_overrides[get_session_service] = lambda: mock_session_service

    # Configure mock
    mock_session_service.create.return_value = Session(
        session_id="test_123",
        status=SessionStatus.ACTIVE,
        created_at="2026-02-02T10:00:00Z",
        updated_at="2026-02-02T10:00:00Z"
    )

    # Test
    response = client.post("/api/sessions", json={
        "patient_id": "patient_123",
        "doctor_id": "doctor_456"
    })

    assert response.status_code == 201
    assert response.json()["session_id"] == "test_123"
    mock_session_service.create.assert_called_once()

    # Cleanup automático via fixture
```

**Fixtures reusables:** Ver `backend/tests/fixtures/`
- `services.py` - Mock services
- `repositories.py` - Mock repositories
- `auth.py` - Mock current_user

---

## 🎨 Patterns Comunes

### 1. Service con Multiple Dependencies

```python
def get_workflow_orchestrator(
    session_service: SessionService = Depends(get_session_service),
    audit_service: DIAuditService = Depends(get_audit_service),
    task_repository: ITaskRepository = Depends(get_task_repository)
) -> WorkflowOrchestrator:
    """Orchestrator con 3 dependencies."""
    return WorkflowOrchestrator(
        session_service=session_service,
        audit_service=audit_service,
        task_repository=task_repository
    )
```

### 2. Singleton via lru_cache

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_audit_repository() -> AuditRepository:
    """Singleton: Una sola instancia para toda la app."""
    return AuditRepository(CORPUS_PATH)
```

**Cuándo usar:**
- Repositories que abren archivos (HDF5)
- Conexiones a DB (SQLAlchemy sessions)
- Caches in-memory

### 3. Request-scoped Dependencies

```python
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Dependency per-request: Nuevo user por cada request."""
    payload = verify_token(token)
    return User.from_token(payload)
```

**Cuándo usar:**
- Auth (current_user diferente por request)
- Request context (request_id, correlation_id)

### 4. Lazy Imports (Circular Dependencies)

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.llm import LLMService

def get_llm_service() -> "LLMService":
    """Lazy import evita circular dependency."""
    from backend.services.llm import LLMService
    return LLMService(...)
```

---

## 🚫 Anti-Patterns

### ❌ Import Directo de Service

```python
# ❌ MAL: Import directo
from backend.services.session import SessionService

def my_endpoint():
    service = SessionService()  # Hard-coded dependency
    ...
```

**Problema:** No testeable, tight coupling.

### ❌ get_container() en Endpoints

```python
# ❌ MAL: Service locator
from backend.infrastructure.common.container import get_container

def my_endpoint():
    container = get_container()
    service = container.session_service  # Service locator anti-pattern
    ...
```

**Problema:** Viola DIP, no testeable.

**Fix:** Usar `Depends(get_session_service)`

### ❌ Global Instances

```python
# ❌ MAL: Global mutable state
session_service = SessionService()  # Module-level global

def my_endpoint():
    return session_service.create(...)
```

**Problema:** No testeable, thread-unsafe, singleton forzado.

---

## 🛠️ Migration Checklist

### De Service Locator → DI

1. **Identificar uso de get_container():**
   ```bash
   python backend/scripts/validate-di-usage.py
   ```

2. **Crear factory function en dependencies.py:**
   ```python
   def get_<service>() -> <Service>:
       return <Service>(...)
   ```

3. **Actualizar endpoint signature:**
   ```python
   def endpoint(
       service: Service = Depends(get_service)
   ):
       ...
   ```

4. **Eliminar get_container() call:**
   ```diff
   - container = get_container()
   - service = container.some_service
   + # service inyectado vía Depends()
   ```

5. **Verificar tests:**
   ```python
   app.dependency_overrides[get_service] = lambda: mock_service
   ```

---

## 📊 Estado Actual (2026-02-02)

**Progreso DI Migration:**
- ✅ Service Locator eliminado de API layer (0 ocurrencias)
- ✅ 17 dominios con dependencies.py
- ✅ Testing fixtures con dependency_overrides
- ⚠️ 7 violaciones arquitectura (domain→api imports)

**Herramientas:**
- `validate-di-usage.py` - Detecta get_container()
- `check-imports.py` - Valida arquitectura
- Ver: `backend/scripts/README.md`

---

## 📚 Referencias

- **FastAPI Dependency Injection:** https://fastapi.tiangolo.com/tutorial/dependencies/
- **Martin Fowler - Inversion of Control:** https://martinfowler.com/articles/injection.html
- **Plan Geológico:** `.claude/guides/backend-refactor-geological-plan.md`
- **Testing Guide:** `.claude/development/testing-guide.md`
