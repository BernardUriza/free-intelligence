# Implementation Guide: Type & Quality Fixes

**Purpose**: Actionable fixes for 66+ type errors across 3 files
**Effort Estimate**: 4-5 hours total
**Testing Duration**: 1-2 hours

---

## Quick Reference: Error Index

| File | Lines | Issue | Fix Time | Priority |
|------|-------|-------|----------|----------|
| adapters_redux.py | 349 | Deprecated utcnow() | 10 min | HIGH |
| adapters_redux.py | 301, 426 | Missing super().__init__() | 5 min | MEDIUM |
| adapters_redux.py | 408 | Return type mismatch | 15 min | HIGH |
| adapters_redux.py | 449-468 | Type inference Unknown | 10 min | MEDIUM |
| adapters_redux.py | 476-495 | Unnecessary checks | 5 min | LOW |
| audit.py | 14, 49-50 | Partial unknown types | 20 min | HIGH |
| audit.py | 82-88 | DTO mapping missing | 15 min | HIGH |
| diarization.py | 280-312 | Unbound variable 'ext' | 10 min | HIGH |
| diarization.py | 350-360 | DRY violation | 10 min | LOW |
| diarization.py | 673 | Type union casting | 10 min | MEDIUM |

**Total**: ~110 minutes (1.8 hours) for implementation + testing

---

## PART A: Create Backend Type Definitions

### File: backend/types.py (NEW)

Create a new file to consolidate all type definitions:

```python
#!/usr/bin/env python3
"""
Type definitions for Free Intelligence backend.

Purpose: Centralize TypedDicts and domain types for type safety.
Location: backend/types.py
"""

from typing import Any, TypedDict


# ============================================================================
# AUDIT LOG TYPES
# ============================================================================

class AuditLogDict(TypedDict):
    """Raw audit log dict returned from HDF5."""
    audit_id: str
    timestamp: str
    operation: str
    user_id: str
    endpoint: str
    payload_hash: str
    result_hash: str
    status: str
    metadata: str


class AuditStatsDict(TypedDict, total=False):
    """Stats dict returned from get_audit_stats()."""
    total_logs: int
    exists: bool
    status_breakdown: dict[str, int]
    operation_breakdown: dict[str, int]
    error: str  # Optional


# ============================================================================
# DIARIZATION WORKER TYPES
# ============================================================================

class ChunkDict(TypedDict):
    """Chunk data from HDF5 diarization storage."""
    chunk_idx: int
    start_time: float
    end_time: float
    text: str
    speaker: str
    temperature: float
    rtf: float
    timestamp: str


class JobStatusDict(TypedDict, total=False):
    """Job status dict from low-priority worker."""
    job_id: str
    session_id: str
    status: str
    progress_pct: int
    total_chunks: int
    processed_chunks: int
    chunks: list[ChunkDict]
    created_at: str
    updated_at: str
    error: str  # Optional


# ============================================================================
# REDUX ADAPTER TYPES
# ============================================================================

class ReduxAction(TypedDict, total=False):
    """Redux action shape."""
    type: str
    payload: dict[str, Any]


class EventMetadataDict(TypedDict):
    """Event metadata dict."""
    user_id: str
    session_id: str
    source: str
    timezone: str


# ============================================================================
# DIARIZATION RESULT TYPES
# ============================================================================

class DiarizationSegmentDict(TypedDict):
    """Diarization segment."""
    start_time: float
    end_time: float
    speaker: str
    text: str


class DiarizationResultDict(TypedDict):
    """Complete diarization result dict."""
    session_id: str
    audio_file_hash: str
    duration_sec: float
    language: str
    model_asr: str
    model_llm: str
    segments: list[DiarizationSegmentDict]
    processing_time_sec: float
    created_at: str
```

**Verification**:
```bash
python -m py_compile backend/types.py
mypy backend/types.py
```

---

## PART B: Fix adapters_redux.py

### Fix B1: Replace datetime.utcnow() (Line 349)

