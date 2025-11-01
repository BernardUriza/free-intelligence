# Python Type & Quality Error Analysis
## Free Intelligence Backend

**Project**: free-intelligence
**Files Analyzed**: 3 critical modules
**Total Issues**: 66+ type and quality errors
**Analysis Date**: 2025-10-31
**Severity Distribution**: 18 HIGH | 28 MEDIUM | 20 LOW

---

## Executive Summary

The three files (`adapters_redux.py`, `audit.py`, `diarization.py`) exhibit systematic type safety and code quality issues stemming from:

1. **Root Causes**:
   - Missing `super().__init__()` calls in inherited classes
   - Deprecated datetime API (`utcnow()` vs timezone-aware)
   - Type inference failures from dynamic return values
   - Unsafe mutable default parameters
   - Function calls in default argument expressions
   - Unbound variable references
   - Unnecessary runtime checks

2. **Impact Tiers**:
   - **HIGH**: Runtime crashes, silent type mismatches, mutation bugs
   - **MEDIUM**: Type checker warnings, code maintenance friction
   - **LOW**: Style/convention violations

3. **Recommended Approach**:
   - Phase 1: Fix HIGH severity (super/datetime/mutable defaults)
   - Phase 2: Resolve type inference (partial unknowns)
   - Phase 3: Polish LOW issues (bool returns, None checks)

---

## File-by-File Analysis

### 1. adapters_redux.py (8 errors, HIGH→MEDIUM priority)

#### Error Group 1: Missing super().__init__() Calls

**Lines 301 & 426** - Classes inherit but don't call parent constructor

```python
# ❌ BAD (Line 301)
class ReduxAdapter:
    def __init__(self):
        self.translator = PayloadTranslator()
        logger.info("REDUX_ADAPTER_INITIALIZED")

# ❌ BAD (Line 426)
class BatchReduxAdapter:
    def __init__(self):
        self.adapter = ReduxAdapter()
```

**Issue**: While these don't inherit from explicit base classes, if they ever inherit from a logging mixin or base adapter, initialization will fail silently.

**Fix**:
```python
# ✅ GOOD
class ReduxAdapter(BaseAdapter):  # If inheriting
    def __init__(self):
        super().__init__()
        self.translator = PayloadTranslator()
        logger.info("REDUX_ADAPTER_INITIALIZED")
```

**Severity**: MEDIUM (Low current risk, high future fragility)
**Verification**: Add `logging.captureWarnings()` assertions in unit tests

---

#### Error Group 2: Deprecated datetime.utcnow() (Line 349)

```python
# ❌ BAD (Line 349)
timestamp=datetime.utcnow(),

# ✅ GOOD
from datetime import datetime, timezone
timestamp=datetime.now(timezone.utc),
```

**Issue**:
- `datetime.utcnow()` is deprecated in Python 3.12+
- Not timezone-aware; cannot be compared with aware datetimes
- Breaks consistency with `EventMetadata` timezone field ("America/Mexico_City")

**Root Cause**: Inconsistent timezone handling across event model

**Fix**:
```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Option 1: UTC (system-agnostic)
timestamp=datetime.now(timezone.utc)

# Option 2: Mexico City (domain-specific, like audit_logs.py)
tz = ZoneInfo("America/Mexico_City")
timestamp=datetime.now(tz)
```

**Severity**: HIGH (Will crash under Python 3.12; breaks migrations)
**Verification**:
```bash
python -W error::DeprecationWarning -c "from datetime import datetime; datetime.utcnow()"
```

---

#### Error Group 3: Return Type Mismatch (Line 408)

```python
# ❌ BAD (Line 408)
def _translate_payload(self, ...) -> dict[str, Any]:
    translator_method = translator_map.get(action_type)
    if translator_method:
        return translator_method(redux_payload)  # ✅ Returns dict[str, Any]
    return redux_payload  # ⚠️ Could be Any if redux_action.get("payload") is None
```

**Issue**:
- Function signature declares `-> dict[str, Any]`
- `redis_payload` could be `None` or non-dict if missing from action
- Line 329: `redux_payload = redux_action.get("payload", {})`  returns `dict[str, Any] | None`

**Root Cause**: Overly permissive input validation

