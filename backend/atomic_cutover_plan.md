# Atomic Cutover Plan

## Objective
Complete the P0 backend refactoring by:
1. Updating all dependent code to use new package structure
2. Deleting legacy backend/services/ and backend/api/ directories
3. Ensuring zero downtime and full functionality

## Files Requiring Import Updates

### Critical Files (Must Update)
- backend/app/main.py - FastAPI entry point
- backend/workers/tasks/*.py - Background workers
- backend/schemas/*.py - Schema definitions

### Test Files (Can Update Later)
- backend/tests/**/*.py - All test files

## Import Mapping Strategy

The new structure follows this pattern:
```
OLD: backend.services.X → NEW: backend.src.fi_DOMAIN.services.X
OLD: backend.api.public.X → NEW: backend.src.fi_DOMAIN.api.public.X
OLD: backend.api.internal.X → NEW: backend.src.fi_DOMAIN.api.internal.X
```

## Execution Plan

1. **Pre-flight Check**
   - Verify new packages have no import errors
   - Document current system state
   - Create rollback plan

2. **Update Dependencies**
   - Update backend/app/main.py (most critical)
   - Update backend/workers/
   - Update backend/schemas/
   - Update backend/tests/ (optional)

3. **Delete Legacy**
   - rm -rf backend/services/
   - rm -rf backend/api/

4. **Validation**
   - Run syntax check on all Python files
   - Attempt to start FastAPI server
   - Run smoke tests

5. **Commit**
   - Single atomic commit with all changes
   - Clear message documenting the cutover

## Rollback Plan

If cutover fails:
```bash
git reset --hard HEAD~1
git push -f origin main  # (only if pushed)
```

## Risk Assessment

- **Risk Level**: Medium-High
- **Impact**: Complete system refactor
- **Mitigation**: Comprehensive testing before deletion

## Success Criteria

- [ ] All Python files have valid syntax
- [ ] No imports from backend.services.* or backend.api.*
- [ ] FastAPI server starts successfully
- [ ] Legacy directories completely removed
- [ ] Single atomic commit created
