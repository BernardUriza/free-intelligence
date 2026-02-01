# Debugging 500 Errors: Multiple Layers

**Date:** 2025-12-31
**Issue:** `/api/clinics` returning 500 - required fixing 3 separate issues

## Lesson: 500 Errors Often Have Multiple Causes

A single 500 error can mask multiple underlying problems. Fixing one may reveal another.

## The Three Layers We Found

### Layer 1: Import Path Errors
**Symptom:** `ModuleNotFoundError: No module named 'fi_observability'`

**Cause:** Python imports used `from fi_X.Y` but PYTHONPATH wasn't set correctly in production.

**Fix:** Mass sed replacement across 37 files:
```bash
sed -i 's/from fi_/from backend.src.fi_/g' backend/src/fi_*/**/*.py
```

**Learning:** All imports in a single try/except block means ONE failure breaks ALL routers silently.

### Layer 2: Missing `__init__.py`
**Symptom:** Router not loading, no error visible

**Cause:** `backend/src/fi_clinic/api/public/` was missing `__init__.py`

**Fix:** Create package init files:
```python
# backend/src/fi_clinic/api/__init__.py
# fi_clinic.api - Clinic API routes

# backend/src/fi_clinic/api/public/__init__.py
from . import clinic_media, clinics
__all__ = ["clinics", "clinic_media"]
```

**Learning:** Python packages require `__init__.py` files. Without them, imports fail silently.

### Layer 3: Database Corruption
**Symptom:** `AttributeError: 'float' object has no attribute 'replace'`

**Cause:** SQLite stored UUID as float due to type affinity issues.

**Fix:** SQL update to fix the data type.

**Learning:** See `2025-12-31-sqlite-uuid-type-affinity.md` for details.

## Debugging Strategy

### 1. Check Health First
```bash
curl https://app.aurity.io/api/health  # If this works, imports succeeded
```

### 2. Check Logs for Traceback
```bash
ssh root@server "journalctl -u aurity-backend -n 200" | grep -B 20 "Error\|Exception"
```

### 3. Verify Database Connectivity
```bash
ssh root@server "sqlite3 /path/to/db 'SELECT 1'"
```

### 4. Check Data Types
```bash
ssh root@server "sqlite3 /path/to/db 'SELECT column, typeof(column) FROM table LIMIT 5'"
```

### 5. Test Locally First
```bash
curl http://localhost:7001/api/clinics  # Must work before deploying
```

## Silent Failure Patterns to Watch

```python
# BAD - Swallows all errors
try:
    from module import router
    app.include_router(router)
except (ImportError, AttributeError):
    pass  # Silent failure!

# BETTER - Log the error
except (ImportError, AttributeError) as e:
    logger.error(f"Failed to load router: {e}")
    raise  # Or at least log it
```

## Key Takeaways

1. **Fix and verify one layer at a time** - Don't assume one fix solved everything
2. **Check logs after each fix** - New errors may appear
3. **Test locally before production** - Catches most issues early
4. **Silent exceptions are dangerous** - Always log or raise
5. **Database issues can masquerade as code bugs** - Check data types when SQLAlchemy fails
