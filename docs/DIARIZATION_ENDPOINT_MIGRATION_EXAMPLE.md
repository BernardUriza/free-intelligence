# Diarization Endpoint Migration Example

## Overview

This document shows how to migrate a complex endpoint (`api/diarization.py`) to use the clean code architecture with services.

## Before: Current Implementation (Mixed Concerns)

```python
# ❌ CURRENT: backend/api/diarization.py
@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_audio_for_diarization(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    language: str = Query("es"),
    persist: bool = Query(False),
):
    """Upload audio file and start diarization job."""

    # ❌ PROBLEM 1: Validation mixed with business logic
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Session-ID header required"
        )

    # ❌ PROBLEM 2: File handling not abstracted
    ext: str = audio.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format"
        )

    audio_content = await audio.read()
    file_size = len(audio_content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large"
        )

    # ❌ PROBLEM 3: Direct HDF5 operations
    try:
        saved = save_audio_file(
            session_id=x_session_id,
            audio_content=audio_content,
            file_extension=ext,
            metadata={"filename": audio.filename}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # ❌ PROBLEM 4: Job creation scattered
    if USE_LOWPRIO_WORKER:
        job_id = create_lowprio_job(...)
    else:
        job_id = create_job(...)

    # ❌ PROBLEM 5: Inconsistent response format
    return UploadResponse(
        job_id=job_id,
        session_id=x_session_id,
        status="processing",
        message="Job started"
    )
```

**Issues**:
- ❌ No separation of concerns
- ❌ Validation mixed with logic
- ❌ Can't test without real files
- ❌ Inconsistent error handling
- ❌ Inconsistent response format
- ❌ Hard to reuse logic
- ❌ Difficult to modify

## After: Migrated Implementation (Clean Architecture)

```python
# ✅ MIGRATED: backend/api/diarization.py (thin controller)
from fastapi import APIRouter, BackgroundTasks, File, Header, Query, status
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel

from backend.container import get_container
from backend.schemas import success_response, error_response, StatusCode

router = APIRouter(prefix="/api/diarization")

class UploadResponse(BaseModel):
    """Upload response."""
    job_id: str
    session_id: str
    status: str
    message: str

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_audio_for_diarization(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(..., description="Audio file to diarize"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    language: str = Query("es", description="Language code"),
    persist: bool = Query(False, description="Save results to disk"),
):
    """
    Upload audio file and start diarization job.

    Uses clean code architecture:
    - DiarizationService handles validation and job creation
    - CorpusService handles file storage
    - SessionService validates session exists
    - AuditService logs the action
    """
    try:
        # Get services from DI container
        diarization_service = get_container().get_diarization_service()
        session_service = get_container().get_session_service()
        audit_service = get_container().get_audit_service()

        # Read audio file
        audio_content = await audio.read()

        # ✅ SERVICE LAYER: Validation + File Storage
        # The service handles:
        # - Filename validation
        # - Extension validation
        # - File size validation
        # - Session validation
        # - Audio file storage via CorpusService
        job_metadata = diarization_service.create_diarization_job(
            session_id=x_session_id,
            audio_filename=audio.filename,
            audio_content=audio_content,
            language=language,
            persist=persist
        )

        job_id = job_metadata["job_id"]

        # ✅ AUDIT: Log the upload
        audit_service.log_action(
            action="audio_uploaded",
            user_id="system",  # or get from session
            resource=f"audio:{job_id}",
            result="success",
            details={
                "filename": audio.filename,
                "language": language,
                "session_id": x_session_id
            }
        )

        # ✅ BACKGROUND PROCESSING: Delegate to worker
        # In production, this would queue to a message broker
        background_tasks.add_task(
            process_diarization,
            job_id=job_id,
            session_id=x_session_id,
            language=language
        )

        # ✅ STANDARDIZED RESPONSE
        return success_response(
            {
                "job_id": job_id,
                "session_id": x_session_id,
                "status": "processing"
            },
            message="Diarization job started",
            code=202
        )

    except ValueError as e:
        # ✅ CONSISTENT ERROR HANDLING
        logger.warning("DIARIZATION_VALIDATION_FAILED", error=str(e))
        return error_response(
            str(e),
            code=400,
            status=StatusCode.VALIDATION_ERROR
        )

    except IOError as e:
        # ✅ CONSISTENT ERROR HANDLING
        logger.error("DIARIZATION_STORAGE_FAILED", error=str(e))
        return error_response(
            "Failed to save audio file",
            code=500,
            status=StatusCode.INTERNAL_ERROR
        )

    except Exception as e:
        # ✅ CONSISTENT ERROR HANDLING
        logger.error("DIARIZATION_UPLOAD_FAILED", error=str(e))
        return error_response(
            "Internal server error",
            code=500,
            status=StatusCode.INTERNAL_ERROR
        )
```

