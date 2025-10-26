# Free Intelligence - No Direct Mutation Policy

**Version**: 1.0
**Date**: 2025-10-25
**Status**: Active
**Task**: FI-DATA-FIX-001

---

## 📋 Executive Summary

Free Intelligence enforces a **strict no-mutation policy** for all data operations. All state changes must be **event-sourced** and **append-only**. Direct mutation functions are **architecturally forbidden**.

**Core Principle**: *Data is immutable. State is derived from events.*

---

## 🎯 Policy Statement

### Forbidden Operations

The following function patterns are **strictly forbidden** in the codebase:

- ❌ `update_*` - Updates existing data
- ❌ `delete_*` - Deletes existing data
- ❌ `remove_*` - Removes entries
- ❌ `modify_*` - Modifies existing state
- ❌ `edit_*` - Edits records
- ❌ `change_*` - Changes values
- ❌ `overwrite_*` - Overwrites data
- ❌ `truncate_*` - Truncates datasets
- ❌ `drop_*` - Drops tables/groups
- ❌ `clear_*` - Clears data
- ❌ `reset_*` - Resets state
- ❌ `set_*` - Sets values (with exceptions)

### Allowed Operations

Only these function patterns are permitted:

- ✅ `append_*` - Append-only operations
- ✅ `add_*` - Add new entries (synonym for append)
- ✅ `get_*` - Read operations
- ✅ `read_*` - Read operations
- ✅ `fetch_*` - Fetch data
- ✅ `find_*` - Query operations
- ✅ `search_*` - Search operations
- ✅ `list_*` - List operations
- ✅ `count_*` - Count operations
- ✅ `validate_*` - Validation
- ✅ `verify_*` - Verification
- ✅ `check_*` - Integrity checks
- ✅ `init_*` - Initialization
- ✅ `generate_*` - Generation
- ✅ `create_*` - Creation (new entities)
- ✅ `build_*` - Building
- ✅ `load_*` - Loading
- ✅ `parse_*` - Parsing

### Exceptions

The following are allowed for system/testing purposes:

- `setUp`, `tearDown` - unittest lifecycle
- `setUpClass`, `tearDownClass` - unittest class lifecycle
- `set_logger` - Logger configuration
- `set_config` - Config initialization

---

## 🔍 Rationale

### Why No Direct Mutations?

1. **Auditability**: Every change is traceable through events
2. **Reversibility**: All operations can be rolled back
3. **Debugging**: Full history enables root cause analysis
4. **Compliance**: Regulatory requirements for data integrity
5. **Event Sourcing**: State is derived from event log
6. **Concurrency**: Append-only avoids race conditions

### Architectural Benefits

- **Immutable Data**: Corpus is append-only HDF5
- **Event Log**: All mutations recorded as events
- **State Reconstruction**: Can rebuild state from events
- **Time Travel**: Query state at any point in time
- **Determinism**: Same events = same state

---

## 🛠️ Enforcement

### Automated Validation

```bash
# Validate codebase
python3 backend/mutation_validator.py

# Output:
# ✅ VALIDATION PASSED
#    No mutation functions detected in backend/
#    Codebase complies with append-only policy
```

### Pre-Commit Hook

```bash
# In .git/hooks/pre-commit
python3 backend/mutation_validator.py || exit 1
```

### CI/CD Integration

```yaml
# In CI pipeline
- name: Validate No-Mutation Policy
  run: python3 backend/mutation_validator.py
```

---

## 📖 Examples

### ❌ Forbidden (Direct Mutation)

```python
# FORBIDDEN: Direct update
def update_interaction(interaction_id, new_prompt):
    with h5py.File(corpus_path, 'a') as f:
        interactions = f["interactions"]
        idx = find_index(interaction_id)
        interactions["prompt"][idx] = new_prompt  # ❌ MUTATION
```

### ✅ Allowed (Event-Sourced)

```python
# ALLOWED: Append-only operation
def append_interaction_correction(
    original_id,
    corrected_prompt,
    correction_reason
):
    # Create new entry with correction
    new_id = append_interaction(
        session_id=session_id,
        prompt=corrected_prompt,
        response=response,
        model=model,
        tokens=tokens,
        metadata={
            "correction_of": original_id,
            "correction_reason": correction_reason,
            "timestamp": now()
        }
    )

    # Original data remains untouched
    # History preserved
    # Audit trail complete

    return new_id
```

---

## 🔄 How to "Modify" Data

Since direct mutation is forbidden, use these patterns:

### Pattern 1: Append Corrected Version

```python
# Don't update, append corrected version
append_interaction_v2(
    replaces=original_id,
    prompt=corrected_prompt,
    ...
)
```

### Pattern 2: Mark as Deprecated

```python
# Mark old version as deprecated (via new entry)
append_deprecation_event(
    target_id=original_id,
    reason="superseded_by",
    new_id=corrected_id
)
```

### Pattern 3: Snapshot + Append

```python
# Snapshot current state
snapshot = get_current_state(entity_id)

# Modify snapshot (in memory)
snapshot["field"] = new_value

# Append modified snapshot as new version
append_state_snapshot(
    entity_id=entity_id,
    version=snapshot["version"] + 1,
    state=snapshot
)
```

---

## 🧪 Testing

All tests validate no-mutation policy:

```bash
# Run mutation validator tests
python3 tests/test_mutation_validator.py

# Expected: 12 tests passing
# - Forbidden names detected
# - Allowed names pass
# - File scanning works
# - Directory scanning works
# - Real codebase validation passes
```

---

## 📊 Current Status

**Last Validation**: 2025-10-25
**Backend Files Scanned**: 7
**Violations Found**: 0
**Compliance**: ✅ 100%

Functions in codebase:
- `append_interaction` ✅
- `append_embedding` ✅
- `get_corpus_stats` ✅
- `read_interactions` ✅
- `init_corpus` ✅
- `validate_corpus` ✅
- `verify_ownership` ✅
- `generate_corpus_id` ✅

---

## 🔐 Enforcement Level

**Level**: `STRICT`
**Action on Violation**: `BLOCK`
**Bypass**: `NOT ALLOWED`

This policy is **non-negotiable**. Any PR introducing mutation functions will be automatically rejected by CI.

---

## 📚 Related Policies

- `APPEND_ONLY_POLICY.md` - HDF5 append-only enforcement
- `EVENT_NAMING.md` - Event naming conventions
- `docs/events.md` - Canonical event list

---

## 🔄 Changelog

### v1.0 - 2025-10-25
- ✅ Initial policy definition
- ✅ Mutation validator implemented
- ✅ 12 tests passing
- ✅ Backend validated (0 violations)
- ✅ Documentation complete

---

**Policy Owner**: Bernard Uriza Orozco
**Enforcement**: `mutation_validator.py`
**Contact**: See CLAUDE.md for context
