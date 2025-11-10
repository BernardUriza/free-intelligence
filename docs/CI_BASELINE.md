# CI Baseline & Quality Gates

**Last Updated:** 2025-11-09
**Owner:** Bernard Uriza Orozco
**Related Card:** FI-REFACTOR-010

## Executive Summary

Baseline de calidad establecido para prevenir regresiones en el backend. CI pipeline en `.github/workflows/backend-ci.yml` valida type checking, tests, lint y security en cada push/PR.

---

## 📊 Current Baselines (2025-11-09 - Updated 18:30)

### Type Checking (Pyright)
```json
{
  "tool": "pyright",
  "date": "2025-11-09",
  "total_errors": 0,
  "total_warnings": 11,
  "files_affected": 8
}
```

**Remaining Warnings:**
- `reportOperatorIssue`: 5 (h5py type incompatibilities - known issue)
- `reportOptionalSubscript`: 3 (fi_exporter.py - optional checks)
- `reportOptionalMemberAccess`: 2 (audit_technical_debt.py - h5py)

**Command:** `make type-check-export`
**Output:** `ops/type_check_results/results.json`

**Gate:** ✅ 0 errors enforced, warnings allowed (h5py typing limitations)

---

### Test Suite
```bash
Backend Tests: pytest backend/tests/
Status: ✅ All tests collecting (25 in test_diarization_api.py)
Warnings: 0 Pydantic deprecations (migrated to V2)
```

**Fixes Applied (2025-11-09):**
- ✅ Pydantic V2 migration complete (14 models, 6 files)
- ✅ Fixed test_diarization_api.py import error
- ✅ Coverage gates enforced (70% minimum)

**Command:** `pytest backend/tests/ -v --cov --cov-fail-under=70`
**Gate:** ✅ CI enforces 70% minimum coverage

---

### Import Validation
```bash
✅ backend.app.main:app
✅ backend.services.diarization_service
✅ backend.api.internal.diarization.router
```

**Command:**
```bash
python3 -c "from backend.app.main import app"
```

**Gate:** ✅ Zero import errors tolerated

---

## 🚦 CI Pipeline Jobs

### 1. Type Check (Pyright)
- **Trigger:** Push/PR to `main` or `develop`
- **Paths:** `backend/**`, `packages/**`, `pyproject.toml`
- **Command:** `make type-check`
- **Failure:** Exports JSON report, continues (warnings allowed)

### 2. Test Suite
- **Matrix:** Python 3.9, 3.11
- **Command:** `pytest backend/tests/ --cov --cov-report=xml`
- **Coverage:** Uploads to Codecov (Python 3.9 only)
- **Failure:** CI fails if tests fail

### 3. Lint (Ruff)
- **Command:** `ruff check backend/ --output-format=github`
- **Format:** `ruff format backend/ --check`
- **Failure:** CI fails on lint errors

### 4. Security (Bandit)
- **Command:** `bandit -r backend/ -f json`
- **Output:** Uploads `bandit-security-report.json`
- **Failure:** Continues (report only)

### 5. Build Validation
- **Depends on:** type-check, test, lint
- **Validates:** Package installation, HDF5 dependencies
- **Command:** `python -c "import backend; import h5py"`
- **Failure:** CI fails if imports fail

---

## 📈 Historical Progress

| Date | Pyright Errors | Pyright Warnings | Files Affected | Pydantic Warnings |
|------|----------------|------------------|----------------|-------------------|
| 2025-11-07 | 821 | 57 | 57 | - |
| 2025-11-09 AM | 4 | 11 | 8 | 21 |
| **2025-11-09 PM** | **0** | **11** | **8** | **0** |

**Improvement:**
- Type errors: 100% reduction (821 → 0) ✅
- Pydantic V2: 100% migrated (21 → 0) ✅

---

## 🎯 Quality Gates

### Pre-Commit (Local)
```bash
make type-check      # Quick check (2 sec)
pytest backend/tests/ -q
ruff check backend/
```

### CI Gates (GitHub Actions)
- ✅ Type errors: 0 required (warnings allowed)
- ✅ Tests: Must pass
- ✅ Coverage: ≥70% required
- ✅ Lint: Must pass (Ruff)
- ✅ Build: Must pass (import validation)
- ℹ️ Security: Report only (Bandit)

### Deployment Gates
- ✅ All CI jobs green
- ✅ Branch: `main` or `develop`
- ✅ No merge conflicts

---

## 🔧 Commands Reference

```bash
# Type checking
make type-check                # Quick Pyright check
make type-check-all            # Pyright + Mypy + Ruff
make type-check-export         # Export JSON report

# Testing
pytest backend/tests/ -v       # Verbose test run
make test                      # Standard test run

# Linting
ruff check backend/            # Lint check
ruff format backend/ --check   # Format check

# Import validation
python3 -c "from backend.app.main import app"

# Full CI simulation (local)
make type-check && pytest backend/tests/ && ruff check backend/
```

---

## 📝 Maintenance

**Review Baseline:** Every sprint (4 days)
**Update Gates:** When baseline improves significantly
**Document Changes:** In this file + FI-REFACTOR-010 card

**Completed (2025-11-09):**
1. ✅ Fixed Pydantic V2 deprecations (21 → 0)
2. ✅ Resolved `test_diarization_api.py` collection error
3. ✅ Reduced type errors from 4 → 0
4. ✅ Added coverage gates (minimum 70%)

**Next Steps:**
1. Reduce warnings: 11 → <5 (h5py type stubs)
2. Increase coverage: baseline → 80%+
3. Add mutation testing (optional)

---

## 📚 References

- CI Pipeline: `.github/workflows/backend-ci.yml`
- Type Check Tool: `tools/detect_type_errors.py`
- Pyright Config: `pyrightconfig.json`
- Type Check Docs: `docs/TYPE_CHECKING_QUICKSTART.md`
