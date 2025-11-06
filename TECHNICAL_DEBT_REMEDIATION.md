# Free Intelligence - Technical Debt Remediation Strategy

**Owner:** Bernard Uriza Orozco
**Date:** 2025-11-05
**Priority:** P0 (Blocks maintainability & onboarding)
**Timeline:** 2 sprints (8 days)
**Approach:** Senior dev best practices + pragmatic prioritization

---

## Executive Summary

Backend has **321 type safety issues**, **17 overly-broad exception handlers**, and **3 large functions (200+ LOC)** causing maintainability friction. This plan reduces debt without disrupting feature delivery.

**Estimated Effort:**
- Quick Wins (5 hrs): Exception handlers, deprecation cleanup, error response standardization
- Medium (8 hrs): Function refactoring, h5py utils, test suite
- Long-term (tracked separately): Type comment cleanup, global state elimination

---

## PHASE 1: CRITICAL FIXES (5 hours) - Sprint START

### 1.1 Fix Broad Exception Handlers in `diarization.py`
**File:** `backend/api/diarization.py`
**Lines:** 526, 604, 668, 733, 784, 847, 893, 935, 973, 1021
**Impact:** Makes errors debuggable, reduces "ghost" failures

**Current pattern (BAD):**
```python
except Exception as err:
    logger.error("JOB_STATUS_FAILED", error=str(err))
    raise HTTPException(status_code=500, detail="Failed to retrieve job status")
```

**New pattern (GOOD):**
```python
except (ValueError, FileNotFoundError, h5py.exceptions.KeyError) as err:
    logger.warning("JOB_STATUS_VALIDATION_FAILED", error=str(err), job_id=job_id)
    raise HTTPException(status_code=400, detail=f"Invalid job ID: {job_id}") from err
except (OSError, IOError) as err:
    logger.error("JOB_STATUS_STORAGE_FAILED", error=str(err), job_id=job_id)
    raise HTTPException(status_code=500, detail="Storage unavailable") from err
except Exception as err:
    logger.critical("JOB_STATUS_UNEXPECTED", error=str(err), job_id=job_id,
                   traceback=traceback.format_exc())
    raise HTTPException(status_code=500, detail="Internal server error") from err
```

**Rule of thumb:** Catch specific exceptions first, generic `Exception` last. Always use `from err` to preserve traceback.

**Task:** Replace pattern in 10 locations
**Acceptance:** No bare `except Exception` without 3+ specific exception types above it

---

### 1.2 Remove Deprecated `_create_lowprio_job()` Function
**File:** `backend/api/diarization.py:77-93`
**Impact:** Removes dead code path, simplifies `upload_audio_for_diarization()`

**Action:**
1. Delete function definition (lines 77-93)
2. Remove references in `upload_audio_for_diarization()` (lines 457-465)
3. Verify no other imports

**Verification:**
```bash
grep -r "_create_lowprio_job" backend/
# Should return 0 matches
```

---

### 1.3 Add Error Handling to `kpis.py`
**File:** `backend/api/kpis.py:26-72`
**Current Issue:** No try/except - crashes if aggregator fails

**Fix:**
```python
@router.get("/kpis", response_model=KPIsResponse)
async def get_kpis(window: str = Query("5m")) -> KPIsResponse:
    """Get aggregated KPIs for monitoring dashboard."""
    try:
        aggregator = get_kpis_aggregator()
        metrics = await aggregator.aggregate(window=window)
        return KPIsResponse(
            timestamp=datetime.now(timezone.utc),
            window=window,
            metrics=metrics
        )
    except ValueError as e:
        logger.warning("KPIS_INVALID_WINDOW", window=window, error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid window: {window}") from e
    except Exception as e:
        logger.error("KPIS_AGGREGATION_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to aggregate metrics") from e
```

---

### 1.4 Standardize Error Response Format
**Goal:** Consistency across all endpoints
**Current state:** Mixed `error_response()` vs `HTTPException` usage

**Decision:** Use `error_response()` helper everywhere (already implemented in codebase)

