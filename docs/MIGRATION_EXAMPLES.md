# Code Migration Examples: Old → New Pattern

## Overview

This document provides before/after examples showing how to refactor existing code to use the new clean architecture patterns.

---

## Example 1: Simple Document Creation Endpoint

### Before (Monolithic)

```python
# ❌ OLD: backend/api/documents.py
from fastapi import APIRouter, UploadFile
import h5py
import json

router = APIRouter()

ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}

@router.post("/documents")
async def create_document(file: UploadFile):
    """Create document from uploaded file."""

    # Validation
    if not file.filename:
        return {"error": "filename required", "code": 400}

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {"error": f"unsupported format", "code": 400}

    content = await file.read()

    # Storage logic (mixed with endpoint)
    try:
        with h5py.File("storage/corpus.h5", "r+") as f:
            if "documents" not in f:
                f.create_group("documents")

            doc_group = f["documents"]
            doc_id = file.filename.replace(".", "_")

            if doc_id in doc_group:
                return {"error": "document exists", "code": 409}

            dataset = doc_group.create_dataset(
                doc_id,
                data=content,
            )
            dataset.attrs["filename"] = file.filename
            dataset.attrs["size"] = len(content)

    except Exception as e:
        return {"error": str(e), "code": 500}

    return {
        "status": "created",
        "id": doc_id,
        "size": len(content)
    }
```

**Problems**:
- 🔴 HDF5 logic in endpoint
- 🔴 No input validation (ValueError not caught)
- 🔴 Inconsistent error responses
- 🔴 Can't test without real file
- 🔴 Code duplication (HDF5 logic repeated)

### After (Clean Architecture)

```python
# ✅ NEW: backend/api/documents.py
from fastapi import APIRouter, UploadFile, HTTPException, status
from backend.container import get_container
from backend.schemas import success_response, error_response, StatusCode

router = APIRouter()

@router.post("/documents")
async def create_document(file: UploadFile):
    """Create document from uploaded file.

    Uses service layer for business logic.
    """
    try:
        # Get service (automatically wired with repository)
        service = get_container().get_corpus_service()

        # Validate file
        if not file.filename:
            raise ValueError("filename required")

        # Read content
        content = await file.read()

        # Call service (handles validation, storage, logging)
        result = service.create_document(
            document_id=file.filename,
            content=content.decode("utf-8"),
            source="upload"
        )

        return success_response(result)

    except ValueError as e:
        return error_response(
            str(e),
            code=400,
            status=StatusCode.VALIDATION_ERROR
        )
    except IOError as e:
        return error_response(
            "Failed to save document",
            code=500,
            status=StatusCode.INTERNAL_ERROR
        )
```

**Improvements**:
- ✅ Clean endpoint (just routing/HTTP concerns)
- ✅ Business logic in service
- ✅ Data access in repository
- ✅ Standardized responses
- ✅ Consistent error handling
- ✅ Easy to test (inject mock service)
- ✅ No code duplication

---

## Example 2: Session Management

### Before (Scattered Logic)

```python
# ❌ OLD: Multiple files with session logic
# api/sessions.py
with h5py.File("storage/sessions.h5") as f:
    sessions = f["active_sessions"]
    session_data = sessions[session_id]

# timeline_api.py
with h5py.File("storage/sessions.h5") as f:
    sessions = f["active_sessions"]
    if session_id in sessions:
        # ... 20 lines of repeated code

# audit_logs.py
with h5py.File("storage/sessions.h5") as f:
    sessions = f["active_sessions"]
    for session_id in sessions.keys():
        # ... more repeated code
```

**Problems**:
- 🔴 Session logic duplicated in 5+ files
- 🔴 No consistent error handling
- 🔴 No validation
- 🔴 Hard to maintain (fix one place, break another)

### After (Centralized Service)

```python
# ✅ NEW: backend/services/session_service.py
class SessionService:
    """Single source of truth for session operations."""

    def __init__(self, repository: SessionRepository):
        self.repository = repository

    def create_session(self, session_id: str, user_id: str):
        # Validation
        if not session_id or len(session_id) < 3:
            raise ValueError("Invalid session_id")

        # Creation
        session_id = self.repository.create(
            session_id=session_id,
            user_id=user_id
        )
        logger.info("SESSION_CREATED", session_id=session_id)
        return session_id

    def get_session(self, session_id: str):
        # Handles not found gracefully
        session = self.repository.read(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session

    def end_session(self, session_id: str):
        # Validation + deletion
        if not self.repository.delete(session_id):
            raise ValueError(f"Session {session_id} not found")
        logger.info("SESSION_ENDED", session_id=session_id)

# ✅ NEW: All endpoints use the service
# api/sessions.py
@app.post("/sessions")
def create_session(request: CreateSessionRequest):
    service = get_container().get_session_service()
    session_id = service.create_session(request.session_id, request.user_id)
    return success_response({"session_id": session_id})

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    service = get_container().get_session_service()
    session = service.get_session(session_id)
    return success_response(session)

@app.delete("/sessions/{session_id}")
def end_session(session_id: str):
    service = get_container().get_session_service()
    service.end_session(session_id)
    return success_response({"status": "ended"})
```