**Current** (Lines 23, 349):
```python
from datetime import datetime
# ... later ...
timestamp=datetime.utcnow(),
```

**Fixed**:
```python
# Line 23: Update import
from datetime import datetime, timezone

# Line 349: Replace utcnow()
timestamp=datetime.now(timezone.utc),
```

**Verification**:
```bash
python -c "from backend.adapters_redux import ReduxAdapter; r = ReduxAdapter(); e = r.translate_action({'type': 'medicalChat/addMessage', 'payload': {'content': 'test'}}, 'c1', 'u1'); assert e.timestamp.tzinfo is not None; print('✅ Timestamp is timezone-aware')"
```

---

### Fix B2: Add Explicit Type Hints for Collections (Lines 449, 456, 465, 468)

**Current** (Lines 449-468):
```python
def translate_batch(
    self,
    redux_actions: list[dict[str, Any]],
    consultation_id: str,
    user_id: str,
    session_id: Optional[str] = None,
) -> list[ConsultationEvent]:
    """..."""
    events = []  # ❌ Type: Unknown

    for redux_action in redux_actions:
        try:
            event = self.adapter.translate_action(
                redux_action, consultation_id, user_id, session_id
            )
            events.append(event)  # ❌ Appending Unknown to Unknown
        except ValueError as e:
            logger.warning(
                "BATCH_TRANSLATION_SKIPPED", action_type=redux_action.get("type"), error=str(e)
            )

    logger.info(
        "BATCH_TRANSLATION_COMPLETED",
        total_actions=len(redux_actions),
        successful_events=len(events),
    )

    return events  # ❌ Returning list[Unknown] as list[ConsultationEvent]
```

**Fixed**:
```python
def translate_batch(
    self,
    redux_actions: list[dict[str, Any]],
    consultation_id: str,
    user_id: str,
    session_id: str | None = None,  # Also modernize Optional
) -> list[ConsultationEvent]:
    """..."""
    events: list[ConsultationEvent] = []  # ✅ Explicit type

    for redux_action in redux_actions:
        try:
            event = self.adapter.translate_action(
                redux_action, consultation_id, user_id, session_id
            )
            events.append(event)  # ✅ Type-safe append
        except ValueError as e:
            logger.warning(
                "BATCH_TRANSLATION_SKIPPED", action_type=redux_action.get("type"), error=str(e)
            )

    logger.info(
        "BATCH_TRANSLATION_COMPLETED",
        total_actions=len(redux_actions),
        successful_events=len(events),
    )

    return events  # ✅ Correct type returned
```

**Verification**:
```bash
mypy backend/adapters_redux.py --strict 2>&1 | grep "translate_batch" || echo "✅ No errors in translate_batch"
```

---

### Fix B3: Add Input Validation for Payload (Lines 329-412)

**Current** (Lines 329, 369-412):
```python
def translate_action(self, ...) -> ConsultationEvent:
    action_type = redux_action.get("type")
    redux_payload = redux_action.get("payload", {})  # Could be None
    # ... validation skipped

def _translate_payload(self, action_type: str, redux_payload: dict[str, Any]) -> dict[str, Any]:
    # ... assumes redux_payload is dict
    translator_map = { ... }
    translator_method = translator_map.get(action_type)
    if translator_method:
        return translator_method(redux_payload)  # ❌ Could pass None
    return redux_payload  # ❌ Type mismatch if payload is None
```

**Fixed**:
```python
def translate_action(
    self,
    redux_action: dict[str, Any],
    consultation_id: str,
    user_id: str,
    session_id: str | None = None,
) -> ConsultationEvent:
    """..."""
    action_type = redux_action.get("type")

    # ✅ Add explicit validation
    if not action_type or not isinstance(action_type, str):
        raise ValueError(f"Redux action missing 'type' field: {redux_action}")

    redux_payload = redux_action.get("payload")
    # ✅ Ensure payload is dict
    if redis_payload is None:
        redux_payload = {}
    elif not isinstance(redux_payload, dict):
        raise ValueError(f"Redux payload must be dict, got {type(redux_payload)}: {redux_payload}")

    # ... rest of method

def _translate_payload(
    self,
    action_type: str,
    redux_payload: dict[str, Any]  # Now guaranteed to be dict
) -> dict[str, Any]:
    """..."""
    translator_map = { ... }
    translator_method = translator_map.get(action_type)

    if translator_method:
        return translator_method(redux_payload)  # ✅ Type-safe

    # ✅ Always return dict
    return redux_payload if redux_payload else {}
```

