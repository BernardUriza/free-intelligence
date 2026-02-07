# Clean Architecture - Free Intelligence Backend

**Última actualización:** 2026-02-02 (P4-2 Documentation Update)
**Patrón:** Hexagonal Architecture + Domain-Driven Design

---

## 🎯 Principios SOLID

### 1. Single Responsibility Principle (SRP)
- **Repository:** Solo persistencia (I/O)
- **Mapper:** Solo transformación (domain ↔ persistence)
- **Service:** Solo lógica de negocio
- **Controller (API):** Solo HTTP handling

### 2. Open/Closed Principle (OCP)
- Nuevos providers (Twilio, SendGrid) sin modificar `NotificationService`
- Nuevos repositories (HDF5, PostgreSQL) sin modificar domain

### 3. Liskov Substitution Principle (LSP)
- Todos los repositories implementan interfaces (ISessionRepository, etc.)
- Mock repositories intercambiables en tests

### 4. Interface Segregation Principle (ISP)
- Interfaces específicas por dominio (ISOAPRepository ≠ ISessionRepository)
- No interfaces monolíticas

### 5. Dependency Inversion Principle (DIP)
- Services dependen de interfaces, no implementaciones
- Dependency Injection vía FastAPI Depends()

---

## 🏗️ Estructura de Capas

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (HTTP)                     │
│  FastAPI routers, request/response models, auth         │
│  Dependencies: ↓ Services (vía Depends())               │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                      │
│  Services: Business logic, use cases, orchestration     │
│  Dependencies: ↓ Repositories (vía interfaces)          │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                   Domain Layer                          │
│  Entities, Value Objects, Domain Services, Interfaces   │
│  Dependencies: NONE (pure business logic)               │
└─────────────────────────────────────────────────────────┘
                           ↑
┌─────────────────────────────────────────────────────────┐
│              Infrastructure Layer                       │
│  Repositories, Mappers, External Services (DB, APIs)    │
│  Dependencies: ↑ Domain (implementa interfaces)         │
└─────────────────────────────────────────────────────────┘
```

**Regla clave:** Dependencies apuntan HACIA ADENTRO (hacia domain).

---

## 📁 Organización del Código

### Backend Root Structure

```
backend/
├── api/                    # API Layer (HTTP)
│   ├── routers/           # FastAPI routers por dominio
│   ├── dependencies.py    # Global dependencies (current_user, etc.)
│   └── audit/             # Audit logging
│
├── domain/                 # Domain Layer (core business)
│   ├── session/
│   │   ├── __init__.py    # Exports: Session, SessionStatus, ISessionRepository
│   │   ├── dependencies.py # Factory: get_session_service()
│   │   └── services/      # Domain services (optional)
│   ├── soap/
│   ├── patient/
│   ├── order/
│   └── interfaces/        # Repository interfaces (ABCs)
│
├── services/               # Application Layer (use cases)
│   ├── session/
│   │   └── services/
│   │       └── session_service.py  # Business logic
│   ├── workflow/
│   ├── llm/
│   └── ...
│
├── repositories/           # Infrastructure (persistence)
│   ├── hdf5_session_repository.py
│   ├── postgres_patient_repository.py
│   └── interfaces/        # Legacy (migrar a domain/interfaces/)
│
├── mappers/                # Data transformation (NEW P1-5)
│   ├── soap_mapper.py     # SOAPNote ↔ HDF5
│   ├── patient_mapper.py  # Patient ↔ PostgreSQL
│   ├── session_mapper.py
│   └── order_mapper.py
│
└── infrastructure/         # External concerns
    ├── auth/              # Auth0, JWT
    ├── workers/           # Background tasks
    ├── observability/     # Logging, metrics
    └── common/            # Shared utilities
```

---

## 🔄 Data Flow

### Request → Response (Read)

```
1. HTTP Request
   ↓