## What Changed

### 1. Removed Concerns from Endpoint
```python
# ❌ Before: In endpoint
ext = audio.filename.rsplit(".", 1)[-1]
if ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(...)

# ✅ After: In service
service.validate_audio_file(filename, size)  # Returns (is_valid, error)
```

### 2. Abstracted File Storage
```python
# ❌ Before: Direct I/O in endpoint
saved = save_audio_file(...)

# ✅ After: Through service + repository
job_metadata = service.create_diarization_job(...)  # Handles storage
```

### 3. Standardized Responses
```python
# ❌ Before: Custom response
return UploadResponse(...)

# ✅ After: Standardized wrapper
return success_response({...})
return error_response("...", code=400)
```

### 4. Consistent Error Handling
```python
# ❌ Before: Inconsistent patterns
except Exception as e:
    raise HTTPException(...)  # Mixed styles

# ✅ After: Consistent pattern
except ValueError as e:
    return error_response(str(e), code=400)
except IOError as e:
    return error_response(..., code=500)
```

### 5. Added Audit Trail
```python
# ✅ New: Automatic audit logging
audit_service.log_action(
    action="audio_uploaded",
    user_id=user_id,
    resource=f"audio:{job_id}",
    result="success",
    details={...}
)
```

## Service Implementation

The `DiarizationService` handles all the moved logic:

```python
# backend/services/diarization_service.py
class DiarizationService:
    """Diarization operations service."""

    def create_diarization_job(
        self,
        session_id: str,
        audio_filename: str,
        audio_content: bytes,
        language: str = "es",
        persist: bool = False
    ) -> dict[str, Any]:
        """Create diarization job.

        Handles:
        - Filename validation (extension check)
        - File size validation
        - Session validation
        - Audio file storage (via CorpusService)
        - Job metadata creation
        """
        # ✅ Validation
        is_valid, error = self.validate_audio_file(audio_filename, len(audio_content))
        if not is_valid:
            raise ValueError(error)

        is_valid, error = self.validate_session(session_id)
        if not is_valid:
            raise ValueError(error)

        # ✅ Storage via CorpusService
        doc_id = self.corpus_service.create_document(
            document_id=f"audio_{job_id}",
            content=audio_content.decode("utf-8", errors="ignore"),
            source="diarization_upload"
        )

        # ✅ Job metadata
        job_metadata = {
            "job_id": str(uuid4()),
            "session_id": session_id,
            "document_id": doc_id,
            "status": "pending",
            "language": language,
            # ... more fields
        }

        return job_metadata
```

## Testing

### Before: Hard to Test
```python
# ❌ Hard to test - needs real files
def test_upload():
    response = upload_audio_for_diarization(file=real_file, ...)
    # Need actual files, cleanup, etc.
```

### After: Easy to Test
```python
# ✅ Easy to test - mock service
def test_upload():
    mock_service = Mock(spec=DiarizationService)
    mock_service.create_diarization_job.return_value = {
        "job_id": "test_123",
        "session_id": "session_123"
    }

    # Call endpoint with mock
    response = upload_audio_for_diarization(...)

    # Verify
    assert response.job_id == "test_123"
    mock_service.create_diarization_job.assert_called_once()
```

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Testability** | Hard (needs files) | Easy (mock services) |
| **Reusability** | No (logic in endpoint) | Yes (logic in service) |
| **Consistency** | Inconsistent | Standardized |
| **Maintainability** | Hard (scattered logic) | Easy (clear locations) |
| **Error Handling** | Mixed | Consistent |
| **Audit Trail** | Manual | Automatic |
| **Type Safety** | Partial | Full |
| **Documentation** | Minimal | Comprehensive |

## Migration Checklist

- [ ] Create DiarizationService class
- [ ] Move validation logic to service
- [ ] Move file storage to repository pattern
- [ ] Update endpoint to use service
- [ ] Add audit logging
- [ ] Standardize response format
- [ ] Add error handling
- [ ] Write tests for service
- [ ] Test endpoint with mocks
- [ ] Update endpoint documentation
- [ ] Commit with clear message

## Next Steps

1. Apply this pattern to other endpoints
2. Create tests for all services
3. Document the pattern in contributing guide
4. Update existing endpoint implementations
5. Measure improvements (test coverage, error consistency)
