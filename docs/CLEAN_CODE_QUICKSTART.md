# Clean Code Quickstart Guide

**Duration**: 30 minutes
**Audience**: Developers working on Free Intelligence
**Goal**: Understand and use the clean code architecture

---

## What Changed?

Your app now has a **clean, layered architecture** instead of scattered logic:

```
Old Way (❌ Problems)         New Way (✅ Solutions)
─────────────────────        ──────────────────────
endpoints → HDF5             endpoints → services → repositories → HDF5
  ├─ API logic               services = business logic + validation
  ├─ Business logic          repositories = data access only
  ├─ Validation
  ├─ Data access
  └─ Error handling
```

---

## 3 Layers You Need to Know

### Layer 1: Repository (Data Access)
**Where**: `backend/repositories/`
**What**: Stores and retrieves data from HDF5
**Example**:
```python
from backend.repositories import CorpusRepository

repo = CorpusRepository("storage/corpus.h5")
doc = repo.read("doc_123")
repo.create("doc_123", "Hello World")
```

### Layer 2: Service (Business Logic)
**Where**: `backend/services/`
**What**: Validates inputs, implements business rules, uses repositories
**Example**:
```python
from backend.services import CorpusService
from backend.repositories import CorpusRepository

repo = CorpusRepository("storage/corpus.h5")
service = CorpusService(repo)
service.create_document("doc_123", "Hello World", source="upload")
```

### Layer 3: API Endpoint (HTTP)
**Where**: `backend/api/`
**What**: Accepts requests, calls services, returns responses
**Example**:
```python
from backend.container import get_container
from backend.schemas import success_response

@app.post("/documents")
def create_document(request):
    service = get_container().get_corpus_service()
    result = service.create_document(...)
    return success_response(result)
```

---

## Container: Dependency Management

Instead of creating services manually, use the container:

```python
from backend.container import get_container

# Get global container (auto-initializes on first call)
container = get_container()

# Get services (automatically wired with repositories)
corpus_service = container.get_corpus_service()
session_service = container.get_session_service()
audit_service = container.get_audit_service()
```

**Why?**
- ✅ Single place to manage all dependencies
- ✅ Easy to swap implementations (for testing)
- ✅ Avoids global state
- ✅ Services auto-wired correctly

---

## 5-Minute Feature: Add New Document Type

### Step 1: Create Service (if needed)
If it's a new feature that needs new business logic:

```python
# backend/services/custom_service.py
class CustomService:
    def __init__(self, repository):
        self.repository = repository

    def process_data(self, data):
        # Your business logic here
        return self.repository.create(...)
```

### Step 2: Add to Container
```python
# backend/container.py
def get_custom_service(self):
    repo = self.get_corpus_repository()  # reuse existing
    return CustomService(repo)
```

### Step 3: Create Endpoint
```python
# backend/api/custom.py
from backend.container import get_container
from backend.schemas import success_response

@app.post("/custom")
def process_custom(request):
    service = get_container().get_custom_service()
    result = service.process_data(request.data)
    return success_response(result)
```

Done! ✅

---

## Common Patterns

### Pattern 1: Validate Input

```python
# In service
def create_document(self, document_id: str, content: str):
    # Validate
    if not document_id or len(document_id) < 3:
        raise ValueError("ID must be >= 3 chars")

    if not content or len(content) == 0:
        raise ValueError("content required")

    # Use repository
    return self.repository.create(document_id, content)
```

### Pattern 2: Handle Errors in Endpoint

```python
# In endpoint
try:
    result = service.operation()
    return success_response(result)
except ValueError as e:
    return error_response(str(e), code=400)
except IOError as e:
    return error_response(str(e), code=500)
```

### Pattern 3: Log Important Actions

```python
# In service
logger.info("DOCUMENT_CREATED", document_id=doc_id)
```

### Pattern 4: List with Filtering

```python
# In service
docs = self.repository.list_all(limit=limit)
if source:
    docs = [d for d in docs if d["source"] == source]
return docs
```

---

## Testing: Before vs After

### Before (Hard)
```python
# ❌ Need real file system
def test_create():
    response = create_document(file=...)
    # Test creates real files
    # Slow, fragile, cleanup needed
```