**Improvements**:
- ✅ Single implementation (one place to fix/update)
- ✅ Consistent validation
- ✅ Consistent error handling
- ✅ Testable (inject mock repository)
- ✅ Easy to add new features (just add method to service)

---

## Example 3: Error Handling Standardization

### Before (Inconsistent)

```python
# ❌ OLD: Different error handling in each endpoint

# api/documents.py
try:
    result = hdf5_operation()
except Exception as e:
    return {"error": str(e)}

# api/sessions.py
try:
    result = hdf5_operation()
except Exception as e:
    return {"status": "error", "message": str(e), "code": 500}

# api/audit.py
try:
    result = hdf5_operation()
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

# Result: Inconsistent API, hard to consume
```

### After (Standardized)

```python
# ✅ NEW: Standardized error handling via schemas

from backend.schemas import (
    success_response,
    error_response,
    validation_error_response,
    StatusCode
)

# All endpoints follow this pattern:
try:
    result = service.operation()
    return success_response(result)

except ValueError as e:
    logger.warning("VALIDATION_FAILED", error=str(e))
    return error_response(
        str(e),
        code=400,
        status=StatusCode.VALIDATION_ERROR
    )

except IOError as e:
    logger.error("STORAGE_FAILED", error=str(e))
    return error_response(
        "Operation failed",
        code=500,
        status=StatusCode.INTERNAL_ERROR
    )

except KeyError as e:
    logger.warning("NOT_FOUND", error=str(e))
    return error_response(
        f"Resource not found: {e}",
        code=404,
        status=StatusCode.NOT_FOUND
    )

# Result: Consistent API that's easy to consume
# All responses have: status, code, data, message, timestamp, request_id
```

---

## Example 4: Testing - Before vs After

### Before (Hard to Test)

```python
# ❌ OLD: Can't test without real HDF5 file
def test_create_document():
    # Needs real file system, slow, fragile
    response = create_document(file=UploadFile(...))
    assert response["status"] == "created"
    # Test creates actual files - cleanup needed
    # If test fails, leaves garbage behind
```

### After (Easy to Test)

```python
# ✅ NEW: Mock repository, fast, isolated tests
import unittest
from unittest.mock import Mock

class TestCorpusService(unittest.TestCase):
    def setUp(self):
        """Setup test fixtures."""
        self.mock_repo = Mock(spec=BaseRepository)
        self.service = CorpusService(self.mock_repo)

    def test_create_document_success(self):
        """Test successful document creation."""
        # Arrange
        self.mock_repo.create.return_value = "doc_123"

        # Act
        result = self.service.create_document(
            document_id="doc_123",
            content="Hello World"
        )

        # Assert
        assert result["status"] == "created"
        self.mock_repo.create.assert_called_once()

    def test_create_document_invalid_id(self):
        """Test validation of document_id."""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.service.create_document(
                document_id="",  # Invalid!
                content="Hello World"
            )

        # Verify repository was NOT called
        self.mock_repo.create.assert_not_called()

    def test_create_document_empty_content(self):
        """Test validation of content."""
        # Act & Assert
        with self.assertRaises(ValueError):
            self.service.create_document(
                document_id="doc_123",
                content=""  # Invalid!
            )

    def test_create_document_storage_error(self):
        """Test error handling."""
        # Arrange
        self.mock_repo.create.side_effect = IOError("Disk full")

        # Act & Assert
        with self.assertRaises(IOError):
            self.service.create_document(
                document_id="doc_123",
                content="Hello World"
            )

# Run: pytest tests/test_corpus_service.py
# Results: Fast (no I/O), isolated (no side effects), focused
```

---

## Example 5: Migrating Diarization Endpoint

### Before (Too Much Logic in Endpoint)

```python
# ❌ OLD: backend/api/diarization.py (250+ lines)
@router.post("/diarization/upload")
async def upload_audio(
    file: UploadFile,
    session_id: str = Header(...)
):
    # Validation (mixed with business logic)
    ext = file.filename.rsplit(".", 1)[-1]
    if ext not in ALLOWED_EXTENSIONS:
        return {"error": "invalid format"}

    # Storage (mixed with endpoint)
    audio_content = await file.read()
    with h5py.File("storage/audio.h5") as f:
        f.create_dataset(...)

    # Session management (mixed with endpoint)
    with h5py.File("storage/sessions.h5") as f:
        f["sessions"][session_id].attrs["audio_file"] = filename

    # Job queuing (mixed with endpoint)
    job_id = str(uuid4())
    with h5py.File("storage/jobs.h5") as f:
        f.create_dataset(...)

    # Logging (inconsistent)
    print(f"Job started: {job_id}")

    return {"job_id": job_id}
```

