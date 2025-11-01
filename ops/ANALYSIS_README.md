# Type Checking Error Analysis - Documentation Index

**Generated:** 2025-11-01  
**Analyzed Data:** 600 errors + 124 warnings across 57 files  
**Source:** `/ops/type_check_results/results.json`

## Quick Start

1. **First Time?** Read the [Visual Summary](#visual-summary) below
2. **Want Details?** Open `TYPE_CHECK_ERROR_ANALYSIS.md` (549 lines)
3. **Need to Execute?** Use `TYPE_CHECK_FIX_PRIORITY.json` (programmatic reference)

---

## Visual Summary

### The Problem

600 type checking errors remaining. Root cause distribution:

- **337 errors (56%)** - h5py union type ambiguity
  - h5py operations return `Group | Dataset | Datatype | Any | Unknown`
  - Pyright can't narrow the type through subsequent operations
  - Single ambiguity cascades into 2-4 duplicate errors
  
- **122 errors (20%)** - Function parameter mismatches
  - Signatures refactored, call sites not updated
  - Missing/wrong parameters in constructors

- **95 warnings (16%)** - Stale type: ignore comments
  - Previous PR added defensive comments
  - Now flagged as unnecessary by improved Pyright
  - audit_logs.py has 15 of 25 errors as unnecessary comments

- **46 errors (8%)** - Other issues
  - Type hint errors (any vs Any)
  - Config None handling
  - Unused variables/imports

### The Solution: 3-Phase Approach

**Phase 1 - Hygiene (30 min)** → 600 → 500 errors
- Remove 95 unnecessary type: ignore comments
- Fix 4 type hint/parameter issues

**Phase 2 - Parameter Audit (45 min)** → 500 → 487 errors
- Inspect container.py, audit_repository.py
- Fix 13 call site mismatches

**Phase 3 - Pragmatic Suppression (30 min)** → 487 → 300 errors
- Add bulk # type: ignore[index] and [attr-defined]
- Accept h5py stubs need improvement

**Total Effort:** 95 minutes → 50% reduction (600 → 300)

---

## Files in This Analysis

### 1. TYPE_CHECK_ERROR_ANALYSIS.md
**Type:** Comprehensive Report (549 lines)  
**Purpose:** Deep dive into all error patterns

**Sections:**
- Executive Summary
- Error distribution by category
- Top 10 files impacted
- Root cause analysis: The "Datatype Union" cascade
- Secondary issue: Unnecessary type ignores
- audit_logs.py deep dive (mystery solved!)
- Non-h5py errors (263 total)
- Top 10 specific errors to fix first
- Fixing strategy: manual vs automated
- Breaking the logjam: new approach
- Implementation roadmap

**Best For:**
- Understanding the full picture
- Learning about each error pattern
- Reference material for long-term strategy

### 2. TYPE_CHECK_FIX_PRIORITY.json
**Type:** Structured Data (304 lines)  
**Purpose:** Programmatic reference for automation/tooling

**Contains:**
- Top 10 errors with metadata (rank, effort, impact, file, line, rule)
- 3-phase implementation plan with specific tasks
- Error distribution before/after each phase
- Key insights and long-term strategy
- File prioritization with ratios and reasoning

**Best For:**
- Building automated fixing scripts
- CI/CD integration
- Quick lookups of specific errors
- Feeding into project management tools

### 3. This File (ANALYSIS_README.md)
**Type:** Index and Quick Reference  
**Purpose:** Navigation and overview

---

## Key Findings

### The "Datatype Union" Cascade Effect

```python
# This single operation generates 4 separate errors:
data = interactions[key]  # Returns Group | Dataset | Datatype | Any | Unknown
value = data[idx]         # Error: "__getitem__" not on Datatype (and others)
```

Why? Pyright reports errors for each union member that doesn't support the operation.

### audit_logs.py Mystery Solved

**Question:** 53 "fixes" applied, yet 25 errors remain?

**Answer:** 15 of the 25 errors are "Unnecessary type: ignore" comments.

**Breakdown:**
- 15 warnings = Unnecessary comments
- 5 errors = h5py __getitem__ on union
- 2 errors = h5py .create_dataset on union
- 2 errors = Type hint issues (any vs Any)
- 1 error = h5py __delitem__ on union

**What to do:** Remove the 15 comments, re-run pyright to see if underlying errors surface.

---

## Error Patterns

### Pattern 1: __getitem__ on Datatype (111 errors)
```python
dataset[i]  # Error: "__getitem__" method not defined on type "Datatype"
```
- Only Dataset and Group support indexing
- Datatype (scalar) doesn't
- Fix: `# type: ignore[index]` or `isinstance` check

### Pattern 2: .attrs access (70 errors)
```python
obj.attrs['key'] = value  # Error: Cannot access attribute "attrs" for Datatype
```
- Only Group and Dataset have .attrs
- Fix: `# type: ignore[attr-defined]` or `isinstance` check

### Pattern 3: .keys() on Dataset (34 errors)
```python
for key in dataset.keys()  # Error: Cannot access attribute "keys" for Dataset
```
- Only Group has .keys()
- Fix: `# type: ignore[attr-defined]` or `isinstance` check

### Pattern 4: Slice notation (15 errors)
```python
dataset[start:end]  # Error: Argument of type "slice" cannot be assigned to "str"
```
- h5py stubs incomplete
- Fix: `# type: ignore[index]` or file issue with h5py

---

## Top 10 Files to Fix First

| File | Errors | h5py% | Priority | Strategy |
|------|--------|-------|----------|----------|
| corpus_ops.py | 102 | 82% | HIGH | Bulk suppress (82 errors), fix 19 argtype |
| fi_corpus_api.py | 88 | 39% | HIGH | Audit (24 argtype), suppress rest |
| diarization_worker_lowprio.py | 63 | 73% | HIGH | Bulk suppress |
| corpus_repository.py | 53 | 58% | MEDIUM | Mixed (24 attr suppress, 9 call fix) |
| fi_exporter.py | 48 | 31% | LOW | Remove 39 unnecessary comments |
| fi_event_store.py | 38 | 79% | HIGH | Bulk suppress |
| buffered_writer.py | 37 | 89% | HIGH | Bulk suppress (32 errors), fix 7 argtype |
| session_repository.py | 31 | 45% | MEDIUM | Suppress 13 attr, fix 5 call |
| audit_repository.py | 26 | 62% | MEDIUM | Fix 6 call issues, suppress 14 attr |
| audit_logs.py | 25 | 28% | LOW | Remove 15 comments, fix 2 hints |

---

## Recommended Execution Order

### Session 1 - Hygiene (30 minutes)
```
Phase 1 tasks (removes technical debt):
[ ] Remove 95 unnecessary type: ignore comments
[ ] Fix audit_logs.py:142-143 (any → Any)
[ ] Fix config_loader.py None handling
[ ] Commit: "chore: remove stale type ignores and fix type hints"

Expected: 600 → 500 errors
```

### Session 2 - Parameter Audit (45 minutes)
```
Phase 2 tasks (fixes real bugs):
[ ] Audit container.py function signatures (7 errors)
[ ] Audit audit_repository.py function signatures (6 errors)
[ ] Fix all identified parameter mismatches
[ ] Commit: "fix: resolve function parameter mismatches"

Expected: 500 → 487 errors
```

### Session 3 - Pragmatic Suppression (30 minutes)
```
Phase 3 tasks (pragmatic, temporary):
[ ] Add bulk # type: ignore[index] to indexing operations
[ ] Add bulk # type: ignore[attr-defined] to attribute access
[ ] Re-run type checker
[ ] Commit: "chore: suppress h5py type issues pending stub improvements"

Expected: 487 → 300 errors (50% reduction)
```

---

## Breaking the Logjam: Key Strategy

**Don't try to fix h5py-related errors manually.**

The h5py stubs are incomplete. Instead:

1. **FIX** what you control
   - Parameter mismatches
   - Type hints (any vs Any)
   - Config None handling
   - Effort: 75 minutes, permanent fix

2. **SUPPRESS** what h5py controls
   - Union type ambiguity
   - Attribute/method availability
   - Slice notation support
   - Effort: 30 minutes, temporary (but explicit)

3. **TYPE NARROW** critical paths (backlog)
   - Use isinstance checks in hot paths
   - Eliminates type errors for valid operations
   - Effort: 2-3 hours, permanent solution

This approach recognizes the constraint (h5py stubs) and works around it pragmatically.

---

## Long-Term Strategy

1. **Monitor h5py project** for stub improvements
2. **Gradually remove** type: ignore comments as stubs improve
3. **Invest in type narrowing** for critical corpus operations
4. **Consider contributing** to h5py stubs project if needed

---

## Files to Avoid

- **fi_exporter.py** - Most errors are unnecessary comments (tedious, low value)

## Files to Prioritize

- **corpus_ops.py** (102 errors, 82% h5py) - Concentrated issues, high impact
- **buffered_writer.py** (37 errors, 89% h5py) - Focused operations, quick win
- **fi_corpus_api.py** (88 errors, 39% h5py) - Large file, requires audit

---

## Success Metrics

**After Phase 1 (30 min):**
- 600 → 500 errors
- All unnecessary comments removed
- No new errors introduced
- Commit message: "chore: remove stale type ignores"

**After Phase 2 (45 min):**
- 500 → 487 errors
- All parameter mismatches identified and fixed
- Function signatures verified
- Commit message: "fix: resolve parameter mismatches"

**After Phase 3 (30 min):**
- 487 → 300 errors (50% reduction)
- h5py issues pragmatically suppressed
- All suppressions explicit and documented
- Commit message: "chore: suppress h5py union type issues"

---

## References

- **h5py documentation:** https://docs.h5py.org/
- **Pyright documentation:** https://github.com/microsoft/pyright
- **Type narrowing patterns:** See TYPE_CHECK_ERROR_ANALYSIS.md Section 7

---

**Last Updated:** 2025-11-01  
**Analysis Duration:** ~2 hours  
**Files Analyzed:** 600 errors + 124 warnings  
**Data Quality:** High (verified against source JSON)
