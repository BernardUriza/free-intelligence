# Exact Code Fixes - Copy/Paste Ready

**Purpose**: Line-by-line fixes ready to implement
**Format**: Each fix shows current code and replacement code
**Validation**: Includes test command after each fix

---

## 1. CREATE: backend/types.py

Copy this entire file into a new file at `backend/types.py`:

```python
#!/usr/bin/env python3
"""
Type definitions for Free Intelligence backend.

Purpose: Centralize TypedDicts and domain types for type safety.
Location: backend/types.py
Created: 2025-10-31
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
    error: str


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
    chunks: list[dict[str, Any]]
    created_at: str
    updated_at: str
    error: str


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
```

**Verify**:
```bash
python -m py_compile backend/types.py && echo "✅ Compiles"
```

---

## 2. FIX: adapters_redux.py - Line 23 (Import)

**Current**:
```python
from datetime import datetime
from typing import Any, Optional
```

**Replace with**:
```python
from datetime import datetime, timezone
from typing import Any
```

**Verify**:
```bash
python -c "from backend.adapters_redux import ReduxAdapter; print('✅ Import OK')"
```

---

## 3. FIX: adapters_redux.py - Line 349 (datetime)

**Current**:
```python
        event = ConsultationEvent(
            event_id=str(uuid4()),
            consultation_id=consultation_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            payload=event_payload,
```

**Replace with**:
```python
        event = ConsultationEvent(
            event_id=str(uuid4()),
            consultation_id=consultation_id,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            payload=event_payload,
```

**Verify**:
```bash
python -c "
from backend.adapters_redux import ReduxAdapter
from datetime import timezone
adapter = ReduxAdapter()
event = adapter.translate_action({'type': 'medicalChat/addMessage', 'payload': {'content': 'test'}}, 'c1', 'u1')
assert event.timestamp.tzinfo == timezone.utc
print('✅ Datetime is timezone-aware')
"
```

---

## 4. FIX: adapters_redux.py - Line 310 (Optional → |)

**Current**:
```python
    def translate_action(
        self,
        redux_action: dict[str, Any],
        consultation_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> ConsultationEvent:
```

**Replace with**:
```python
    def translate_action(
        self,
        redux_action: dict[str, Any],
        consultation_id: str,
        user_id: str,
        session_id: str | None = None,
    ) -> ConsultationEvent:
```

---

## 5. FIX: adapters_redux.py - Line 329-412 (Input validation)

**Current**:
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
        redux_payload = redux_action.get("payload", {})

        # Map action type to event type
        if action_type not in ACTION_TO_EVENT_MAP:
```

**Replace with**:
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

        # Validate action type exists and is string
        if not action_type or not isinstance(action_type, str):
            raise ValueError(f"Redux action missing 'type' field: {redux_action}")

        redux_payload = redux_action.get("payload")

        # Ensure payload is dict
        if redux_payload is None:
            redux_payload = {}
        elif not isinstance(redux_payload, dict):
            raise ValueError(f"Redux payload must be dict, got {type(redux_payload)}")

        # Map action type to event type
        if action_type not in ACTION_TO_EVENT_MAP:
```

---

## 6. FIX: adapters_redux.py - Line 369-412 (_translate_payload method)

**Current**:
```python
    def _translate_payload(self, action_type: str, redux_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Translate Redux payload to event payload.

        Args:
            action_type: Redux action type
            redux_payload: Redux payload dict

        Returns:
            Translated event payload dict
        """
        # Map action types to translator methods
        translator_map = {
```

**Add at start of function after docstring**:
```python
    def _translate_payload(self, action_type: str, redux_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Translate Redux payload to event payload.

        Args:
            action_type: Redux action type
            redux_payload: Redux payload dict

        Returns:
            Translated event payload dict
        """
        # Guarantee redux_payload is dict (should be from translate_action validation)
        if not redux_payload or not isinstance(redux_payload, dict):
            return {}

        # Map action types to translator methods
        translator_map = {
```

---

## 7. FIX: adapters_redux.py - Line 449-468 (Type hints for events list)