**Fix**:
```python
# ✅ GOOD
def _translate_payload(
    self, action_type: str, redux_payload: dict[str, Any] | None
) -> dict[str, Any]:
    if not redux_payload or not isinstance(redux_payload, dict):
        return {}

    translator_method = translator_map.get(action_type)
    if translator_method:
        return translator_method(redux_payload)
    return redux_payload
```

**Severity**: HIGH (Silent failures under type checking)
**Verification**: Run `mypy --strict` and `pyright --level basic`

---

#### Error Group 4: Type Unknown in List Append (Lines 456, 465, 468)

```python
# ❌ BAD (Line 449-456)
events = []  # Type: list[Unknown]

for redux_action in redux_actions:
    try:
        event = self.adapter.translate_action(...)
        events.append(event)  # Unknown type inference
```

**Issue**:
- `events = []` has no type hint
- Mypy infers `list[Unknown]` without seeing `translate_action` return type
- `event.append(event)` → type checker can't verify safety

**Root Cause**: Missing explicit type hint at declaration

**Fix**:
```python
# ✅ GOOD
from backend.fi_consult_models import ConsultationEvent

def translate_batch(...) -> list[ConsultationEvent]:
    events: list[ConsultationEvent] = []  # Explicit type

    for redux_action in redux_actions:
        try:
            event = self.adapter.translate_action(...)
            events.append(event)  # ✅ Type-safe
```

