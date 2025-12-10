# Phase 5: Endpoint Migration - In Progress

## Overview

Phase 5 migrates existing API endpoints to use the clean code architecture (Repository + Service + DI Container patterns).

## Migration Strategy

### Priority 1: Core Business Logic Endpoints
These endpoints have significant business logic and benefit most from service layer:
- `api/diarization.py` - Audio processing + job management
- `api/corpus.py` - Document storage operations (if exists)
- `api/timeline.py` - Timeline operations

### Priority 2: CRUD Endpoints
These endpoints handle simple CRUD operations:
- `api/sessions.py` - Session management (already has SessionsStore abstraction)
- `api/audit.py` - Audit log queries (already abstracted in audit_logs module)
- `api/exports.py` - Export operations

### Priority 3: Supporting Endpoints
These endpoints support core business:
- `api/transcribe.py` - Transcription
- `api/triage.py` - Triage operations
- `api/verify.py` - Verification

---

## Migration Process

### Step 1: Identify What to Migrate
For each endpoint, identify:
1. **Data Access Logic** → Move to Repository
2. **Business Logic** → Move to Service
3. **Validation** → Keep in Service (some in endpoint for fast-fail)
4. **API Routing** → Keep in endpoint

### Step 2: Create/Update Service
```python
# backend/services/my_service.py
class MyService:
    def __init__(self, repository: BaseRepository):
        self.repository = repository

    def operation(self, ...):
        # Validation
        if not valid:
            raise ValueError("...")
        # Business logic
        # Call repository
        return result
```

### Step 3: Update Endpoint
```python
# backend/api/my_endpoint.py
from backend.container import get_container
from backend.schemas import success_response, error_response

@app.post("/operation")
def operation(request):
    try:
        service = get_container().get_my_service()
        result = service.operation(...)
        return success_response(result)
    except ValueError as e:
        return error_response(str(e), code=400)
    except IOError as e:
        return error_response(str(e), code=500)
```

### Step 4: Test
```python
# tests/test_my_service.py
def test_operation():
    mock_repo = Mock()
    service = MyService(mock_repo)
    result = service.operation(...)
    assert result == expected
```

---

## Current Status

### ✅ Completed (Infrastructure)
- Repository pattern (4 repositories + base class)
- Service layer (3 services + base patterns)
- DI Container (manages singletons)
- Standardized response schemas
- Documentation & guides

### 🟡 In Progress (Endpoint Migration)
- `api/audit.py` - Updated imports (ready for service integration)
- `api/sessions.py` - Updated imports (SessionsStore already follows patterns)
- `api/diarization.py` - Identified for migration (complex logic)

### ⏳ Pending (Full Service Integration)
- Diarization endpoint full migration
- All remaining endpoints
- Comprehensive testing

---

## Diarization.py Migration Example

### Before (Current - Mixed Concerns)

```python
# ❌ Current: api/diarization.py
@router.post("/upload")
async def upload_audio_for_diarization(
    audio: UploadFile,
    x_session_id: str = Header(...)
):
    # Validation (mixed with business logic)
    if not x_session_id:
        raise HTTPException(status_code=400, ...)

    # File handling (data access)
    ext = audio.filename.rsplit(".", 1)[-1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, ...)

    # Read file
    audio_content = await audio.read()
    if len(audio_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, ...)

    # Save audio (data access, not abstracted)
    saved = save_audio_file(...)

    # Create job (business logic mixed with data)
    if USE_LOWPRIO_WORKER:
        job_id = create_lowprio_job(...)
    else:
        job_id = create_job(...)

    # Background processing (business logic)
    background_tasks.add_task(...)

    # Inconsistent response
    return UploadResponse(...)
```

**Problems**:
- ❌ Validation mixed with business logic
- ❌ File storage not abstracted
- ❌ Job creation directly in endpoint
- ❌ Background task scheduling in endpoint
- ❌ Can't test without real files
- ❌ Inconsistent response format

### After (Proposed - Clean Separation)

```python
# ✅ Proposed: api/diarization.py (thin controller)
from backend.container import get_container
from backend.schemas import success_response, error_response, StatusCode

@router.post("/upload", status_code=202)
async def upload_audio_for_diarization(
    background_tasks: BackgroundTasks,
    audio: UploadFile,
    x_session_id: str = Header(...),
    language: str = Query("es")
):
    """Upload audio and start diarization job."""
    try:
        # Get services from container
        session_service = get_container().get_session_service()
        corpus_service = get_container().get_corpus_service()
        audit_service = get_container().get_audit_service()

        # Validate session exists (service handles validation)
        session = session_service.get_session(x_session_id)

        # Save audio file (service handles validation + storage)
        audio_content = await audio.read()
        doc_id = corpus_service.create_document(
            document_id=f"audio_{x_session_id}",
            content=audio_content.decode("utf-8", errors="ignore"),
            source="diarization_upload"
        )

        # Log the action (audit service)
        audit_service.log_action(
            action="audio_uploaded",
            user_id=session.get("user_id", "anonymous"),
            resource=f"audio:{doc_id}",
            result="success",
            details={"filename": audio.filename, "language": language}
        )

        # Schedule background job
        background_tasks.add_task(process_diarization, doc_id, language)

        # Consistent response
        return success_response(
            {
                "document_id": doc_id,
                "session_id": x_session_id,
                "status": "processing"
            },
            code=202
        )

    except ValueError as e:
        return error_response(str(e), code=400, status=StatusCode.VALIDATION_ERROR)
    except IOError as e:
        return error_response("Storage error", code=500, status=StatusCode.INTERNAL_ERROR)
```

**Improvements**:
- ✅ Endpoint focuses only on HTTP routing
- ✅ Validation in services
- ✅ Services handle data access
- ✅ Consistent error handling
- ✅ Consistent response format
- ✅ Easy to test (mock services)
- ✅ Audit trail automatically created

---

## Remaining Work

### To Complete Phase 5:

1. **Diarization Service** (create if needed)
   - Handle audio file validation
   - Coordinate job creation
   - Manage background processing

2. **Update Diarization Endpoint**
   - Use services from container
   - Return standardized responses
   - Consistent error handling

3. **Migrate Other Major Endpoints**
   - Identify business logic in each
   - Extract to services
   - Update endpoints to use services

4. **Testing**
   - Unit tests for new services
   - Integration tests for endpoints
   - Error case coverage

### Estimated Effort:
- Diarization migration: 2-3 hours
- Other major endpoints: 2 hours each
- Testing: 4-6 hours
- **Total: 12-16 hours**

---

## Next Steps

1. ✅ Infrastructure (DONE)
2. 🟡 Audit.py imports updated (started)
3. ⏳ Complete diarization migration
4. ⏳ Migrate remaining endpoints
5. ⏳ Comprehensive testing
6. ⏳ Commit with clear messages

---

## Success Criteria

- ✅ All major endpoints use services
- ✅ Standardized response format everywhere
- ✅ Consistent error handling
- ✅ 80%+ test coverage for services
- ✅ No business logic in endpoints
- ✅ No direct HDF5 calls in endpoints
