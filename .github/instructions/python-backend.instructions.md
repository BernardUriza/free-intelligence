---
applyTo: "backend/**/*.py"
---

# Python Backend Instructions - AURITY

## Python Version
**Python 3.14 ONLY** - This is a hard requirement.

### Modern Syntax Requirements
```python
from __future__ import annotations  # REQUIRED in every file

# Use modern union types
def process(data: str | None) -> dict[str, Any]:  # ✅
    # NOT: Optional[str], Dict[str, Any]  # ❌

# Use match/case for state machines
match state:
    case "READY":
        return process_ready()
    case "ERROR":
        return handle_error()
```

## Type Safety

### Always Include Type Hints
```python
# Function signatures
async def create_session(
    session_id: str,
    user_id: str,
    metadata: dict[str, Any] | None = None
) -> SessionResponse:
    ...

# Variables when ambiguous
events: list[dict[str, Any]] = []
updates: dict[str, Any] = {}
```

### Pydantic Models
```python
from pydantic import BaseModel, Field

class SessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    user_id: str
    metadata: dict[str, Any] | None = None
```

## FastAPI Patterns

### Dependency Injection
```python
from fastapi import Depends, HTTPException, status
from backend.auth.jwt import get_current_user

@router.post("/api/workflows/aurity/sessions")
async def create_session(
    request: SessionRequest,
    user: User = Depends(get_current_user)  # Automatic auth
):
    logger.info("session_created", session_id=request.session_id, user_id=user.id)
    return {"session_id": request.session_id}
```

### Async I/O (Critical)
```python
# ✅ CORRECT - non-blocking
async def process_file(file: UploadFile):
    content = await file.read()
    result = await some_async_operation(content)
    return result

# ❌ WRONG - blocks event loop
async def process_file(file: UploadFile):
    content = file.file.read()  # Blocking I/O
    return content
```

## Event Sourcing - HDF5

### CRITICAL: Append-Only Pattern
```python
import h5py
from datetime import UTC, datetime

# ✅ CORRECT - Append with versioning
def save_data(session_id: str, data: bytes):
    timestamp = datetime.now(UTC).isoformat()
    path = f"/sessions/{session_id}/tasks/TASK_TYPE/versions/{timestamp}"

    with h5py.File(CORPUS_PATH, "a") as f:
        f.create_dataset(path, data=data)
        f.attrs[f"latest_{session_id}"] = timestamp

# ❌ FORBIDDEN - Deletes audit trail
def save_data(session_id: str, data: bytes):
    path = f"/sessions/{session_id}/tasks/TASK_TYPE/result"

    with h5py.File(CORPUS_PATH, "r+") as f:
        if path in f:
            del f[path]  # VIOLATION - destroys history
        f.create_dataset(path, data=data)
```

### Atomic Writes
```python
import os
import hashlib

def save_session_atomic(session_id: str, data: dict):
    final_path = f"storage/sessions/{session_id}.h5"
    temp_path = f"{final_path}.part"

    try:
        # Write to temporary file
        with h5py.File(temp_path, "w") as f:
            f.create_dataset("data", data=audio_data)
            f.attrs["created_at"] = datetime.now(UTC).isoformat()
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic rename (POSIX guarantee)
        os.rename(temp_path, final_path)

        # Calculate integrity checksum
        with open(final_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        logger.info("session_saved", session_id=session_id, checksum=checksum)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
```

## Security - HIPAA Compliance

### NO PHI/PII in Logs
```python
import structlog

logger = structlog.get_logger(__name__)

# ✅ CORRECT - Only IDs
logger.info("patient_created", patient_id=patient.patient_id)
logger.info("user_authenticated", user_id=user.id)

# ❌ FORBIDDEN - Exposes PHI
logger.info("patient_created", nombre=patient.nombre)  # PHI
logger.error("auth_failed", email=email)  # PII
```

### Environment Variables Only
```python
import os

# ✅ CORRECT
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY not set")

# ❌ FORBIDDEN
DEEPGRAM_API_KEY = "sk-abc123..."  # Hardcoded secret
```

## Error Handling

### Structured Exceptions
```python
from fastapi import HTTPException, status

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    try:
        session = await session_service.get(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        return session

    except ValueError as e:
        logger.error("invalid_session_id", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )

    except Exception as e:
        logger.error("session_fetch_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

## Testing

### Pytest Patterns
```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    return TestClient(app)

async def test_create_session(client):
    response = client.post(
        "/api/workflows/aurity/sessions",
        json={"session_id": "test-123", "user_id": "user-456"}
    )
    assert response.status_code == 200
    assert response.json()["session_id"] == "test-123"
```

## Architecture Rules

### Three-Layer Separation
```python
# ✅ PUBLIC LAYER - backend/api/public/workflows/aurity_*.py
@router.post("/api/workflows/aurity/sessions")  # Exposed to clients
async def create_session(...):
    # Orchestration logic
    return await internal_service.create_session(...)

# ✅ INTERNAL LAYER - backend/api/internal/*
@router.post("/internal/sessions")  # Backend-only
async def internal_create_session(...):
    # Atomic operation
    return session_repository.create(...)

# ✅ WORKER LAYER - backend/workers/*
def transcribe_audio(audio_bytes: bytes) -> str:
    # CPU-intensive task in ThreadPoolExecutor
    return transcription_result
```

### Worker Configuration

**IMPORTANT**: This project uses **ThreadPoolExecutor** (no Docker/Redis/Celery).

Configuration (as of 2025-11-15):
- **4 workers** for transcription tasks
- **2 workers** for diarization tasks
- All task tracking persisted in HDF5

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

# backend/workers/sync_workers.py
transcription_executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="transcription"
)

diarization_executor = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="diarization"
)

# Submit CPU-intensive task to worker pool
async def submit_transcription(session_id: str, audio_bytes: bytes):
    loop = asyncio.get_event_loop()

    # Run blocking task in thread pool
    result = await loop.run_in_executor(
        transcription_executor,
        transcribe_audio,
        audio_bytes
    )

    # Save result to HDF5
    task_repository.save_result(
        session_id=session_id,
        task_type="TRANSCRIPTION",
        result=result
    )

    return result
```

## Anti-Patterns

1. ❌ `del f[path]` in HDF5 files
2. ❌ Logging PHI: `email`, `nombre`, `curp`, `phone`
3. ❌ Blocking I/O in async functions
4. ❌ Hardcoded secrets/API keys
5. ❌ Missing `from __future__ import annotations`
6. ❌ Using `Optional[X]` instead of `X | None`
7. ❌ Calling `/api/internal/*` from frontend

## Success Checklist

- [ ] `from __future__ import annotations` at top
- [ ] Type hints on all functions
- [ ] Async I/O for file/network operations
- [ ] Append-only for HDF5 writes
- [ ] No PHI/PII in logs
- [ ] Environment variables for secrets
- [ ] Proper exception handling
- [ ] Tests for new functionality
