# Refactor Checklist - Free Intelligence Backend

**Última actualización:** 2026-02-02 (P4-2 Documentation Update)
**Propósito:** Guía rápida para mantener arquitectura limpia al agregar código nuevo

---

## ✅ Nuevo Endpoint API

### 1. Structure

- [ ] **Router placement:** `backend/api/routers/<domain>/<visibility>/<resource>.py`
  - visibility: `public/` (sin auth) o `internal/` (requiere auth)
  - Ejemplo: `api/routers/session/public/sessions.py`

- [ ] **Pydantic models:** Request + Response schemas en mismo archivo
  ```python
  class CreateSessionRequest(BaseModel):
      patient_id: str
      doctor_id: str

  class CreateSessionResponse(BaseModel):
      session_id: str
      status: str
  ```

### 2. Dependencies (NO Service Locator)

- [ ] **Import dependencies factory:**
  ```python
  from backend.domain.session.dependencies import get_session_service
  from backend.api.audit.dependencies import get_audit_service
  ```

- [ ] **Inject vía Depends():**
  ```python
  @router.post("/sessions")
  def create_session(
      data: CreateSessionRequest,
      session_service: SessionService = Depends(get_session_service),
      audit_service: DIAuditService = Depends(get_audit_service)
  ):
  ```

- [ ] **❌ NUNCA usar:**
  ```python
  # ❌ Service Locator anti-pattern
  container = get_container()
  service = container.session_service
  ```

### 3. Audit Logging

- [ ] **Success case:**
  ```python
  audit_service.log_action(
      action="<resource>_<operation>",  # e.g., "session_created"
      user_id=current_user.id,          # o doctor_id, "system"
      clinic_id=clinic_id,               # si aplica
      resource=resource_id,              # e.g., session_id
      result="success",
      details={...}                      # Metadata relevante
  )
  ```

- [ ] **Failure case (en except block):**
  ```python
  except Exception as e:
      audit_service.log_action(
          action="<resource>_<operation>_failed",
          user_id=user_id or "system",
          resource=resource_id or "unknown",
          result="failure",
          details={"error": str(e), **context}
      )
      raise HTTPException(...)
  ```

- [ ] **❌ NO usar logger.error():**
  - Audit logging reemplaza logging para eventos de negocio
  - logger solo para debugging técnico

### 4. Testing

- [ ] **Test success case:**
  ```python
  def test_create_session_success(app, client, mock_session_service):
      app.dependency_overrides[get_session_service] = lambda: mock_session_service
      response = client.post("/api/sessions", json={...})
      assert response.status_code == 201
  ```

- [ ] **Test failure case:**
  ```python
  def test_create_session_failure(app, client, mock_session_service):
      mock_session_service.create.side_effect = ValueError("Error")
      response = client.post("/api/sessions", json={...})
      assert response.status_code == 500
  ```

- [ ] **Verify audit logged:**
  ```python
  mock_audit_service.log_action.assert_called_once()
  ```

---

## ✅ Nuevo Service

### 1. Structure

- [ ] **Location:** `backend/services/<domain>/services/<service>.py`
  - Ejemplo: `services/session/services/session_service.py`

- [ ] **Dependencies via constructor:**
  ```python
  class SessionService:
      def __init__(
          self,
          repository: ISessionRepository,
          audit_service: IAuditService
      ):
          self.repository = repository
          self.audit_service = audit_service
  ```

### 2. Factory Function

- [ ] **Create factory en `domain/<domain>/dependencies.py`:**
  ```python
  def get_session_service(
      repository: ISessionRepository = Depends(get_session_repository),
      audit_service: IAuditService = Depends(get_audit_service)
  ) -> SessionService:
      return SessionService(
          repository=repository,
          audit_service=audit_service
      )
  ```

### 3. Business Logic

- [ ] **Validaciones de negocio en service, NO en API:**
  ```python
  # ✅ BIEN: Validación en service
  def create(self, patient_id: str):
      if self._has_active_session(patient_id):
          raise BusinessRuleViolation("Active session exists")
      ...

  # ❌ MAL: Validación en API
  @router.post("/sessions")
  def create_session(data):
      if has_active_session(data.patient_id):  # ❌ Business logic en API
          raise HTTPException(...)
  ```

### 4. Testing

- [ ] **Unit test con mock repository:**
  ```python
  def test_service_create(mock_repository):
      service = SessionService(repository=mock_repository)
      result = service.create(patient_id="123")
      mock_repository.save.assert_called_once()
  ```

---

## ✅ Nuevo Repository

### 1. Interface First

- [ ] **Define interface en `domain/interfaces/`:**
  ```python
  class ISessionRepository(ABC):
      @abstractmethod
      def save(self, session: Session) -> str:
          ...

      @abstractmethod
      def find_by_id(self, session_id: str) -> Session | None:
          ...
  ```

### 2. Implementation

- [ ] **Implementa interface en `repositories/`:**
  ```python
  class HDF5SessionRepository(ISessionRepository):
      def __init__(self, hdf5_path: Path):
          self.hdf5_path = hdf5_path

      def save(self, session: Session) -> str:
          metadata = SessionMapper.to_hdf5_metadata(session)
          # ... HDF5 I/O
          return session.session_id
  ```