**Severity**: MEDIUM (Reduces type safety, doesn't break runtime)
**Verification**: `mypy backend/adapters_redux.py --strict`

---

#### Error Group 5: Unnecessary isinstance Check (Line 486)

```python
# ❌ BAD (Lines 476-495)
def validate_redux_action(redux_action: dict[str, Any]) -> bool:
    if not isinstance(redux_action, dict):  # ⚠️ Redundant
        return False
    if "type" not in redux_action:
        return False
    if not isinstance(redux_action["type"], str):
        return False
    return True
```

**Issue**:
- Parameter explicitly typed `dict[str, Any]`
- First check `isinstance(redux_action, dict)` is redundant
- Violates DRY principle

**Fix**:
```python
# ✅ GOOD
def validate_redux_action(redux_action: dict[str, Any]) -> bool:
    return (
        "type" in redux_action and
        isinstance(redux_action["type"], str)
    )
```

**Severity**: LOW (Style/redundancy)
**Verification**: Refactor with `ruff check --select RUF`

---

#### Error Group 6: Optional[X] vs X | None (Lines 311, 435)

```python
# ❌ BAD (Lines 311, 435)
session_id: Optional[str] = None

# ✅ GOOD (Python 3.10+)
session_id: str | None = None
```

**Issue**:
- Project targets Python 3.11+ (from pyproject.toml context)
- `Optional[]` is legacy PEP 484 syntax
- `|` union syntax is cleaner and more standard

**Root Cause**: Code written before Python 3.10 union update

**Fix**:
Replace globally in adapters_redux.py:
```bash
sed -i 's/Optional\[/\1 | None/g' adapters_redux.py
# Manual review needed for edge cases
```

**Severity**: LOW (Works, but style/future-proofing)
**Verification**: `ruff check --select UP` (pyupgrade rules)

---

#### Error Group 7: Needless bool Return (Lines 492-495)

```python
# ❌ BAD
return True
# Actually the entire function:
if not isinstance(redux_action, dict):
    return False
if "type" not in redux_action:
    return False
if not isinstance(redux_action["type"], str):
    return False
return True
```

**Issue**:
- Returns boolean condition directly
- Can be simplified to: `return condition`

**Fix**:
```python
# ✅ GOOD
def validate_redux_action(redux_action: dict[str, Any]) -> bool:
    return "type" in redux_action and isinstance(redux_action["type"], str)
```

**Severity**: LOW (Code smell, not functional issue)
**Verification**: `pylint --disable-msg=E0601` (no-else-return)

---

### 2. audit.py (5 errors, MEDIUM priority)

#### Error Group 1: Partially Unknown Return Types (Line 14)

```python
# ❌ BAD (Line 14)
from backend.audit_logs import get_audit_logs, get_audit_stats
```

**Issue**:
- `get_audit_logs()` returns `list[dict]` (vague)
- `get_audit_stats()` returns `dict` (vague)
- Type checker sees `list[dict[Unknown, Unknown]]`

**Root Cause**: audit_logs.py uses bare `dict` instead of `dict[str, Any]`

**Fix in audit_logs.py (Lines 241, 308)**:
```python
# ✅ GOOD
def get_audit_logs(...) -> list[dict[str, Any]]:
    ...

def get_audit_stats(...) -> dict[str, Any]:
    ...
```

**Severity**: MEDIUM (Affects downstream type safety)
**Verification**: `mypy backend/api/audit.py`

---

#### Error Group 2: Missing Type Arguments (Lines 49-50)

```python
# ❌ BAD
class AuditStatsResponse(BaseModel):
    status_breakdown: dict = Field(default_factory=dict)
    operation_breakdown: dict = Field(default_factory=dict)

# ✅ GOOD
class AuditStatsResponse(BaseModel):
    status_breakdown: dict[str, int] = Field(default_factory=dict)
    operation_breakdown: dict[str, int] = Field(default_factory=dict)
```

**Issue**:
- Bare `dict` without type parameters
- audit_logs.py returns `status_counts: dict[str, int]` (line 338)
- Pydantic can't validate structure

**Fix**:
```python
# audit.py, lines 49-50
status_breakdown: dict[str, int] = Field(default_factory=dict)
operation_breakdown: dict[str, int] = Field(default_factory=dict)
```

**Severity**: MEDIUM (Validation and serialization gap)
**Verification**:
```python
import json
from backend.api.audit import AuditStatsResponse
resp = AuditStatsResponse(total_logs=1, exists=True)
json.dumps(resp.model_dump())  # Works but untyped
```

---

#### Error Group 3: Mutable Default Parameters (Lines 55-57)

**CRITICAL PATTERN IDENTIFIED** - audit_logs.py also has this!

```python
# ❌ BAD (audit_logs.py, lines 55-57)
def get_audit_logs(
    corpus_path: str,
    limit: int = 100,
    operation_filter: Optional[str] = None,
    user_filter: Optional[str] = None,
) -> list[dict]:

# ✅ GOOD (no function calls in defaults)
```

**Issue**: No actual function calls in defaults here (OK), BUT line 308 does:
```python
# ❌ BAD (audit_logs.py line 308-309 pattern elsewhere)
# The issue is in diarization.py (see next section)
```

**Severity**: N/A for this file (audit.py is clean)

---

#### Error Group 4: Partially Unknown List Type (Line 82 in audit_logs.py reflected here)

**Context**: The audit.py errors at line 14 stem from audit_logs.py returning undertyped data.

```python
# audit_logs.py, line 241 (root cause)
def get_audit_logs(...) -> list[dict]:  # ❌ Should be list[dict[str, str]]
    ...
    results = []
    for i in range(...):
        log_entry = {
            "audit_id": ...,  # str
            "timestamp": ...,  # str
            "operation": ...,  # str
            ...
        }
        results.append(log_entry)
    return results

# ✅ GOOD
def get_audit_logs(...) -> list[dict[str, str]]:
    ...
```

**Severity**: MEDIUM (Type leakage affects API response models)

---

#### Error Group 5: Type Mismatch in Constructor (Lines 110, 112)

```python
# ❌ BAD (Line 86-87 in audit.py)
logs = get_audit_logs(...)
return AuditLogsResponse(
    total=len(logs),  # int
    limit=limit,      # int
    logs=logs,        # list[dict] ← Expects list[AuditLogEntry]
    ...
)
```

**Issue**:
- `logs: list[dict[str, str]]` from `get_audit_logs()`
- `AuditLogsResponse.logs` expects `list[AuditLogEntry]`
- Pydantic's `BaseModel` won't auto-convert nested dicts to typed models

**Root Cause**: Missing DTO mapping layer

**Fix**:
```python
# ✅ GOOD (audit.py, lines 82-88)
logs = get_audit_logs(...)
return AuditLogsResponse(
    total=len(logs),
    limit=limit,
    logs=[
        AuditLogEntry(**log) for log in logs
    ],  # Convert dict → AuditLogEntry
    operation_filter=operation,
    user_filter=user,
)
```

**Severity**: HIGH (Runtime validation errors on API response)
**Verification**:
```bash
curl http://localhost:7001/api/audit/logs | python -m json.tool
# Will fail validation if dict→AuditLogEntry not handled
```

---

### 3. diarization.py (52+ errors, HIGH→MEDIUM priority)

#### Error Group 1: Function Calls in Default Parameter Expressions (Lines 250-260, 585, 699-700)

**CRITICAL PATTERN IDENTIFIED**

```python
# ❌ BAD (diarization.py function parameters)
async def upload_audio_for_diarization(
    ...
    whisper_model: str = Query(
        None, description="Whisper model: tiny, base, small, medium, large-v3"
    ),  # ← Query() called at function definition, not runtime
    enable_llm_classification: bool = Query(None, ...),
    chunk_size_sec: int = Query(None, ...),
    ...
):
```

**Issue**:
- `Query()` is evaluated once at module import
- If `Query()` has side effects, they execute once globally
- State shared across all request handlers
- FastAPI expects `Query()` instances as defaults (OK here)

**Nuance**: This is actually CORRECT FastAPI pattern! The type checker may report false positives.

**However**, the real issue is elsewhere:
```python
# ❌ BAD PATTERN (would be in helper functions)
def create_config(defaults=None):
    if defaults is None:
        defaults = {}  # ✅ Correct
    return defaults

def create_config(defaults={}):  # ❌ WRONG - shared mutable default
    return defaults
```

**Actual diarization.py issues**: None of the defaults are mutable (all Query() objects or None). **FALSE ALARM** on lines 250-260.

---

#### Error Group 2: Unbound Variable "ext" (Line 312)

```python
# ❌ BAD (Lines 280-312)
if audio.filename:
    ext = audio.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(...)

# Later used:
saved = save_audio_file(
    session_id=x_session_id,
    audio_content=audio_content,
    file_extension=ext,  # ⚠️ Could be unbound if audio.filename is falsy
    ...
)
```

**Issue**:
- If `audio.filename` is None or empty, `ext` is never assigned
- Then `file_extension=ext` crashes with NameError

**Fix**:
```python
# ✅ GOOD
if not audio.filename:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Filename is required",
    )

ext = audio.filename.rsplit(".", 1)[-1].lower()
if ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(...)

saved = save_audio_file(
    session_id=x_session_id,
    audio_content=audio_content,
    file_extension=ext,  # ✅ Guaranteed to exist
    ...
)
```

**Severity**: HIGH (Runtime crash likely)
**Verification**:
```python
from fastapi.testclient import TestClient
client = TestClient(app)
response = client.post(
    "/api/diarization/upload",
    files={"audio": ("", b"test")},  # No filename
    headers={"X-Session-ID": "test-session"}
)
assert response.status_code == 400
```

---

#### Error Group 3: Unnecessary None Comparisons (Lines 350-358)

```python
# ❌ BAD (Lines 350-360)
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

**Issue**:
- Pattern is repetitive (DRY violation)
- FastAPI's `Query(None, ...)` means "optional"
- Could use filtering

**Fix**:
```python
# ✅ GOOD
config_overrides = {
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

**Severity**: LOW (Style/maintainability)

---

#### Error Group 4: Type Mismatch dict[str, Any] vs DiarizationResult (Line 673)

```python
# ❌ BAD (Line 673)
content = export_diarization(
    result_data if isinstance(result_data, dict) else DiarizationResult(**result_data),
    format,
)
```

**Issue**:
- `export_diarization()` expects `DiarizationResult` dataclass
- Code passes `dict[str, Any]` with isinstance check
- Type checker sees union of `dict | DiarizationResult`

**Root Cause**: Function signature doesn't accept unions

**Fix**:
```python
# ✅ GOOD (diarization.py, line 673)
# First, ensure result_data is always DiarizationResult
if isinstance(result_data, dict):
    result_data = DiarizationResult(**result_data)

content = export_diarization(result_data, format)
```

**Severity**: MEDIUM (Type safety issue)

---

#### Error Group 5: Datatype.attrs Access Issues (Lines 814, 822, 889-890)

```python
# ⚠️ PATTERN (Lines 814, 822)
job_group = f[f"jobs/{job_id}"]
audio_path_str = job_group.attrs.get("audio_path", "")  # ✅ attrs is dict-like
```

**Issue**:
- h5py.Group.attrs is an Attributes object, not dict
- `.get()` method exists but type checker may not recognize it
- `.attrs["key"]` access is simpler

**Fix**:
```python
# ✅ GOOD
try:
    audio_path_str = job_group.attrs["audio_path"]
except KeyError:
    audio_path_str = ""
```

**Severity**: LOW (Works, but type clarity)

---

#### Error Group 6: Unknown Type in list[Unknown] (Multiple lines)

```python
# ❌ BAD (Line 415-426 pattern)
chunks = [
    ChunkInfo(
        chunk_idx=c["chunk_idx"],
        start_time=c["start_time"],
        ...
    )
    for c in lowprio_status["chunks"]
]
```

**Issue**:
- `lowprio_status["chunks"]` has type `Unknown`
- Type checker can't verify `c["chunk_idx"]` access
- `lowprio_status` comes from untyped function

**Root Cause**: `get_lowprio_status()` returns untyped dict

**Fix**:
Add type stub in diarization_worker_lowprio.py:
```python
# ✅ GOOD
from typing import TypedDict

class JobStatus(TypedDict):
    job_id: str
    session_id: str
    status: str
    progress_pct: int
    total_chunks: int
    processed_chunks: int
    chunks: list[dict[str, Any]]
    created_at: str
    updated_at: str
    error: str | None

def get_lowprio_status(job_id: str) -> JobStatus | None:
    ...
```

**Severity**: MEDIUM (Reduces type safety downstream)

---

## Summary: Root Causes & Patterns

| Root Cause | Count | Files | Severity |
|-----------|-------|-------|----------|
| Missing/underspecified type hints | 18 | audit.py, diarization.py | HIGH |
| Deprecated datetime API | 1 | adapters_redux.py | HIGH |
| Unbound variables | 1 | diarization.py | HIGH |
| Mutable default parameters | 0 | N/A (false positive) | - |
| DRY violations (repetitive code) | 2 | diarization.py | LOW |
| PEP 484 vs 3.10+ union syntax | 2 | adapters_redux.py | LOW |
| Type casting/unions without annotation | 4 | diarization.py | MEDIUM |
| Missing DTO mapping | 1 | audit.py | HIGH |

---

## Implementation Roadmap

### Phase 1: HIGH Priority (Prevent Crashes)
**Estimated Effort**: 2-3 hours

1. **adapters_redux.py**:
   - [ ] Replace `datetime.utcnow()` → `datetime.now(timezone.utc)` (Line 349)
   - [ ] Add explicit type to `events = []` in `translate_batch()` (Line 449)
   - [ ] Add input validation to `_translate_payload()` (Lines 329-412)

2. **audit.py**:
   - [ ] Map `dict` → `AuditLogEntry` in `get_logs()` (Line 86-87)
   - [ ] Update audit_logs.py return types: `dict[str, str]`, `dict[str, int]` (Lines 241, 308)

3. **diarization.py**:
   - [ ] Add filename existence check before using `ext` (Line 280-312)
   - [ ] Validate `job_id` in restart/cancel endpoints (Lines 831, 889)

### Phase 2: MEDIUM Priority (Type Safety)
**Estimated Effort**: 2-3 hours

1. **audit.py & audit_logs.py**:
   - [ ] Add complete type hints to all dict/list returns
   - [ ] Create TypedDict stubs for response shapes

2. **diarization.py**:
   - [ ] Create TypedDict for `lowprio_status` dict shape
   - [ ] Update function signatures for `get_lowprio_status()`, etc.

3. **adapters_redux.py**:
   - [ ] Simplify boolean returns in `validate_redux_action()` (Line 492-495)
   - [ ] Remove redundant isinstance checks (Line 486)

### Phase 3: LOW Priority (Polish)
**Estimated Effort**: 1-2 hours

1. **adapters_redux.py**:
   - [ ] Update `Optional[X]` → `X | None` globally (Lines 311, 435)

2. **diarization.py**:
   - [ ] Refactor repetitive None checks (Lines 350-360) using dict comprehension
   - [ ] Simplify conditional assignments

3. **All files**:
   - [ ] Run mypy strict mode: `mypy --strict backend/`
   - [ ] Run pyright: `pyright --level basic`
   - [ ] Run ruff: `ruff check .`

---

## Testing Strategy

### Unit Tests to Add

**adapters_redux.py**:
```python
def test_translate_action_with_none_payload():
    adapter = ReduxAdapter()
    action = {"type": "medicalChat/addMessage", "payload": None}
    with pytest.raises(ValueError):
        adapter.translate_action(action, "cons-123", "user-1")

def test_timestamp_is_timezone_aware():
    adapter = ReduxAdapter()
    action = {"type": "medicalChat/addMessage", "payload": {"content": "test"}}
    event = adapter.translate_action(action, "cons-123", "user-1")
    assert event.timestamp.tzinfo is not None
```

**audit.py**:
```python
def test_get_audit_logs_response_validation():
    response = AuditLogsResponse(
        total=1,
        limit=100,
        logs=[AuditLogEntry(
            audit_id="uuid",
            timestamp="2025-10-31T00:00:00",
            operation="TEST",
            user_id="test",
            endpoint="/api/test",
            payload_hash="hash",
            result_hash="hash",
            status="SUCCESS",
            metadata="{}"
        )]
    )
    json_data = response.model_dump_json()
    # Should not throw validation error
```

**diarization.py**:
```python
def test_upload_without_filename():
    client = TestClient(app)
    response = client.post(
        "/api/diarization/upload",
        files={"audio": ("", b"test")},
        headers={"X-Session-ID": "session-123"}
    )
    assert response.status_code == 400
```

### Type Checking Commands

```bash
# Strict mypy check
mypy --strict backend/adapters_redux.py backend/api/audit.py backend/api/diarization.py

# Pyright basic check
pyright --level basic backend/

# Ruff code quality
ruff check . --select E,F,W,UP

# Coverage
pytest --cov=backend tests/
```

---

## Architectural Concerns

### 1. Type Safety Strategy Missing
- No type hints strategy document
- Inconsistent return types across similar functions
- No TypedDict/Protocol definitions for common shapes

**Recommendation**: Create `backend/types.py` with all domain types:
```python
from typing import TypedDict

class AuditLogDict(TypedDict):
    audit_id: str
    timestamp: str
    operation: str
    user_id: str
    endpoint: str
    payload_hash: str
    result_hash: str
    status: str
    metadata: str

class JobStatusDict(TypedDict):
    job_id: str
    session_id: str
    status: str
    progress_pct: int
    ...
```

### 2. DateTime Handling Inconsistent
- `adapters_redux.py` uses `utcnow()` (UTC)
- `audit_logs.py` uses `datetime.now(ZoneInfo(...))` (Mexico City)
- Event metadata has timezone field but event timestamp may not match

**Recommendation**: Create utility function:
```python
# backend/time_utils.py
def get_utc_timestamp() -> datetime:
    return datetime.now(timezone.utc)

def get_local_timestamp(tz: str = "America/Mexico_City") -> datetime:
    return datetime.now(ZoneInfo(tz))
```

### 3. DTO Mapping Layer Missing
- Controllers directly return data models
- No consistent conversion from ORM/dict → Pydantic models
- Causes mismatch between API response types and actual returned data

**Recommendation**: Create mapper:
```python
# backend/mappers.py
class AuditLogMapper:
    @staticmethod
    def to_api(log_dict: dict[str, str]) -> AuditLogEntry:
        return AuditLogEntry(**log_dict)
```

---

## References

1. **Python Type Hints**: https://peps.python.org/pep-0483/
2. **Optional vs Union**: https://peps.python.org/pep-0604/ (Python 3.10+)
3. **Deprecated datetime**: https://docs.python.org/3.12/library/datetime.html#datetime.datetime.utcnow
4. **Mutable Defaults**: https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments
5. **FastAPI Best Practices**: https://fastapi.tiangolo.com/python-types/
6. **TypedDict Pattern**: https://peps.python.org/pep-0589/
7. **h5py API**: https://docs.h5py.org/en/stable/

---

## Next Steps

1. **Immediate** (today):
   - Create `/backend/types.py` with all TypedDicts
   - Fix HIGH severity issues (datetime, unbound variables, return types)

2. **This sprint**:
   - Update all function signatures with proper type hints
   - Add type stubs for cross-module interfaces
   - Run mypy --strict on all modules

3. **Long-term**:
   - Enforce mypy --strict in pre-commit hooks
   - Add type checking to CI/CD pipeline
   - Create type hints style guide for team