**Audit files:**
- `backend/api/sessions.py` - use `error_response()` instead of direct `HTTPException`
- `backend/api/triage.py` - standardize format
- `backend/api/kpis.py` - apply above fix

**Verification:**
```bash
grep -r "raise HTTPException" backend/api/ | wc -l
# Should be < 3 (only for edge cases like 404)
```

---

## PHASE 2: HIGH-PRIORITY REFACTORING (8 hours) - Sprint MID-POINT

### 2.1 Refactor `upload_audio_for_diarization()` (237 LOC)
**File:** `backend/api/diarization.py:301-498`
**Goal:** Break into 4 helper functions, each ~50-70 LOC

**Current monolith:**
```
Lines 334-335:  Get services
Lines 338-342:  Validation
Lines 345:      Read audio
Lines 349-356:  Create job
Lines 361-372:  Audit logging
Lines 386-407:  Save audio
Lines 408-434:  Path hardening
Lines 436-454:  Build config
Lines 456-487:  Route to pipeline
Lines 490-498:  Return response
```

**Refactored structure:**
```python
async def upload_audio_for_diarization(...) -> Any:
    """Main endpoint - orchestrates workflow."""
    # Validate input
    validated_input = await _validate_and_prepare_upload(audio, x_session_id)

    # Create job record
    job_id = await _create_diarization_job(validated_input, services)

    # Save and route
    audio_path = await _save_audio_and_route(validated_input, job_id, services)

    # Return response
    return _format_upload_response(job_id, audio_path)

async def _validate_and_prepare_upload(
    audio: UploadFile,
    x_session_id: str
) -> ValidatedUploadInput:
    """Validate audio file and extract metadata."""
    # Lines 338-345 (validation + read)

async def _create_diarization_job(
    input: ValidatedUploadInput,
    services: DIContainer
) -> str:
    """Create job record in HDF5 and return job_id."""
    # Lines 349-356

async def _save_audio_and_route(
    input: ValidatedUploadInput,
    job_id: str,
    services: DIContainer
) -> Path:
    """Save audio file and route to pipeline."""
    # Lines 386-487 (storage + config + routing)

def _format_upload_response(job_id: str, audio_path: Path) -> Any:
    """Format successful upload response."""
    # Lines 490-498
```

**Benefits:**
- Each helper testable in isolation
- Main endpoint becomes 20-30 LOC (readable)
- Easier to add logging/tracing per stage
- Better error messages (know which stage failed)

---

### 2.2 Create `backend/common/h5py_utils.py` - Eliminate 6+ Duplicate Patterns
**Goal:** Centralize HDF5 access, fix 20+ type: ignore comments

**Current duplicated code:**
```python
# In 6+ files:
value = group["field"][index].decode("utf-8")  # type: ignore[index,attr-defined]
```

**New utility:**
```python
# backend/common/h5py_utils.py
from typing import Any
import h5py
from backend.logger import get_logger

logger = get_logger(__name__)

def safe_decode_string(value: Any) -> str:
    """
    Safely decode bytes or convert to string.

    Args:
        value: bytes or string value from HDF5

    Returns:
        Decoded UTF-8 string

    Raises:
        ValueError: If decode fails after fallback
    """
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            logger.warning("DECODE_FALLBACK", value_len=len(value))
            return value.decode('utf-8', errors='replace')
    return str(value)


def get_h5_string(group: h5py.Group | h5py.Dataset, field: str, index: int) -> str:
    """
    Safely retrieve and decode string from HDF5 group.

    Args:
        group: HDF5 group or dataset
        field: Field name in group
        index: Row index

    Returns:
        Decoded string value

    Raises:
        KeyError: If field doesn't exist
        IndexError: If index out of bounds
    """
    if isinstance(group, h5py.Dataset):
        return safe_decode_string(group[index])
    else:
        return safe_decode_string(group[field][index])


def get_h5_value(
    group: h5py.Group | h5py.Dataset,
    field: str,
    index: int,
    dtype: type
) -> Any:
    """Generic HDF5 value accessor with type coercion."""
    try:
        if isinstance(group, h5py.Dataset):
            value = group[index]
        else:
            value = group[field][index]

        if dtype == str:
            return safe_decode_string(value)
        elif dtype in (int, float, bool):
            return dtype(value)
        return value
    except (KeyError, IndexError, TypeError) as e:
        logger.error("H5PY_ACCESS_FAILED", field=field, index=index, error=str(e))
        raise
```