**Current**:
```python
    def translate_batch(
        self,
        redux_actions: list[dict[str, Any]],
        consultation_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> list[ConsultationEvent]:
        """..."""
        events = []

        for redux_action in redux_actions:
```

**Replace with**:
```python
    def translate_batch(
        self,
        redux_actions: list[dict[str, Any]],
        consultation_id: str,
        user_id: str,
        session_id: str | None = None,
    ) -> list[ConsultationEvent]:
        """..."""
        events: list[ConsultationEvent] = []

        for redux_action in redux_actions:
```

---

## 8. FIX: adapters_redux.py - Lines 476-495 (Simplify validate_redux_action)

**Current**:
```python
def validate_redux_action(redux_action: dict[str, Any]) -> bool:
    """
    Validate Redux action structure.

    Args:
        redux_action: Redux action dict

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(redux_action, dict):
        return False

    if "type" not in redux_action:
        return False

    if not isinstance(redux_action["type"], str):
        return False

    return True
```

**Replace with**:
```python
def validate_redux_action(redux_action: dict[str, Any]) -> bool:
    """
    Validate Redux action structure.

    Args:
        redux_action: Redux action dict

    Returns:
        True if valid, False otherwise
    """
    return (
        "type" in redux_action
        and isinstance(redux_action["type"], str)
    )
```

---

## 9. FIX: backend/audit_logs.py - Line 14 (Add import)

**Current**:
```python
import h5py

# Audit log schema
```

**Add after imports (after line 14)**:
```python
import h5py

from backend.types import AuditLogDict, AuditStatsDict
```

---

## 10. FIX: backend/audit_logs.py - Line 241 (Return type)

**Current**:
```python
def get_audit_logs(
    corpus_path: str,
    limit: int = 100,
    operation_filter: Optional[str] = None,
    user_filter: Optional[str] = None,
) -> list[dict]:
```

**Replace with**:
```python
def get_audit_logs(
    corpus_path: str,
    limit: int = 100,
    operation_filter: str | None = None,
    user_filter: str | None = None,
) -> list[AuditLogDict]:
```

---

## 11. FIX: backend/audit_logs.py - Line 308 (Return type)

**Current**:
```python
def get_audit_stats(corpus_path: str) -> dict:
    """
    Get audit log statistics.
    ...
    """
    try:
        with h5py.File(corpus_path, "r") as f:
            if "audit_logs" not in f:
                return {"total_logs": 0, "exists": False}
```

**Replace with**:
```python
def get_audit_stats(corpus_path: str) -> AuditStatsDict:
    """
    Get audit log statistics.
    ...
    """
    try:
        with h5py.File(corpus_path, "r") as f:
            if "audit_logs" not in f:
                return AuditStatsDict(total_logs=0, exists=False)
```

---

## 12. FIX: backend/audit_logs.py - Line 341-346 (Return dict → AuditStatsDict)

**Current**:
```python
            return {
                "total_logs": total,
                "exists": True,
                "status_breakdown": status_counts,
                "operation_breakdown": operation_counts,
            }
```

**Replace with**:
```python
            return AuditStatsDict(
                total_logs=total,
                exists=True,
                status_breakdown=status_counts,
                operation_breakdown=operation_counts,
            )
```

---

## 13. FIX: backend/api/audit.py - Line 9 (Add import)

**Current**:
```python
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
```

**Add after line 9**:
```python
from typing import Optional

from backend.types import AuditLogDict

from fastapi import APIRouter, HTTPException, Query
```

---

## 14. FIX: backend/api/audit.py - Lines 49-50 (Type dict)

**Current**:
```python
class AuditStatsResponse(BaseModel):
    """Response model for audit stats"""

    total_logs: int
    exists: bool
    status_breakdown: dict = Field(default_factory=dict)
    operation_breakdown: dict = Field(default_factory=dict)
```

**Replace with**:
```python
class AuditStatsResponse(BaseModel):
    """Response model for audit stats"""

    total_logs: int
    exists: bool
    status_breakdown: dict[str, int] = Field(default_factory=dict)
    operation_breakdown: dict[str, int] = Field(default_factory=dict)
```

---

## 15. FIX: backend/api/audit.py - Lines 82-88 (DTO mapping)

