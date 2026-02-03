# Testing Guide - Free Intelligence Backend

**Última actualización:** 2026-02-02 (P4-2 Documentation + P3-3 Testing Infrastructure)
**Framework:** pytest + FastAPI TestClient + unittest.mock

---

## 🎯 Testing Philosophy

### Pirámide de Testing

```
     /\
    /  \   E2E (pocos, críticos)
   /────\
  / Unit \  Integration (endpoints con mocks)
 /────────\
/ Unit Tests \ (muchos, rápidos)
──────────────
```

**Distribución objetivo:**
- 70% Unit tests (services, mappers, domain logic)
- 25% Integration tests (API endpoints con dependency_overrides)
- 5% E2E tests (flujos completos usuario)

---

## 📁 Estructura de Tests

```
backend/tests/
├── conftest.py                 # Fixtures globales
├── fixtures/
│   ├── services.py            # Mock services
│   ├── repositories.py        # Mock repositories
│   └── auth.py                # Mock current_user
├── unit/
│   ├── mappers/               # Mapper tests (bidirectional)
│   ├── services/              # Service layer tests
│   └── domain/                # Domain model tests
└── integration/
    └── api/                   # API endpoint tests
```

---

## 🧪 Unit Testing

### Pattern: Mapper Tests

**Test bidireccional:** domain ↔ persistence

**backend/tests/unit/mappers/test_soap_mapper.py:**
```python
from backend.mappers.soap_mapper import SOAPMapper, SOAPHDF5Metadata, SOAPHDF5Content
from backend.domain.soap.models import SOAPNote, SubjectiveData, ObjectiveData

class TestSOAPMapperToHDF5:
    """Test domain → HDF5 conversion."""

    def test_to_hdf5_converts_correctly(self):
        # Arrange: Create domain entity
        soap = SOAPNote(
            subjective=SubjectiveData(
                chief_complaint="Dolor de cabeza",
                history_present_illness="Desde hace 3 días",
                past_medical_history="Ninguna"
            ),
            objective=ObjectiveData(
                vital_signs="BP: 120/80",
                physical_exam="Normal"
            ),
            # ... assessment, plan
        )
        soap.soap_id = "soap_123"
        soap.session_id = "session_456"

        # Act: Convert to HDF5
        metadata, content = SOAPMapper.to_hdf5(soap)

        # Assert: Verify structure
        assert isinstance(metadata, SOAPHDF5Metadata)
        assert metadata.soap_id == "soap_123"
        assert content.subjective["chief_complaint"] == "Dolor de cabeza"

    def test_from_hdf5_converts_correctly(self):
        # Arrange: Create HDF5 structures
        metadata = SOAPHDF5Metadata(
            soap_id="soap_123",
            session_id="session_456",
            created_at="2026-02-02T10:00:00Z"
        )
        content = SOAPHDF5Content(
            subjective={"chief_complaint": "Test", ...},
            # ... other sections
        )

        # Act: Convert to domain
        soap = SOAPMapper.from_hdf5("soap_123", metadata, content)

        # Assert: Verify entity
        assert isinstance(soap, SOAPNote)
        assert soap.soap_id == "soap_123"

    def test_round_trip_preserves_data(self):
        """Critical: domain → HDF5 → domain should preserve all fields."""
        original = SOAPNote(...)  # Full entity
        metadata, content = SOAPMapper.to_hdf5(original)
        reconstructed = SOAPMapper.from_hdf5(original.soap_id, metadata, content)

        assert reconstructed.soap_id == original.soap_id
        assert reconstructed.subjective.chief_complaint == original.subjective.chief_complaint
        # ... verify all fields
```

### Pattern: Service Tests

**Test con mock repository:**

```python
def test_session_service_create(mock_session_repository):
    """Test SessionService.create() con mock repository."""
    # Arrange
    mock_session_repository.save.return_value = "session_123"

    service = SessionService(repository=mock_session_repository)

    # Act
    session_id = service.create(
        patient_id="patient_456",
        doctor_id="doctor_789"
    )

    # Assert
    assert session_id == "session_123"
    mock_session_repository.save.assert_called_once()

    # Verify call arguments
    call_args = mock_session_repository.save.call_args
    session_arg = call_args[0][0]  # First positional arg
    assert session_arg.patient_id == "patient_456"
    assert session_arg.status == SessionStatus.ACTIVE
```