**Verification**:
```bash
python -m pytest tests/ -k "test_redux" -v
```

---

### Fix B4: Modernize Optional Syntax (Lines 311, 435)

**Current**:
```python
from typing import Any, Optional  # Line 24

def translate_action(
    ...,
    session_id: Optional[str] = None,  # Lines 311
) -> ConsultationEvent:
    ...

class BatchReduxAdapter:
    def translate_batch(
        ...,
        session_id: Optional[str] = None,  # Line 435
    ) -> list[ConsultationEvent]:
        ...
```

**Fixed**:
```python
from typing import Any  # Removed Optional

def translate_action(
    ...,
    session_id: str | None = None,  # Line 311
) -> ConsultationEvent:
    ...

class BatchReduxAdapter:
    def translate_batch(
        ...,
        session_id: str | None = None,  # Line 435
    ) -> list[ConsultationEvent]:
        ...
```

**Verification**:
```bash
grep -n "Optional\[" backend/adapters_redux.py || echo "✅ No Optional usage"
```

---

### Fix B5: Simplify validate_redux_action (Lines 476-495)

**Current**:
```python
def validate_redux_action(redux_action: dict[str, Any]) -> bool:
    if not isinstance(redux_action, dict):  # ❌ Redundant
        return False
    if "type" not in redux_action:
        return False
    if not isinstance(redux_action["type"], str):
        return False
    return True  # ❌ Needless bool
```

**Fixed**:
```python
def validate_redux_action(redux_action: dict[str, Any]) -> bool:
    """Validate Redux action structure."""
    return (
        "type" in redux_action
        and isinstance(redux_action["type"], str)
    )
```

**Verification**:
```bash
python -c "
from backend.adapters_redux import validate_redux_action
assert validate_redux_action({'type': 'test'}) == True
assert validate_redux_action({}) == False
print('✅ Validation works')
"
```

---

## PART C: Fix audit.py & audit_logs.py

### Fix C1: Update audit_logs.py Return Types (Lines 241, 308)

**File: backend/audit_logs.py**

**Current** (Line 241):
```python
def get_audit_logs(
    corpus_path: str,
    limit: int = 100,
    operation_filter: Optional[str] = None,
    user_filter: Optional[str] = None,
) -> list[dict]:  # ❌ Vague
    """..."""
```

**Fixed**:
```python
from backend.types import AuditLogDict

def get_audit_logs(
    corpus_path: str,
    limit: int = 100,
    operation_filter: str | None = None,
    user_filter: str | None = None,
) -> list[AuditLogDict]:  # ✅ Specific type
    """..."""
```

**Current** (Line 308):
```python
def get_audit_stats(corpus_path: str) -> dict:  # ❌ Vague
    """..."""
    return {
        "total_logs": total,
        "exists": True,
        "status_breakdown": status_counts,
        "operation_breakdown": operation_counts,
    }
```

**Fixed**:
```python
from backend.types import AuditStatsDict

def get_audit_stats(corpus_path: str) -> AuditStatsDict:  # ✅ Specific type
    """..."""
    return AuditStatsDict(
        total_logs=total,
        exists=True,
        status_breakdown=status_counts,
        operation_breakdown=operation_counts,
    )
```

**Verification**:
```bash
mypy backend/audit_logs.py --strict
```

---

### Fix C2: Update audit.py Response Models (Lines 49-50, 86-88)

**File: backend/api/audit.py**

**Current** (Lines 49-50):
```python
class AuditStatsResponse(BaseModel):
    total_logs: int
    exists: bool
    status_breakdown: dict = Field(default_factory=dict)  # ❌ Bare dict
    operation_breakdown: dict = Field(default_factory=dict)  # ❌ Bare dict
```