### After (Clean Separation)

```python
# ✅ NEW: backend/api/diarization.py (50 lines, focused)
from backend.container import get_container
from backend.schemas import success_response, error_response, StatusCode
import logging

logger = logging.getLogger(__name__)

@router.post("/diarization/upload")
async def upload_audio(
    file: UploadFile,
    session_id: str = Header(...),
    language: str = Query("es")
):
    """Upload audio file and start diarization.

    Services handle:
    - Session validation
    - File storage
    - Job creation
    - Audit logging
    """
    try:
        # Get services
        session_service = get_container().get_session_service()
        corpus_service = get_container().get_corpus_service()
        audit_service = get_container().get_audit_service()

        # Validate session exists
        session = session_service.get_session(session_id)

        # Save audio file
        audio_content = await file.read()
        doc_id = corpus_service.create_document(
            document_id=f"audio_{session_id}",
            content=audio_content.decode("utf-8", errors="ignore"),
            source="diarization_upload"
        )

        # Log the upload
        audit_service.log_action(
            action="audio_uploaded",
            user_id=session.get("user_id", "anonymous"),
            resource=f"audio:{doc_id}",
            result="success",
            details={"filename": file.filename}
        )

        return success_response({
            "document_id": doc_id,
            "session_id": session_id
        })

    except ValueError as e:
        return error_response(
            str(e),
            code=400,
            status=StatusCode.VALIDATION_ERROR
        )
    except IOError as e:
        logger.error("AUDIO_SAVE_FAILED", error=str(e))
        return error_response(
            "Failed to save audio",
            code=500,
            status=StatusCode.INTERNAL_ERROR
        )
```

**Improvements**:
- ✅ Endpoint focuses on HTTP/routing
- ✅ Business logic delegated to services
- ✅ Consistent error handling
- ✅ Audit trail automatically created
- ✅ Testable (can mock services)
- ✅ Much shorter and clearer

---

## Step-by-Step Migration Checklist

For each endpoint file, follow this process:

```
[ ] 1. Identify business logic (validation, transformations, decisions)
[ ] 2. Move business logic to service (create if needed)
[ ] 3. Identify data operations (HDF5 reads/writes)
[ ] 4. Verify repository handles data operations
[ ] 5. Update endpoint to:
      [ ] Inject service from get_container()
      [ ] Call service methods
      [ ] Return APIResponse via success_response()
      [ ] Handle errors with error_response()
[ ] 6. Add unit tests for service
[ ] 7. Test endpoint with mock service
[ ] 8. Verify no HDF5 code in endpoint
[ ] 9. Verify no business logic in endpoint
[ ] 10. Commit with clear message
```

---

## Common Pitfalls to Avoid

### ❌ Pitfall 1: Business Logic in Endpoint

```python
# WRONG: Validation in endpoint
@app.post("/documents")
def create_doc(req):
    if len(req.content) > 1000000:  # ❌ Business logic here
        raise ValueError("Too large")
    ...

# RIGHT: Validation in service
class DocumentService:
    def create_document(self, content):
        if len(content) > 1000000:  # ✅ Business logic here
            raise ValueError("Too large")
        return self.repository.create(...)
```

### ❌ Pitfall 2: Not Using Dependency Injection

```python
# WRONG: Creating dependency in constructor
class DocumentService:
    def __init__(self):
        self.repo = DocumentRepository()  # ❌ Can't mock

# RIGHT: Injecting dependency
class DocumentService:
    def __init__(self, repo: DocumentRepository):
        self.repo = repo  # ✅ Can inject mock for testing
```

### ❌ Pitfall 3: Inconsistent Error Handling

```python
# WRONG: Different patterns in each endpoint
try:
    result = service.operation()
    return {"success": True, "data": result}  # ❌ Custom format
except Exception as e:
    return {"error": str(e), "code": 500}  # ❌ Different format

# RIGHT: Consistent responses
try:
    result = service.operation()
    return success_response(result)  # ✅ Standardized
except ValueError as e:
    return error_response(str(e), code=400)  # ✅ Standardized
```

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Code Location** | Scattered | Organized (repositories/services) |
| **Logic Mixing** | API + Business + Data | Separated concerns |
| **Testing** | Difficult (real I/O) | Easy (mock services) |
| **Error Handling** | Inconsistent | Standardized |
| **Code Reuse** | Duplication | DRY |
| **Maintainability** | Hard (scattered logic) | Easy (single locations) |
| **Testability** | Low | High |
| **Flexibility** | Rigid | Flexible (easy to extend) |
