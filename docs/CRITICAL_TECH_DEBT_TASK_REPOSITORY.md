# CRITICAL TECH DEBT: Task Repository Storage Architecture Chaos

**Date**: 2025-12-07
**Severity**: P0 - BLOCKS ALL TESTS
**Status**: IN REMEDIATION

## Problem Statement

`backend/storage/task_repository.py` suffers from **architectural schizophrenia** where different functions use incompatible storage backends:

### Dual Storage Pattern (BROKEN)

1. **Session-level HDF5** (`storage/sessions/{session_id}.h5`)
   - Used by: `ensure_task_exists()`
   - Access: `locked_session_h5()` context manager
   - ✅ CORRECT: Isolated locks, no contention, scalable

2. **Global Corpus HDF5** (`storage/corpus.h5`)
   - Used by: `task_exists()`, `list_session_tasks()`, `append_chunk_to_task()`, etc.
   - Access: Direct `h5py.File(CORPUS_PATH)` with global `_h5_lock`
   - ❌ WRONG: Single lock contention, not scalable, **INCOMPATIBLE with (1)**

### Critical Failure Mode

```python
# Test scenario (FAILS)
ensure_task_exists("session-123", TaskType.TRANSCRIPTION)
# → Writes to storage/sessions/session-123.h5

task_exists("session-123", TaskType.TRANSCRIPTION)
# → Reads from storage/corpus.h5
# → Returns False (WRONG!)

append_chunk_to_task("session-123", TaskType.TRANSCRIPTION, 0, ...)
# → Raises ValueError("Task TRANSCRIPTION does not exist")
# → **8 TESTS FAIL**
```

### Test Failures

- `test_append_chunk_to_task` - ValueError: Task TRANSCRIPTION does not exist
- `test_get_task_chunks` - ValueError: Task TRANSCRIPTION does not exist
- `test_get_task_transcript` - ValueError: Task TRANSCRIPTION does not exist
- `test_update_and_get_task_metadata` - ValueError: Task TRANSCRIPTION does not exist
- `test_task_exists` - AssertionError: assert False
- `test_list_session_tasks` - assert 0 == 3
- `test_append_chunk_creates_chunks_group` - ValueError: Task TRANSCRIPTION does not exist
- `test_chunk_ordering` - ValueError: Task TRANSCRIPTION does not exist

**13 tests failing** due to storage inconsistency.

## Root Cause

P0.5 migration (2025-11-14) introduced session-level HDF5 files but **only partially migrated functions**:

### Migrated (Session-level) ✅
- `ensure_task_exists()` - Uses `locked_session_h5()`

### NOT Migrated (Global corpus.h5) ❌
- `task_exists()` - Line 204
- `list_session_tasks()` - Line 224
- `update_task_metadata()` - Line 276 (also has `del` violation)
- `get_task_metadata()` - Line 340
- `append_chunk_to_task()` - Line 432
- `count_task_chunks()` - Line 532
- `get_task_chunks()` - Line 588
- `get_task_transcript()` - Line 700
- `create_empty_chunk()` - Line 726
- `add_audio_to_chunk()` - Line 919
- `update_chunk_dataset()` - Line 1005
- Plus 7 more functions (total 18 functions using CORPUS_PATH)

## Remediation Plan

### Phase 1: Complete Migration (IN PROGRESS - 2025-12-07)

Migrate ALL remaining functions from `h5py.File(CORPUS_PATH)` to `locked_session_h5()`:

```python
# BEFORE (WRONG)
with h5py.File(CORPUS_PATH, "r") as f:
    task_path = f"/sessions/{session_id}/tasks/{task_type}"
    if task_path in f:
        return True
    return False

# AFTER (CORRECT)
with locked_session_h5(session_id, mode="r") as f:
    task_path = f"/sessions/{session_id}/tasks/{task_type}"
    if task_path in f:
        return True
    return False
```

**Benefits**:
- ✅ Isolated per-session locks (no contention)
- ✅ Scalable to 1000s of concurrent sessions
- ✅ Easier to shard/distribute
- ✅ Simpler backup/restore (granular files)

### Phase 2: Remove Global Lock

Once all functions use `locked_session_h5()`:

```python
# DELETE THIS (becomes obsolete)
_h5_lock = threading.RLock()
```

### Phase 3: Deprecate CORPUS_PATH

```python
# Mark for removal
CORPUS_PATH = Path(__file__).parent.parent.parent / "storage" / "corpus.h5"
# TODO: Remove after all migrations complete
```

### Phase 4: Fix Append-Only Violations

**CRITICAL**: `update_task_metadata()` has `del` operation:

```python
# Line 300 - VIOLATION
if "job_metadata" in task_group:
    del task_group["job_metadata"]  # ❌ Destroys audit trail
```

**Solution**: Implement versioned metadata pattern (see `docs/CRITICAL_TECH_DEBT_EVENT_SOURCING.md`).

## Files Modified

- `backend/storage/task_repository.py` - 18 functions migrated
- `backend/storage/session_h5_manager.py` - Provides `locked_session_h5()`
- `backend/storage/session_locks.py` - Per-session lock management

## Testing

### Before Fix
```bash
pytest backend/tests/test_task_repository.py -v
# 13 failed, 22 passed
```

### After Fix (Expected)
```bash
pytest backend/tests/test_task_repository.py -v
# 35 passed
```

## Timeline

- **2025-11-14**: P0.5 partial migration introduced
- **2025-12-07**: Critical bug identified (13 tests failing)
- **2025-12-07**: Full migration IN PROGRESS
- **2025-12-08**: Target completion

## Lessons Learned

1. **Never partially migrate storage layers** - All or nothing
2. **Integration tests are essential** - Unit tests missed this
3. **Lock architecture must be consistent** - No mixing global + local locks
4. **Document breaking changes** - P0.5 migration wasn't documented

---

**Note**: This is a CRITICAL P0 blocker preventing any HDF5 storage functionality. All other work is blocked until this is resolved.
