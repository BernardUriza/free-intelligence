# Workflow Service Architecture

**Clean Architecture + SOLID + Dependency Injection**

This service implements intelligent workflow orchestration for medical session processing (diarization, SOAP generation, emotion analysis, encryption).

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    HTTP Layer (Controllers)                      │
│  backend/api/routers/session/public/sessions_pkg/workflows.py   │
│                                                                   │
│  • Thin controllers (10-15 lines of code)                        │
│  • FastAPI Depends() for service injection                       │
│  • Error handling (404, 400, 500)                                │
│  • NO business logic                                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Dependency Providers (DI)                       │
│         backend/services/workflow/dependencies.py                │
│                                                                   │
│  • get_workflow_orchestrator() → IWorkflowOrchestrator           │
│  • get_workflow_router() → IWorkflowRouter                       │
│  • get_workflow_tracker() → IWorkflowTracker                     │
│  • get_intelligent_orchestration_service() → IIntelligent...     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Service Layer (Business Logic)                │
│         backend/services/workflow/services/                      │
│                                                                   │
│  • IntelligentOrchestrationService (main orchestrator)           │
│  • WorkflowOrchestrator (task dispatch)                          │
│  • WorkflowRouter (routing decisions)                            │
│  • WorkflowTracker (state tracking)                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Interface Layer (Contracts)                   │
│         backend/services/workflow/interfaces/                    │
│                                                                   │
│  • IWorkflowOrchestrator (task dispatch abstraction)             │
│  • IWorkflowRouter (routing abstraction)                         │
│  • IWorkflowTracker (state tracking abstraction)                 │
│  • IIntelligentOrchestrationService (orchestration abstraction)  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer (Storage)                  │
│         backend/repositories/, backend/infrastructure/           │
│                                                                   │
│  • ITaskRepository (task CRUD operations)                        │
│  • ICorpusRepository (audio/session data)                        │
│  • ILogger (structured logging)                                  │
│  • Workers (ThreadPoolExecutor task execution)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Design Principles

### 1. Clean Architecture

**Layering:**
- **Controllers (HTTP):** Thin, no business logic
- **Services (Business Logic):** Orchestration, routing, state tracking
- **Interfaces (Contracts):** Abstract dependencies
- **Infrastructure (Storage):** Repositories, workers, storage

**Dependency Rule:**
- Inner layers (services) do NOT depend on outer layers (controllers)
- Outer layers depend on inner layers via interfaces
- Example: `IntelligentOrchestrationService` depends on `IWorkflowOrchestrator` (interface), NOT `WorkflowOrchestrator` (concrete class)

### 2. SOLID Principles

✅ **Single Responsibility:**
- `IntelligentOrchestrationService` → Orchestrate workflows
- `WorkflowRouter` → Decide which workflows to execute
- `WorkflowTracker` → Track workflow state

✅ **Open/Closed:**
- Add new workflows without changing controllers (add to router logic)

✅ **Liskov Substitution:**
- Any `IWorkflowOrchestrator` implementation can replace `WorkflowOrchestrator`

✅ **Interface Segregation:**
- Small, focused interfaces (IWorkflowRouter only has `route_workflows()`)

✅ **Dependency Inversion:**
- Services depend on `ILogger`, NOT `get_logger()` (abstraction > concrete)

### 3. Dependency Injection

**Before (Service Locator Anti-Pattern):**
```python
@router.post("/analyze")
def analyze(session_id: str) -> dict:
    from backend.services.workflow.api.public.services import get_workflow_orchestrator
    orchestrator = get_workflow_orchestrator()  # ❌ Service locator
    return orchestrator.dispatch(...)
```

**After (Dependency Injection via FastAPI):**
```python
@router.post("/analyze")
def analyze(
    session_id: str,
    orchestrator: WorkflowOrchestratorDep,  # ✅ Dependency injection
) -> dict:
    return await orchestrator.dispatch(...)
```

**Benefits:**
- Type-safe (Pyright validates dependencies)
- Testable (mock services via `app.dependency_overrides`)
- Clear dependency graph (visible in function signatures)

---

## 🚀 Usage Examples

### 1. Adding a New Workflow

**Step 1:** Define workflow in `constants.py`:
```python
WORKFLOW_MY_NEW_FEATURE = "my_new_feature"
```

**Step 2:** Add dispatch method to `IWorkflowOrchestrator`:
```python
@abstractmethod
async def dispatch_my_new_feature(
    self,
    session_id: str,
    language: str = "es",
) -> dict[str, Any]:
    """Dispatch my new feature workflow."""
    ...
```

**Step 3:** Implement in `WorkflowOrchestrator`:
```python
async def dispatch_my_new_feature(
    self,
    session_id: str,
    language: str = "es",
) -> dict[str, Any]:
    # Dispatch worker
    spawn_worker(my_new_feature_worker, session_id=session_id)
    return {"task_id": session_id, "status": "dispatched"}
```

**Step 4:** Add routing logic in `WorkflowRouter`:
```python
def _rule_based_routing(...):
    workflows = []

    # Add your routing logic
    if some_condition:
        workflows.append(WORKFLOW_MY_NEW_FEATURE)

    return {"workflows": workflows, ...}
```

**Step 5:** Add endpoint in `workflows.py` (optional):
```python
@router.post("/sessions/{session_id}/my-feature")
async def dispatch_my_feature(
    session_id: str,
    orchestrator: WorkflowOrchestratorDep,
) -> dict:
    return await orchestrator.dispatch_my_new_feature(session_id)
```

### 2. Testing with Mocked Services