**Usage in code:**
```python
# BEFORE:
text_val = chunk_record["text"][i].decode("utf-8")  # type: ignore[index,attr-defined]

# AFTER:
from backend.common.h5py_utils import get_h5_string
text_val = get_h5_string(chunk_record, "text", i)
```

**Files to update:**
- `backend/services/fi_exporter.py:75`
- `backend/services/diarization_job_service.py:126`
- `backend/services/timeline_api.py` (likely)
- 3+ more

**Acceptance:**
- All HDF5 byte access uses helper
- Type: ignore comments for h5py reduced by 80%

---

### 2.3 Fix Circular Import Pattern
**File:** `backend/common/container.py:17-18`
**Goal:** Remove lazy loader workaround

**Current workaround:**
```python
def _get_logger():
    """Lazy logger initialization to avoid circular imports."""
    from backend.logger import get_logger
    return get_logger(__name__)
```

**Root cause:** `backend.logger` → `backend.common.logger` → `backend.common.__init__` → `backend.common.container`

**Fix:** Reorganize imports
```bash
# 1. Verify import order
python3 -c "import backend.api.diarization; print('OK')"

# 2. Move if needed:
# - backend.logger should NOT import from backend.common
# - OR: move logger implementation to backend.common._logger (private module)

# 3. Update container.py to direct import
from backend.logger import get_logger
logger = get_logger(__name__)
```

**Verification:**
```bash
python3 -c "from backend.common import container; print('OK')"
python3 -c "import backend; print('OK')"
```

---

### 2.4 Create Basic Test Suite (10-15 tests)
**File:** `backend/tests/test_diarization_api.py` (new)
**Goal:** Seed testing culture, catch regressions

**Test structure:**
```python
# backend/tests/test_diarization_api.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.fixture
def sample_audio_file():
    """Create minimal MP3 for testing."""
    # Generate 1-second silence
    import numpy as np
    import wave
    ...

class TestUploadAudioForDiarization:
    """Test upload endpoint."""

    def test_upload_valid_audio(self, sample_audio_file):
        """Should accept valid audio file."""
        response = client.post(
            "/api/diarization/upload",
            files={"audio": sample_audio_file},
            headers={"X-Session-ID": "session_test_001"}
        )
        assert response.status_code == 200
        assert "job_id" in response.json()

    def test_upload_missing_session_id(self, sample_audio_file):
        """Should reject without X-Session-ID header."""
        response = client.post(
            "/api/diarization/upload",
            files={"audio": sample_audio_file}
        )
        assert response.status_code == 400
        assert "session" in response.json()["error"].lower()

    def test_upload_file_too_large(self, oversized_audio_file):
        """Should reject files exceeding MAX_FILE_SIZE."""
        response = client.post(
            "/api/diarization/upload",
            files={"audio": oversized_audio_file},
            headers={"X-Session-ID": "session_test_001"}
        )
        assert response.status_code == 413  # Payload Too Large

    def test_upload_invalid_format(self):
        """Should reject non-audio files."""
        response = client.post(
            "/api/diarization/upload",
            files={"audio": ("test.txt", b"not audio")},
            headers={"X-Session-ID": "session_test_001"}
        )
        assert response.status_code == 400
        assert "audio" in response.json()["error"].lower()

class TestGetJobStatus:
    """Test job status endpoint."""

    def test_get_status_nonexistent_job(self):
        """Should return 404 for unknown job_id."""
        response = client.get("/api/diarization/jobs/nonexistent_id")
        assert response.status_code == 404

    def test_get_status_valid_job(self, uploaded_job_id):
        """Should return job status with chunks."""
        response = client.get(f"/api/diarization/jobs/{uploaded_job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == uploaded_job_id
        assert "status" in data
        assert "chunks" in data
```