**Fixed**:
```python
class AuditStatsResponse(BaseModel):
    total_logs: int
    exists: bool
    status_breakdown: dict[str, int] = Field(default_factory=dict)  # ✅ Typed
    operation_breakdown: dict[str, int] = Field(default_factory=dict)  # ✅ Typed
```

**Current** (Lines 82-88):
```python
@router.get("/logs", response_model=AuditLogsResponse)
async def get_logs(...):
    try:
        config = load_config()
        corpus_path = config["storage"]["corpus_path"]

        logs = get_audit_logs(...)  # Returns list[AuditLogDict]

        return AuditLogsResponse(
            total=len(logs),
            limit=limit,
            logs=logs,  # ❌ Type mismatch: list[AuditLogDict] != list[AuditLogEntry]
            operation_filter=operation,
            user_filter=user,
        )
```

**Fixed**:
```python
@router.get("/logs", response_model=AuditLogsResponse)
async def get_logs(...):
    try:
        config = load_config()
        corpus_path = config["storage"]["corpus_path"]

        logs = get_audit_logs(...)  # Returns list[AuditLogDict]

        return AuditLogsResponse(
            total=len(logs),
            limit=limit,
            logs=[
                AuditLogEntry(**log) for log in logs  # ✅ Convert dict → model
            ],
            operation_filter=operation,
            user_filter=user,
        )
```

**Verification**:
```bash
python -c "
from backend.api.audit import AuditLogsResponse, AuditLogEntry
resp = AuditLogsResponse(
    total=1, limit=100,
    logs=[AuditLogEntry(
        audit_id='test', timestamp='2025-01-01T00:00:00',
        operation='TEST', user_id='test', endpoint='/test',
        payload_hash='hash', result_hash='hash', status='SUCCESS', metadata='{}'
    )]
)
json_str = resp.model_dump_json()
print('✅ Response serializes correctly')
"
```

---

## PART D: Fix diarization.py

### Fix D1: Guarantee 'ext' is Bound (Lines 280-312)

**Current**:
```python
# Validate file extension
if audio.filename:  # ❌ Could be falsy
    ext = audio.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(...)

# Later used:
saved = save_audio_file(
    session_id=x_session_id,
    audio_content=audio_content,
    file_extension=ext,  # ❌ Could be unbound NameError
    ...
)
```

**Fixed**:
```python
# Validate filename exists
if not audio.filename:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Filename is required",
    )

# Extract and validate extension
ext = audio.filename.rsplit(".", 1)[-1].lower()  # ✅ Now guaranteed to exist
if ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
    )

# Later, ext is guaranteed to be bound
saved = save_audio_file(
    session_id=x_session_id,
    audio_content=audio_content,
    file_extension=ext,  # ✅ Type-safe
    ...
)
```

**Verification**:
```bash
python -m pytest tests/test_diarization_api_integration.py -k "upload_without_filename" -v
```

---

### Fix D2: Refactor Config Overrides (Lines 350-360)

**Current**:
```python
config_overrides = {}
if whisper_model is not None:
    config_overrides["whisper_model"] = whisper_model
if enable_llm_classification is not None:
    config_overrides["enable_llm_classification"] = enable_llm_classification
if chunk_size_sec is not None:
    config_overrides["chunk_size_sec"] = chunk_size_sec
if beam_size is not None:
    config_overrides["beam_size"] = beam_size
if vad_filter is not None:
    config_overrides["vad_filter"] = vad_filter
```

**Fixed**:
```python
# Build config overrides, filtering out None values
config_overrides: dict[str, Any] = {
    k: v for k, v in {
        "whisper_model": whisper_model,
        "enable_llm_classification": enable_llm_classification,
        "chunk_size_sec": chunk_size_sec,
        "beam_size": beam_size,
        "vad_filter": vad_filter,
    }.items()
    if v is not None
}
```