2. API Router (FastAPI)
   ↓ Depends(get_session_service)
3. SessionService.get(session_id)
   ↓ calls repository.find_by_id()
4. SessionRepository.find_by_id()
   ↓ reads HDF5
5. SessionMapper.from_hdf5()
   ↓ converts to domain entity
6. Session entity
   ↓ returns through layers
7. HTTP Response (Pydantic serialization)
```

### Request → Persistence (Write)

```
1. HTTP Request (POST)
   ↓
2. API Router validates Pydantic model
   ↓ Depends(get_session_service)
3. SessionService.create(data)
   ↓ creates Session entity
4. SessionRepository.save(session)
   ↓ calls mapper
5. SessionMapper.to_hdf5(session)
   ↓ converts to persistence format
6. Repository writes to HDF5
   ↓
7. HTTP Response (201 Created)
```

---

## 🗺️ Mappers Pattern (P1-5)

### Responsabilidad

**Antes (coupled):**
```python
class SessionRepository:
    def save(self, session):
        # ❌ Repository + mapping mixed
        hdf5_data = {
            "session_id": session.session_id,
            "status": session.status.value,
            ...
        }
        self.hdf5_file.write(hdf5_data)
```

**Después (separated):**
```python
class SessionRepository:
    def save(self, session):
        # ✅ Repository delegates to mapper
        metadata = SessionMapper.to_hdf5_metadata(session)
        self.hdf5_file.write(metadata)

class SessionMapper:
    @staticmethod
    def to_hdf5_metadata(session: Session) -> SessionHDF5Metadata:
        """Pure transformation: Session → HDF5."""
        return SessionHDF5Metadata(
            session_id=session.session_id,
            status=session.status.value,
            ...
        )
```

**Beneficios:**
- ✅ **SRP:** Repository = I/O, Mapper = transformation
- ✅ **Testeable:** Mapper tests son unit tests puros
- ✅ **Reusable:** 1 mapper para múltiples repos (HDF5, SQL)

### 4 Mappers Implementados

1. **SOAPMapper:** SOAPNote ↔ (SOAPHDF5Metadata, SOAPHDF5Content)
2. **PatientMapper:** Patient ↔ DBPatient (identity mapper)
3. **SessionMapper:** Session ↔ SessionHDF5Metadata
4. **OrderMapper:** Order ↔ OrderHDF5Metadata

Ver: `backend/mappers/` + tests en `backend/tests/unit/mappers/`

---

## 🎨 Service Layer Pattern

### Responsabilidades

**Service Layer:**
- ✅ Business logic (validaciones, cálculos)
- ✅ Orchestration (coordinar múltiples repositories)
- ✅ Transactions (atomicidad de operaciones)
- ❌ NO HTTP concerns (eso es API layer)
- ❌ NO persistence details (eso es repository)

**Ejemplo: SessionService**

```python
class SessionService:
    """Session management business logic."""

    def __init__(
        self,
        repository: ISessionRepository,
        audit_service: IAuditService
    ):
        self.repository = repository
        self.audit_service = audit_service

    def create(self, patient_id: str, doctor_id: str) -> str:
        """Create new session with business rules validation.

        Business rules:
        - Patient must exist
        - Doctor must be active
        - Max 1 active session per patient
        """
        # Validation (business logic)
        if self._has_active_session(patient_id):
            raise BusinessRuleViolation("Patient already has active session")

        # Create entity
        session = Session.create_now(
            session_id=str(uuid4()),
            patient_id=patient_id,
            doctor_id=doctor_id
        )

        # Persist
        session_id = self.repository.save(session)

        # Audit (cross-cutting concern)
        self.audit_service.log_action(
            action="session_created",
            user_id=doctor_id,
            resource=session_id,
            result="success"
        )

        return session_id