**Running tests:**
```bash
pytest backend/tests/test_diarization_api.py -v
pytest backend/tests/test_diarization_api.py -v --cov=backend.api.diarization
```

---

## PHASE 3: TYPE HINT MODERNIZATION (4 hours) - Sprint END

### 3.1 Standardize `Optional[T]` → `T | None`
**Files affected:** 8 files
**Tool:** Use `libcst` to automate

```bash
# Install codemod (if not present)
pip install libcst

# Create migration script
cat > /tmp/modernize_types.py << 'EOF'
import libcst as cst
from pathlib import Path

class OptionalRewriter(cst.CSTTransformer):
    def leave_Subscript(self, original_node: cst.Subscript) -> cst.BaseExpression:
        if isinstance(original_node.value, cst.Name) and original_node.value.value == "Optional":
            # Extract inner type: Optional[str] -> str | None
            inner = original_node.slice[0].slice.value
            return cst.BinaryOperation(
                left=inner,
                operator=cst.BitOr(),
                right=cst.Name("None")
            )
        return original_node

# Apply to files
for py_file in Path("backend").rglob("*.py"):
    code = py_file.read_text()
    tree = cst.parse_module(code)
    modified = tree.visit(OptionalRewriter())
    py_file.write_text(modified.code)
    print(f"Updated: {py_file}")
EOF

python3 /tmp/modernize_types.py
```

**Verification:**
```bash
grep -r "Optional\[" backend/ | grep -v "__future__" | wc -l
# Should be 0 or < 5 (pre-existing)
```

---

### 3.2 Add Missing Type Hints to Nested Functions
**File:** `backend/services/diarization_job_service.py:26`

**Current:**
```python
def _get_lowprio_status(job_id):  # ❌ Missing types
    """Lazy loader for low-priority job status."""
```

**Updated:**
```python
def _get_lowprio_status(job_id: str) -> dict[str, Any] | None:
    """
    Lazy loader for low-priority job status.

    Args:
        job_id: Unique identifier for diarization job

    Returns:
        Dictionary with keys {status, progress, error} or None if not found
    """
```

**Scan for missing hints:**
```bash
python3 -m pyright backend/services/ --outputjson | grep "no-untyped-def"
```

---

## PHASE 4: LONG-TERM TRACKING (Separate sprints)

### 4.1 Address 323 `type: ignore` Comments
**Current approach:** Use structured ignores (not blanket `# type: ignore`)

**Examples:**
- h5py issues: Create better type stubs or use cast() for one-liners
- logger issues: Fix structlog signature (already partially done)

**Process:**
1. Generate report: `python3 tools/detect_type_errors.py backend/ --export-json`
2. Group by rule (reportIndexIssue, reportAttributeAccessIssue, etc.)
3. Fix per-rule rather than per-file (more effective)