**Current**:
```python
        logs = get_audit_logs(
            corpus_path, limit=limit, operation_filter=operation, user_filter=user
        )

        return AuditLogsResponse(
            total=len(logs), limit=limit, logs=logs, operation_filter=operation, user_filter=user
        )
```

**Replace with**:
```python
        logs = get_audit_logs(
            corpus_path, limit=limit, operation_filter=operation, user_filter=user
        )

        return AuditLogsResponse(
            total=len(logs),
            limit=limit,
            logs=[AuditLogEntry(**log) for log in logs],  # Convert dict → model
            operation_filter=operation,
            user_filter=user,
        )
```

---

## 16. FIX: backend/api/diarization.py - Lines 280-315 (Unbound variable 'ext')

**Current**:
```python
    # Validate file extension
    if audio.filename:
        ext = audio.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            )

    # Read file
    audio_content = await audio.read()
    file_size = len(audio_content)

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB",
        )

    logger.info(
        "DIARIZATION_UPLOAD_START",
        session_id=x_session_id,
        filename=audio.filename,
        size=file_size,
        lowprio_mode=USE_LOWPRIO_WORKER,
    )

    # Save audio file
    try:
        saved = save_audio_file(
            session_id=x_session_id,
            audio_content=audio_content,
            file_extension=ext,  # ❌ ext could be unbound
```

**Replace with**:
```python
    # Validate filename exists
    if not audio.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Extract and validate extension
    ext = audio.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file
    audio_content = await audio.read()
    file_size = len(audio_content)

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB",
        )

    logger.info(
        "DIARIZATION_UPLOAD_START",
        session_id=x_session_id,
        filename=audio.filename,
        size=file_size,
        lowprio_mode=USE_LOWPRIO_WORKER,
    )

    # Save audio file
    try:
        saved = save_audio_file(
            session_id=x_session_id,
            audio_content=audio_content,
            file_extension=ext,  # ✅ ext guaranteed to exist
```

---

## 17. FIX: backend/api/diarization.py - Lines 350-360 (Refactor config overrides)

**Current**:
```python
    # Build configuration dict from optional parameters
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

**Replace with**:
```python
    # Build configuration dict from optional parameters, filtering None values
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

---

## 18. FIX: backend/api/diarization.py - Line 673 (Type union casting)

**Current**:
```python
        content = export_diarization(
            result_data if isinstance(result_data, dict) else DiarizationResult(**result_data),
            format,
        )
```

**Replace with**:
```python
        # Ensure result_data is DiarizationResult instance
        if isinstance(result_data, dict):
            result = DiarizationResult(**result_data)
        else:
            result = result_data

        # Now type-safe
        content = export_diarization(result, format)
```

---

## Verification Commands

Run these in sequence after making all fixes:

```bash
# 1. Syntax check all modified files
python -m py_compile backend/types.py
python -m py_compile backend/adapters_redux.py
python -m py_compile backend/audit_logs.py
python -m py_compile backend/api/audit.py
python -m py_compile backend/api/diarization.py
echo "✅ All files compile"

# 2. Import check
python -c "from backend.types import AuditLogDict, JobStatusDict, AuditStatsDict"
echo "✅ Types import successfully"

# 3. Type check (requires mypy)
mypy backend/adapters_redux.py --strict 2>&1 | head -20
mypy backend/audit_logs.py --strict 2>&1 | head -20
mypy backend/api/audit.py --strict 2>&1 | head -20

# 4. Run existing tests
pytest tests/ -v -x

# 5. Check for common issues
grep -n "datetime\.utcnow()" backend/adapters_redux.py || echo "✅ No utcnow() found"
grep -n "Optional\[str\]" backend/adapters_redux.py | head -5 || echo "✅ No Optional[] found"
```

---

## Order of Implementation

1. Create `backend/types.py` (File 1)
2. Fix adapters_redux.py (Fixes 2-8)
3. Fix audit_logs.py (Fixes 9-12)
4. Fix audit.py (Fixes 13-15)
5. Fix diarization.py (Fixes 16-18)
6. Run verification commands
7. Commit with message: "fix: Resolve 66+ type and quality errors"