**Unit Test (Service Layer):**
```python
@pytest.fixture
def mock_orchestrator():
    orchestrator = MagicMock()
    orchestrator.dispatch_diarization = AsyncMock(
        return_value={"task_id": "test-123", "status": "dispatched"}
    )
    return orchestrator

@pytest.fixture
def service(mock_orchestrator, mock_router, mock_tracker, ...):
    return IntelligentOrchestrationService(
        orchestrator=mock_orchestrator,
        router=mock_router,
        tracker=mock_tracker,
        ...
    )

@pytest.mark.asyncio
async def test_orchestrate_success(service):
    result = await service.orchestrate_intelligent_workflow(...)
    assert result["status"] == "dispatched"
```

**Integration Test (HTTP Layer):**
```python
@pytest.fixture
def client(mock_orchestration_service):
    app.dependency_overrides[get_intelligent_orchestration_service] = (
        lambda: mock_orchestration_service
    )
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_analyze_endpoint_success(client):
    response = client.post("/api/sessions/test-123/analyze")
    assert response.status_code == 202
    assert response.json()["status"] == "dispatched"
```

---

## 📊 Service Comparison

| Feature | Before (Service Locator) | After (Dependency Injection) |
|---------|-------------------------|------------------------------|
| **Dependency Resolution** | Runtime (global singletons) | Compile-time (type hints) |
| **Testability** | Hard (must mock global state) | Easy (app.dependency_overrides) |
| **Type Safety** | ❌ No (service locator returns Any) | ✅ Yes (Annotated types) |
| **Circular Imports** | ⚠️ Common | ✅ Rare (interfaces break cycles) |
| **Clear Dependencies** | ❌ Hidden (inside function) | ✅ Visible (in signature) |
| **SOLID Compliance** | ❌ Violates DIP | ✅ Follows DIP |

---

## 📁 File Structure

```
backend/services/workflow/
├── README.md                  # This file
├── constants.py               # Magic numbers → constants
│
├── interfaces/                # Abstract contracts (DIP)
│   ├── __init__.py
│   ├── iworkflow_orchestrator.py
│   ├── iworkflow_router.py
│   ├── iworkflow_tracker.py
│   └── iintelligent_orchestration.py
│
├── services/                  # Business logic implementations
│   ├── intelligent_orchestration_service.py  # Main orchestrator
│   ├── workflow_orchestrator.py              # Task dispatch
│   ├── workflow_router.py                    # Routing decisions
│   └── workflow_tracker.py                   # State tracking
│
├── dependencies.py            # FastAPI dependency providers
│
└── tests/                     # Unit + integration tests
    ├── test_intelligent_orchestration_service.py
    └── test_workflows_endpoints.py (in api/routers/session/tests/)
```

---

## 🧪 Testing Strategy

### Unit Tests (`test_intelligent_orchestration_service.py`)

**Focus:** Business logic in isolation

**Pattern:**
- Mock ALL dependencies (orchestrator, router, tracker, repositories)
- Test service methods directly
- Verify correct calls to dependencies
- Test error handling (FileNotFoundError, ValueError)

**Example:**
```python
def test_audio_duration_fallback(service, mock_corpus_repo):
    """Test fallback when audio detection fails."""
    mock_corpus_repo.get_session_audio.side_effect = FileNotFoundError()

    result = await service.orchestrate_intelligent_workflow(...)

    assert result["audio_duration_seconds"] == DEFAULT_AUDIO_DURATION_SECONDS
```

### Integration Tests (`test_workflows_endpoints.py`)

**Focus:** HTTP layer with mocked services

**Pattern:**
- Use FastAPI TestClient (real HTTP requests)
- Mock services via `app.dependency_overrides`
- Test HTTP status codes (202, 404, 400, 500)
- Verify response structure

**Example:**
```python
def test_analyze_endpoint_success(client, mock_service):
    response = client.post("/api/sessions/test-123/analyze")

    assert response.status_code == 202
    assert response.json()["status"] == "dispatched"
    mock_service.orchestrate_intelligent_workflow.assert_called_once()
```

---

## 🔧 Troubleshooting

### Error: "Circular import detected"

**Cause:** Import cycle between modules

**Fix:** Use TYPE_CHECKING guard for type-only imports:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.workflow.services.workflow_orchestrator import WorkflowOrchestrator

def my_function(orchestrator: "WorkflowOrchestrator") -> None:
    ...
```

### Error: "No attribute 'dispatch_diarization'"

**Cause:** Mock not configured correctly

**Fix:** Use AsyncMock for async methods:
```python
orchestrator.dispatch_diarization = AsyncMock(return_value={...})
```

### Error: "Dependency override not working"

**Cause:** Override not cleared after test

**Fix:** Always clear overrides in fixture teardown:
```python
@pytest.fixture
def client():
    app.dependency_overrides[...] = ...
    yield TestClient(app)
    app.dependency_overrides.clear()  # ← Critical!
```

---

## 📚 References

- **Clean Architecture:** https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- **SOLID Principles:** https://en.wikipedia.org/wiki/SOLID
- **FastAPI Dependency Injection:** https://fastapi.tiangolo.com/tutorial/dependencies/
- **Dependency Inversion Principle:** https://en.wikipedia.org/wiki/Dependency_inversion_principle

---

## 📝 Migration History

| PR | Date | Changes | Impact |
|----|------|---------|--------|
| **PR #1** | 2026-01-31 | Interfaces + Service Implementations | +993 lines, architecture foundation |
| **PR #2** | 2026-01-31 | Dependency Providers + Endpoint Refactor | -175 lines, service locator eliminated |
| **PR #3** | 2026-01-31 | Tests + Documentation | +535 lines, validation + docs |

**Total:** +1,353 lines net, **Architecture Grade: C+ → A** ✅

---

**Questions?** See `.claude/rules/architecture/` for more details.