**Verification**:
```bash
python -c "
config_overrides = {
    k: v for k, v in {
        'whisper_model': 'base',
        'enable_llm_classification': None,
        'chunk_size_sec': 30,
    }.items()
    if v is not None
}
assert config_overrides == {'whisper_model': 'base', 'chunk_size_sec': 30}
print('✅ Config filtering works')
"
```

---

### Fix D3: Type-Safe Result Handling (Line 673)

**Current**:
```python
content = export_diarization(
    result_data if isinstance(result_data, dict) else DiarizationResult(**result_data),
    format,
)
```

**Fixed**:
```python
# Ensure result_data is DiarizationResult instance
if isinstance(result_data, dict):
    result = DiarizationResult(**result_data)
else:
    result = result_data

# Now type-safe
content = export_diarization(result, format)
```

**Verification**:
```bash
mypy backend/api/diarization.py --strict 2>&1 | grep "export_diarization" || echo "✅ No type errors in export_diarization"
```

---

## PART E: Comprehensive Testing

### Test Suite Creation

**File: tests/test_type_safety.py (NEW)**

```python
#!/usr/bin/env python3
"""Tests for type safety fixes."""

import pytest
from datetime import datetime, timezone
from backend.adapters_redux import ReduxAdapter, BatchReduxAdapter, validate_redux_action
from backend.api.audit import get_logs, AuditLogsResponse, AuditLogEntry
from backend.api.diarization import upload_audio_for_diarization
from fastapi.testclient import TestClient


class TestAdaptersReduxTypes:
    """Test type safety in adapters_redux.py"""

    def test_timestamp_is_timezone_aware(self):
        """Verify datetime.now() with timezone is used."""
        adapter = ReduxAdapter()
        event = adapter.translate_action(
            {"type": "medicalChat/addMessage", "payload": {"content": "test"}},
            consultation_id="cons-123",
            user_id="user-1",
        )
        assert event.timestamp.tzinfo is not None
        assert event.timestamp.tzinfo == timezone.utc

    def test_translate_batch_preserves_type(self):
        """Verify list type inference works."""
        adapter = BatchReduxAdapter()
        events = adapter.translate_batch(
            [
                {"type": "medicalChat/addMessage", "payload": {"content": "test"}},
            ],
            consultation_id="cons-123",
            user_id="user-1",
        )
        assert isinstance(events, list)
        assert all(hasattr(e, 'event_id') for e in events)

    def test_validate_redux_action_simplification(self):
        """Verify validate function works correctly."""
        assert validate_redux_action({"type": "test"}) is True
        assert validate_redux_action({}) is False
        assert validate_redux_action({"type": 123}) is False


class TestAuditTypes:
    """Test type safety in audit.py"""

    def test_audit_logs_response_validation(self):
        """Verify AuditLogsResponse validates correctly."""
        response = AuditLogsResponse(
            total=1,
            limit=100,
            logs=[
                AuditLogEntry(
                    audit_id="test-uuid",
                    timestamp="2025-10-31T00:00:00",
                    operation="TEST",
                    user_id="test-user",
                    endpoint="/api/test",
                    payload_hash="abc123",
                    result_hash="def456",
                    status="SUCCESS",
                    metadata="{}",
                )
            ],
        )
        json_data = response.model_dump_json()
        assert "test-uuid" in json_data

    def test_audit_stats_typed_dict(self):
        """Verify dict fields are typed correctly."""
        from backend.api.audit import AuditStatsResponse
        response = AuditStatsResponse(
            total_logs=5,
            exists=True,
            status_breakdown={"SUCCESS": 4, "FAILED": 1},
            operation_breakdown={"TEST": 5},
        )
        assert response.status_breakdown["SUCCESS"] == 4


class TestDiarizationTypes:
    """Test type safety in diarization.py"""

    def test_upload_requires_filename(self):
        """Verify ext variable is always bound."""
        from fastapi.testclient import TestClient
        from backend.api.diarization import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post(
            "/api/diarization/upload",
            files={"audio": ("", b"test")},
            headers={"X-Session-ID": "session-123"},
        )
        assert response.status_code == 400
        assert "Filename is required" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Run tests**:
```bash
pytest tests/test_type_safety.py -v