```

---

## 🔌 Dependency Injection

### Pattern: Factory + Depends()

**backend/domain/session/dependencies.py:**
```python
def get_session_repository() -> ISessionRepository:
    """Factory: Crea repository implementation."""
    return HDF5SessionRepository(hdf5_path=CORPUS_PATH)

def get_session_service(
    repository: ISessionRepository = Depends(get_session_repository)
) -> SessionService:
    """Factory: Crea service con dependencies inyectadas."""
    return SessionService(repository=repository)
```

**backend/api/routers/session/router.py:**
```python
@router.post("/sessions")
def create_session(
    data: CreateSessionRequest,
    session_service: SessionService = Depends(get_session_service)
):
    """Endpoint: session_service auto-injected."""
    return session_service.create(
        patient_id=data.patient_id,
        doctor_id=data.doctor_id
    )
```

Ver: `.claude/architecture/dependency-injection.md`

---

## 🧱 Domain Layer Design

### Domain Entities

**Características:**
- Pure Python (no framework dependencies)
- Business rules enforcement
- Immutability preferred (dataclasses with frozen=True)

**Ejemplo: Session**
```python
@dataclass
class Session:
    session_id: str
    status: SessionStatus
    created_at: str
    updated_at: str

    def finalize(self, encryption_metadata: EncryptionMetadata) -> None:
        """Business rule: Only ACTIVE sessions can be finalized."""
        if self.status != SessionStatus.ACTIVE:
            raise InvalidStateTransition(
                f"Cannot finalize session in {self.status} state"
            )

        self.status = SessionStatus.FINALIZED
        self.finalized_at = datetime.now(UTC).isoformat()
```

### Repository Interfaces (ABCs)

**backend/domain/interfaces/isession_repository.py:**
```python
from abc import ABC, abstractmethod

class ISessionRepository(ABC):
    """Session persistence interface (storage-agnostic)."""

    @abstractmethod
    def save(self, session: Session) -> str:
        """Persist session entity."""
        ...

    @abstractmethod
    def find_by_id(self, session_id: str) -> Session | None:
        """Find session by ID."""
        ...
```

**Beneficio:** Domain no conoce HDF5 ni PostgreSQL, solo la interfaz.

---

## 🚫 Architecture Violations

### Validación Automática

```bash
# Detecta imports ilegales (domain→api, services→api, etc.)
python backend/scripts/check-imports.py --fix-suggestions

# Detecta service locator (get_container)
python backend/scripts/validate-di-usage.py
```

### Reglas Enforced

| Violation | Tool | Status |
|-----------|------|--------|
| API imports core/ | check-imports.py | 0 violations ✅ |
| Domain imports API | check-imports.py | 7 violations ⚠️ |
| Services imports API | check-imports.py | 5 violations ⚠️ |
| Service Locator usage | validate-di-usage.py | 0 violations ✅ |

---

## 📊 Architecture Metrics

**Estado actual (2026-02-02):**

| Métrica | Valor | Target | Status |
|---------|-------|--------|--------|
| Layers separados | 4 | 4 | ✅ |
| Services extraídos | 17 | 15 | ✅ |
| Mappers implementados | 4/4 | 4 | ✅ |
| DI adoption (API) | 100% | 100% | ✅ |
| Architecture violations | 7 | 0 | ⚠️ |
| Max file size (infra) | 689 | 300 | ⚠️ |

**Próximos pasos:**
1. Fix 7 architecture violations (domain→api imports)
2. Modularizar container.py (689 líneas → deprecar)
3. Aumentar test coverage (40% → 70%)

---

## 📚 Referencias

- **Clean Architecture:** Robert C. Martin (2017)
- **Hexagonal Architecture:** Alistair Cockburn
- **DDD:** Eric Evans - Domain-Driven Design
- **Plan Geológico:** `.claude/guides/backend-refactor-geological-plan.md`
- **DI Guide:** `.claude/architecture/dependency-injection.md`
- **Testing Guide:** `.claude/development/testing-guide.md`