### 4.2 Test Coverage Target
**Goal:** >80% for api/*.py and services/*.py

**Current:** ~5% (2 test files)

**Effort estimate:** 12-16 hours (not in this sprint)

### 4.3 Remove Global Mutable State
**File:** `backend/services/diarization_service.py:60`

**Candidate for DI container or `functools.lru_cache`:**
```python
# AFTER refactoring
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1)
def _check_ollama_available_cached(ttl_timestamp: int) -> bool:
    """Check Ollama availability with 5-minute TTL."""
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def check_ollama_available() -> bool:
    """Thread-safe Ollama availability check with caching."""
    ttl_timestamp = int(datetime.now().timestamp() / 300)  # 5-minute buckets
    return _check_ollama_available_cached(ttl_timestamp)
```

---

## IMPLEMENTATION CHECKLIST

### Week 1 (Sprint START)
- [ ] Fix 17 broad exception handlers in `diarization.py`
- [ ] Remove `_create_lowprio_job()` dead code
- [ ] Add error handling to `kpis.py`
- [ ] Standardize error response format in sessions.py and triage.py
- [ ] Commit: `fix(api): Critical exception handling improvements`

### Week 2 (Sprint MID-POINT)
- [ ] Refactor `upload_audio_for_diarization()` → 4 helpers
- [ ] Create `backend/common/h5py_utils.py`
- [ ] Update 6 files to use h5py utils
- [ ] Fix circular import in container.py
- [ ] Create test suite (test_diarization_api.py, 10+ cases)
- [ ] Commit: `refactor(api,services): Extract helpers, centralize HDF5 access`

### Week 2 (Sprint END)
- [ ] Modernize type hints: `Optional[T]` → `T | None`
- [ ] Add missing type hints to nested functions
- [ ] Run full type check: `make type-check-all`
- [ ] Commit: `chore(typing): Modernize type hints to PEP 604`

### Post-Sprint (Tracked separately)
- [ ] Address `type: ignore` comments systematically (321 remaining)
- [ ] Increase test coverage to >80%
- [ ] Eliminate global mutable state
- [ ] Add CI checks for type coverage, lint, docstring coverage

---

## SUCCESS METRICS

### After Phase 1 (Quick Wins)
- ✅ 0 bare `except Exception` handlers
- ✅ All endpoints have explicit error handling
- ✅ Error responses consistent (single format)
- ✅ 20 lines of dead code removed

### After Phase 2 (Refactoring)
- ✅ Largest function reduced from 237 → 30 LOC
- ✅ 20+ `# type: ignore` comments eliminated (h5py utils)
- ✅ 10+ test cases passing
- ✅ Import order verified (no circular dependencies)

### After Phase 3 (Type Hints)
- ✅ 0 `Optional[T]` in codebase (100% PEP 604)
- ✅ All functions have explicit return types
- ✅ `pyright --strict` passes with <10 errors

### Long-term (Tracked Q1 2025)
- ✅ Test coverage >80%
- ✅ 0 global mutable state
- ✅ 0 `# type: ignore` comments (except unavoidable h5py ones)
- ✅ CI enforces type checking + lint

---

## REFERENCES

**Modern Python Best Practices:**
- PEP 604: `X | None` instead of `Optional[X]`
- PEP 8: Exception handling specificity
- PEP 257: Docstring conventions
- Pylance: https://github.com/microsoft/pylance-release/blob/main/docs/diagnostics

**FastAPI Best Practices:**
- Layered architecture (routes → services → repos)
- Dependency injection for testability
- Structured logging with context

**Senior Dev Principles:**
- Fix root causes, not symptoms
- Prioritize debuggability (good error messages)
- Write tests before refactoring
- Commit frequently with clear messages
- Measure impact (before/after metrics)

---

## COMMIT MESSAGES (Template)

```
fix(api): Replace broad exception handlers with specific types

- Fix 17 instances of bare `except Exception` in diarization.py
- Add 3+ specific exception types before fallback handler
- Use `from err` to preserve exception context in logs
- Improves debuggability: now can distinguish validation vs storage errors

Fixes: #FI-API-DEBT-001
```

```
refactor(api): Extract upload validation & routing into helpers

- Split upload_audio_for_diarization() from 237 → 30 LOC endpoint
- Extract _validate_and_prepare_upload() (50 LOC)
- Extract _create_diarization_job() (40 LOC)
- Extract _save_audio_and_route() (100 LOC)
- Extract _format_upload_response() (20 LOC)
- Each helper now independently testable

Fixes: #FI-API-DEBT-003
```

```
feat(common): Add h5py utilities to eliminate byte-decoding duplication

- New: backend/common/h5py_utils.py with safe_decode_string()
- New: get_h5_string() and get_h5_value() helpers
- Updated 6 files to use utilities (fi_exporter.py, diarization_job_service.py, etc.)
- Reduces type: ignore comments by 20+
- Centralizes error handling for malformed UTF-8

Fixes: #FI-API-DEBT-005
```

---

**Last Updated:** 2025-11-05
**Next Review:** 2025-11-13 (post-implementation)