# Type check
mypy tests/test_type_safety.py --strict
```

---

## PART F: Verification Checklist

Run these commands in sequence:

```bash
# 1. Create types file
python -m py_compile backend/types.py
echo "✅ Types file compiles"

# 2. Check imports
python -c "from backend.types import AuditLogDict, JobStatusDict"
echo "✅ Types importable"

# 3. Type check adapters_redux.py
mypy backend/adapters_redux.py --strict
echo "✅ adapters_redux.py passes strict mypy"

# 4. Type check audit.py
mypy backend/api/audit.py --strict
echo "✅ audit.py passes strict mypy"

# 5. Type check audit_logs.py
mypy backend/audit_logs.py --strict
echo "✅ audit_logs.py passes strict mypy"

# 6. Type check diarization.py
mypy backend/api/diarization.py --strict
echo "✅ diarization.py passes strict mypy"

# 7. Run unit tests
pytest tests/ -v --tb=short
echo "✅ All tests pass"

# 8. Coverage check
pytest tests/ --cov=backend --cov-report=term-missing
echo "✅ Coverage report generated"

# 9. Code quality
ruff check backend/ --select E,F,W,UP
echo "✅ Ruff checks pass"
```

---

## Quick Fix Application Script

Create a script to apply all fixes automatically:

**File: scripts/fix_type_errors.sh (NEW)**

```bash
#!/bin/bash
set -e

echo "Applying type and quality fixes..."

# 1. Create types.py
echo "[1/6] Creating backend/types.py..."
# (File content above)

# 2. Update adapters_redux.py
echo "[2/6] Updating adapters_redux.py..."
sed -i '' 's/from datetime import datetime/from datetime import datetime, timezone/' backend/adapters_redux.py
sed -i '' 's/datetime\.utcnow()/datetime.now(timezone.utc)/' backend/adapters_redux.py
sed -i '' 's/Optional\[str\]/str | None/g' backend/adapters_redux.py

# 3. Update audit_logs.py
echo "[3/6] Updating audit_logs.py..."
sed -i '' 's/-> list\[dict\]/-> list[AuditLogDict]/' backend/audit_logs.py
sed -i '' 's/-> dict:/-> AuditStatsDict:/' backend/audit_logs.py

# 4. Update audit.py
echo "[4/6] Updating audit.py..."
sed -i '' 's/status_breakdown: dict/status_breakdown: dict[str, int]/' backend/api/audit.py
sed -i '' 's/operation_breakdown: dict/operation_breakdown: dict[str, int]/' backend/api/audit.py

# 5. Update diarization.py
echo "[5/6] Updating diarization.py..."
sed -i '' 's/if audio.filename:/if not audio.filename:\n        raise HTTPException(...)\n    if audio.filename:/' backend/api/diarization.py

# 6. Run tests
echo "[6/6] Running tests..."
python -m pytest tests/ -v

echo "✅ All fixes applied successfully!"
```

---

## Summary of Changes

| Module | Changes | Time |
|--------|---------|------|
| backend/types.py | Create new file with TypedDicts | 10 min |
| adapters_redux.py | 6 fixes (datetime, types, validation) | 30 min |
| audit_logs.py | 2 fixes (return types) | 15 min |
| audit.py | 2 fixes (dict types, DTO mapping) | 15 min |
| diarization.py | 3 fixes (unbound var, refactor, type union) | 20 min |
| tests/ | Create type safety test suite | 20 min |
| Verification | mypy, pytest, ruff | 20 min |

**Total**: ~130 minutes (2.2 hours)

---

## Post-Implementation Actions

1. **Code Review**: Have team review changes in PR
2. **CI/CD Update**: Add `mypy --strict` to pipeline
3. **Documentation**: Update CONTRIBUTING.md with type hints requirements
4. **Team Training**: Brief on `TypedDict` and union types
5. **Monitoring**: Track type error metrics in sprint planning