---

## 🌐 Integration Testing

### Pattern: API Endpoint con DI Override

**backend/tests/integration/api/test_sessions.py:**
```python
def test_create_session_success(app, client, mock_session_service, mock_audit_service):
    """Test POST /api/sessions con mocks."""
    from backend.domain.session.dependencies import get_session_service
    from backend.api.audit.dependencies import get_audit_service

    # Arrange: Override dependencies
    app.dependency_overrides[get_session_service] = lambda: mock_session_service
    app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

    # Configure mock responses
    mock_session_service.create.return_value = Session(
        session_id="test_123",
        status=SessionStatus.ACTIVE,
        created_at="2026-02-02T10:00:00Z",
        updated_at="2026-02-02T10:00:00Z"
    )

    # Act: Make HTTP request
    response = client.post("/api/sessions", json={
        "patient_id": "patient_123",
        "doctor_id": "doctor_456"
    })

    # Assert: HTTP response
    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == "test_123"

    # Assert: Service interactions
    mock_session_service.create.assert_called_once_with(
        patient_id="patient_123",
        doctor_id="doctor_456"
    )

    # Assert: Audit logged
    mock_audit_service.log_action.assert_called_once()
    audit_call = mock_audit_service.log_action.call_args
    assert audit_call.kwargs["action"] == "session_created"
    assert audit_call.kwargs["result"] == "success"

    # Cleanup: Automatic via conftest.py fixture
```

### Pattern: Error Handling

```python
def test_create_session_failure(app, client, mock_session_service, mock_audit_service):
    """Test error handling + failure audit logging."""
    from backend.domain.session.dependencies import get_session_service
    from backend.api.audit.dependencies import get_audit_service

    app.dependency_overrides[get_session_service] = lambda: mock_session_service
    app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

    # Configure mock to raise error
    mock_session_service.create.side_effect = ValueError("Patient not found")

    # Act
    response = client.post("/api/sessions", json={
        "patient_id": "invalid",
        "doctor_id": "doctor_456"
    })

    # Assert: HTTP error
    assert response.status_code == 500

    # Assert: Failure audit logged
    assert mock_audit_service.log_action.called
    audit_call = mock_audit_service.log_action.call_args
    assert audit_call.kwargs["result"] == "failure"
    assert "Patient not found" in str(audit_call.kwargs["details"])
```

---

## 🎭 Mock Fixtures

### Fixtures Disponibles

**backend/tests/fixtures/services.py:**
- `mock_audit_service` - DIAuditService mock
- `mock_session_service` - SessionService mock
- `mock_llm_client` - LLM client mock
- `mock_task_repository` - ITaskRepository mock
- `mock_export_service` - ExportService mock
- `mock_notification_service` - NotificationService mock

**backend/tests/fixtures/repositories.py:**
- `mock_session_repository` - ISessionRepository mock
- `mock_soap_repository` - ISOAPRepository mock
- `mock_patient_repository` - IPatientRepository mock
- `mock_order_repository` - IOrderRepository mock

**backend/tests/fixtures/auth.py:**
- `mock_current_user` - Default test user
- `mock_admin_user` - Admin role
- `mock_doctor_user` - Doctor role
- `mock_patient_user` - Patient role (limited permissions)

### Uso de Fixtures

```python
def test_with_multiple_mocks(
    app,
    client,
    mock_audit_service,
    mock_session_service,
    mock_current_user
):
    """Fixtures automáticamente inyectados por pytest."""
    from backend.domain.session.dependencies import get_session_service
    from backend.api.audit.dependencies import get_audit_service
    from backend.api.dependencies import get_current_user

    # Override all dependencies
    app.dependency_overrides[get_session_service] = lambda: mock_session_service
    app.dependency_overrides[get_audit_service] = lambda: mock_audit_service
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    # ... test logic
```

---

## 🔧 Test Utilities

### Factories

**backend/tests/conftest.py** incluye factories:

```python
def test_with_session_data(session_factory):
    """Factory fixture crea datos de test."""
    session_data = session_factory(
        session_id="custom_123",
        status="active"
    )
    assert session_data["session_id"] == "custom_123"
```

### Fixtures Disponibles:
- `session_factory` - Genera session dicts
- `audit_entry_factory` - Genera audit log entries
- `temp_h5_file` - HDF5 temporal (auto-cleanup)

---

## 🏃 Running Tests

### Comandos Comunes

```bash
# Run all tests
pytest

# Run specific file
pytest backend/tests/unit/mappers/test_soap_mapper.py

# Run with coverage
pytest --cov=backend --cov-report=html

# Run only unit tests
pytest backend/tests/unit/

# Run only integration tests
pytest backend/tests/integration/

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_create"

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

### Coverage Target

```bash
pytest --cov=backend --cov-report=term-missing

# Target: >70% overall
# Critical: 100% mappers, 80% services
```

---

## ✅ Testing Checklist

### Para Nuevo Endpoint

- [ ] **Success case:** Happy path retorna 2XX
- [ ] **Failure case:** Error retorna 4XX/5XX
- [ ] **Audit logging:** Success + failure logged
- [ ] **Auth:** current_user correctamente usado
- [ ] **Validation:** Pydantic models validados
- [ ] **Mocks:** dependency_overrides correctos
- [ ] **Cleanup:** app.dependency_overrides.clear() automático

### Para Nuevo Service

- [ ] **Unit test:** Lógica de negocio aislada
- [ ] **Mock repository:** No I/O real
- [ ] **Error handling:** Exceptions manejadas
- [ ] **Edge cases:** None, empty lists, etc.

### Para Nuevo Mapper

- [ ] **to_hdf5/to_db:** Domain → Persistence
- [ ] **from_hdf5/from_db:** Persistence → Domain
- [ ] **Round-trip:** Preserva todos los campos
- [ ] **Error cases:** Missing fields, invalid data

---

## 🚨 Common Pitfalls

### ❌ Fixture sin cleanup

```python
# ❌ MAL: Overrides se quedan entre tests
def test_one(app, mock_service):
    app.dependency_overrides[get_service] = lambda: mock_service
    # No cleanup!

def test_two(app):
    # Hereda override del test_one! 🐛
```

**Fix:** Usar `override_dependencies` fixture:
```python
def test_one(app, override_dependencies, mock_service):
    app.dependency_overrides[get_service] = lambda: mock_service
    # Cleanup automático vía fixture
```

### ❌ Mock sin spec

```python
# ❌ MAL: Typos no detectados
mock_service = Mock()
mock_service.creat()  # Typo: debería ser create()

# ✅ BIEN: Mock con spec
mock_service = Mock(spec=SessionService)
mock_service.creat()  # ❌ AttributeError: spec no tiene 'creat'
```

### ❌ No verificar mock calls

```python
# ❌ MAL: Test pasa pero servicio nunca llamado
def test_create(mock_service):
    response = client.post("/api/sessions", json={...})
    assert response.status_code == 201
    # ⚠️  No verifica que mock_service.create fue llamado!

# ✅ BIEN: Verifica interacciones
def test_create(mock_service):
    response = client.post("/api/sessions", json={...})
    assert response.status_code == 201
    mock_service.create.assert_called_once()  # ✅
```

---

## 📊 Coverage Report

**Estado actual (2026-02-02):**

| Módulo | Coverage | Target | Status |
|--------|----------|--------|--------|
| mappers/ | 100% | 100% | ✅ |
| services/ | ~40% | 80% | ⚠️ |
| api/ | ~30% | 70% | ⚠️ |
| domain/ | ~60% | 80% | ⚠️ |

**Prioridad:** Aumentar coverage de services/ y api/

---

## 📚 Referencias

- **pytest Docs:** https://docs.pytest.org/
- **FastAPI Testing:** https://fastapi.tiangolo.com/tutorial/testing/
- **Dependency Injection:** `.claude/architecture/dependency-injection.md`
- **Mock fixtures:** `backend/tests/fixtures/`
- **Example tests:** `backend/tests/unit/mappers/test_soap_mapper.py`