### After (Easy)
```python
# ✅ Just mock the repository
from unittest.mock import Mock

def test_create():
    mock_repo = Mock()
    mock_repo.create.return_value = "doc_123"

    service = CorpusService(mock_repo)
    result = service.create_document(...)

    assert result["status"] == "created"
    mock_repo.create.assert_called_once()
```

---

## API Response Format

Every endpoint returns this structure:

```json
{
  "status": "success",
  "code": 200,
  "data": {...},
  "message": "Operation successful",
  "timestamp": "2025-11-01T12:00:00Z",
  "request_id": "req_123"
}
```

Use helper functions:

```python
# Success
return success_response({"id": "123"})

# Error
return error_response("Invalid input", code=400)

# Validation error
return validation_error_response([
    {"field": "email", "error": "invalid format"}
])
```

---

## Files & Locations

| What | Where |
|------|-------|
| Repository code | `backend/repositories/` |
| Service code | `backend/services/` |
| Container | `backend/container.py` |
| Response types | `backend/schemas.py` |
| Endpoint code | `backend/api/` |
| Tests | `tests/` |
| Docs | `docs/CLEAN_CODE_*.md` |

---

## When to Use Each Layer

### Use Repository When:
- You need to read/write HDF5 data
- You need persistence operations

### Use Service When:
- You need business logic
- You need validation
- You need to orchestrate multiple operations
- You need error handling
- You need logging

### Use Endpoint When:
- You need HTTP routing
- You need to parse requests
- You need to return responses

---

## Troubleshooting

### "Module not found"
```python
# Make sure __init__.py exports the class
# backend/repositories/__init__.py
from .corpus_repository import CorpusRepository
__all__ = ["CorpusRepository"]
```

### "Container not initializing"
```python
# Check HDF5 file path exists
from backend.container import get_container
try:
    container = get_container()
except IOError as e:
    print(f"Init failed: {e}")
```

### "Service not returning right type"
```python
# Check return type annotation matches
def create_document(...) -> str:
    return self.repository.create(...)
```

---

## SOLID Principles (Quick Reference)

**S**ingle Responsibility
→ Each class does ONE thing (Repository stores, Service validates)

**O**pen/Closed
→ Easy to add new repositories without modifying existing ones

**L**iskov Substitution
→ Any repository can replace BaseRepository

**I**nterface Segregation
→ Don't force classes to implement methods they don't need

**D**ependency Inversion
→ Depend on abstractions (BaseRepository), not concrete types

---

## Real Example: Create Session Endpoint

### Step 1: Service Already Exists ✅
```python
# backend/services/session_service.py
class SessionService:
    def create_session(self, session_id: str, user_id: str) -> str:
        return self.repository.create(session_id=session_id, user_id=user_id)
```

### Step 2: Endpoint Code
```python
# backend/api/sessions.py
from backend.container import get_container
from backend.schemas import success_response, error_response, StatusCode

@app.post("/sessions")
def create_session(request):
    try:
        # Get service from container
        service = get_container().get_session_service()

        # Call service
        session_id = service.create_session(
            session_id=request.session_id,
            user_id=request.user_id
        )

        # Return success
        return success_response({"session_id": session_id})

    except ValueError as e:
        return error_response(str(e), code=400)
    except IOError as e:
        return error_response("Storage error", code=500)
```

### Step 3: Test It
```python
# tests/test_sessions.py
from unittest.mock import Mock
from backend.services import SessionService

def test_create_session():
    # Setup
    mock_repo = Mock()
    mock_repo.create.return_value = "session_123"
    service = SessionService(mock_repo)

    # Execute
    result = service.create_session("session_123", "user_1")

    # Assert
    assert result == "session_123"
    mock_repo.create.assert_called_once()
```

Done! ✅

---

## Next: Read Full Docs

For more details:
- **CLEAN_CODE_REFACTORING.md** - Full architecture guide (15 min read)
- **MIGRATION_EXAMPLES.md** - Practical examples (10 min read)

---

## Summary

✅ Use **repositories** for data access
✅ Use **services** for business logic
✅ Use **container** for dependency management
✅ Use **standardized responses** for consistency
✅ Use **test mocks** for testing

You're ready to build! 🚀