### 3. Use Mapper

- [ ] **Delegate transformation to mapper:**
  ```python
  # ✅ Repository usa mapper
  metadata = SessionMapper.to_hdf5_metadata(session)
  self.hdf5_file.write(metadata)

  # ❌ Repository con mapping inline (acoplado)
  hdf5_data = {"session_id": session.session_id, ...}  # ❌
  ```

### 4. Factory

- [ ] **Create factory:**
  ```python
  def get_session_repository() -> ISessionRepository:
      return HDF5SessionRepository(hdf5_path=CORPUS_PATH)
  ```

---

## ✅ Nuevo Mapper

### 1. Structure

- [ ] **Location:** `backend/mappers/<entity>_mapper.py`
  - Ejemplo: `mappers/session_mapper.py`

- [ ] **Dataclasses for persistence:**
  ```python
  @dataclass
  class SessionHDF5Metadata:
      session_id: str
      status: str
      created_at: str
      ...
  ```

### 2. Bidirectional Conversion

- [ ] **to_hdf5/to_db (domain → persistence):**
  ```python
  @staticmethod
  def to_hdf5_metadata(session: Session) -> SessionHDF5Metadata:
      return SessionHDF5Metadata(
          session_id=session.session_id,
          status=session.status.value,
          ...
      )
  ```

- [ ] **from_hdf5/from_db (persistence → domain):**
  ```python
  @staticmethod
  def from_hdf5(session_id: str, metadata: SessionHDF5Metadata) -> Session:
      return Session(
          session_id=metadata.session_id,
          status=SessionStatus(metadata.status),
          ...
      )
  ```

### 3. Testing

- [ ] **Test to_hdf5:**
  ```python
  def test_to_hdf5():
      session = Session(...)
      metadata = SessionMapper.to_hdf5_metadata(session)
      assert metadata.session_id == session.session_id
  ```

- [ ] **Test from_hdf5:**
  ```python
  def test_from_hdf5():
      metadata = SessionHDF5Metadata(...)
      session = SessionMapper.from_hdf5("123", metadata)
      assert session.session_id == "123"
  ```

- [ ] **Test round-trip (CRITICAL):**
  ```python
  def test_round_trip():
      original = Session(...)
      metadata = SessionMapper.to_hdf5_metadata(original)
      reconstructed = SessionMapper.from_hdf5(original.session_id, metadata)
      assert reconstructed.session_id == original.session_id
      # ... verify all fields
  ```

---

## ✅ Pre-Commit Checks

### Auto-validation

```bash
# 1. Check architecture boundaries
python backend/scripts/check-imports.py

# 2. Validate DI usage (no get_container)
python backend/scripts/validate-di-usage.py

# 3. Check file sizes
python backend/scripts/analyze-file-sizes.py

# 4. Run tests
pytest backend/tests/
```

### Manual Review

- [ ] **No emojis en código** (usar lucide-react icons)
- [ ] **No secrets en código** (.env, credentials.json)
- [ ] **Español mexicano en comments/docstrings**
- [ ] **Type hints en todas las funciones**
- [ ] **Docstrings en funciones públicas**

---

## 🚨 Red Flags

### ❌ Immediate Fix Needed

| Code | Problem | Solution |
|------|---------|----------|
| `get_container()` | Service Locator | Use `Depends(get_service)` |
| `from backend.core import` | Legacy import | Migrate to `services/` |
| `logger.error()` in endpoint | Missing audit | Add `audit_service.log_action()` |
| Mapper logic in repository | Coupling | Extract to `mappers/` |
| 500+ lines in file | Too complex | Split into smaller modules |
| No tests for endpoint | Quality risk | Add integration test |

---

## 📊 Quality Gates

### Before PR

- [ ] **Architecture:** 0 violations (`check-imports.py`)
- [ ] **DI:** 0 service locator usage (`validate-di-usage.py`)
- [ ] **Tests:** All new code has tests
- [ ] **Coverage:** No decrease in overall coverage
- [ ] **Docs:** Update if architecture changed

### CI/CD Gates

- [ ] Tests pass
- [ ] Linting passes (ruff, pyright)
- [ ] Architecture validation passes
- [ ] No sensitive data committed

---

## 📚 Quick Reference

**Documentation:**
- Clean Architecture: `.claude/architecture/clean-architecture.md`
- Dependency Injection: `.claude/architecture/dependency-injection.md`
- Testing Guide: `.claude/development/testing-guide.md`
- Plan Geológico: `.claude/guides/backend-refactor-geological-plan.md`

**Tools:**
- check-imports.py
- validate-di-usage.py
- analyze-file-sizes.py
- generate-dependency-graph.py

**Examples:**
- Mapper tests: `backend/tests/unit/mappers/test_soap_mapper.py`
- API tests: `backend/tests/integration/api/test_audit_integration.py`
- Service: `backend/services/session/services/session_service.py`
