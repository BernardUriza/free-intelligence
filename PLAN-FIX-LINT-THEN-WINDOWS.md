# Plan Actualizado: Fix Lint → Windows CI/CD

**Prioridad**: Arreglar los 92 errores de lint PRIMERO, luego continuar con Windows CI/CD.

---

## Fase 0: Fix Lint Errors (BLOQUEADOR)

### Problema Identificado

PR #72 (Windows CI/CD) está bloqueado porque el PR gate tiene:
- ✅ Backend: Compiles - PASS
- ❌ Backend: Lint - **FAIL (92 errors)**
- ❌ Backend: Unit Tests - FAIL (depende de lint)
- ⏭️ AI Gatekeeper - SKIPPED (depende de tests)

### Breakdown de Errores

```bash
$ ruff check backend/
Found 92 errors:
  - 91x W293: Blank line contains whitespace (auto-fixable)
  - 1x RUF043: Regex pattern sin raw string (manual fix)
```

**Archivos afectados:**
- backend/tests/unit/test_checkin_models.py (2 errors)
- backend/tests/unit/test_db_models.py (2 errors)
- backend/tests/unit/test_hdf5_soap.py (1 error - RUF043)
- backend/tests/unit/test_llm_extended.py (2 errors)
- backend/tests/unit/test_session_models.py (2 errors)
- backend/tests/unit/test_subscription_models.py (2 errors)
- backend/tests/unit/test_transcription_job.py (2 errors)
- ... (otros archivos con W293)

### Success Criteria

- ✅ `ruff check backend/` returns 0 errors
- ✅ PR gate: Backend Lint - PASS
- ✅ AI Gatekeeper runs and comments on PR

---

## Fix #1: Auto-Fix W293 (Whitespace)

**Complejidad**: Trivial (1 comando)
**Tiempo estimado**: < 1 minuto

### Comando

```bash
ruff check --fix backend/
```

**Resultado esperado:**
```
Found 91 errors (91 fixed, 1 remaining).
```

### Verificación

```bash
ruff check backend/ | grep W293
# Debe estar vacío
```

---

## Fix #2: Manual Fix RUF043 (Regex Raw String)

**Complejidad**: Trivial (cambio de 1 línea)
**Tiempo estimado**: < 1 minuto

### Ubicación

**Archivo**: `backend/tests/unit/test_hdf5_soap.py:56`

**Código actual:**
```python
with pytest.raises(ValueError, match="Task.*not found"):
```

**Código corregido:**
```python
with pytest.raises(ValueError, match=r"Task.*not found"):
                                      ^
                                      Agregar 'r' prefix
```

**Razón del error:**
Python regex patterns con metacharacters (`.`, `*`, `+`, etc.) deben usar raw strings (`r"..."`) para evitar interpretación de escape sequences.

### Implementación

```python
# Edit line 56
- with pytest.raises(ValueError, match="Task.*not found"):
+ with pytest.raises(ValueError, match=r"Task.*not found"):
```

### Verificación

```bash
ruff check backend/tests/unit/test_hdf5_soap.py
# Debe estar limpio
```

---

## Fix #3: Verificar que TODO pasa

### Comando

```bash
ruff check backend/
```

**Salida esperada:**
```
All checks passed!
```

### Si fallan más errores

```bash
# Ver errores restantes
ruff check backend/ --output-format=grouped

# Auto-fix si son fixables
ruff check --fix backend/

# Manual fix si son RUF043 u otros
```

---

## Fix #4: Commit Lint Fixes

### Git Workflow

```bash
# Desde repo root
git add backend/

git commit -m "fix(lint): resolve 92 lint errors (W293 + RUF043)

## Summary
- Auto-fixed 91x W293 (blank line whitespace)
- Manual fix 1x RUF043 (regex raw string in test_hdf5_soap.py:56)

## Changes
Files affected: tests/unit/*.py (whitespace cleanup)

## Verification
\`\`\`bash
ruff check backend/  # All checks passed!
\`\`\`

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git push origin chore/archive-fi-devtools
```

### Resultado Esperado

GitHub Actions should trigger:
- ✅ Backend: Compiles - PASS
- ✅ Backend: Lint - **PASS** (was FAIL)
- ✅ Backend: Unit Tests - PASS
- ✅ AI Gatekeeper - **RUNS** (was SKIPPED)

---

## Fase 1: Windows CI/CD (DESPUÉS de lint fixes)

Una vez que PR #72 tenga lint pasando, continuar con el plan original:

### Ya Implementado ✅

1. Platform-specific binaries (tauri.conf.json)
2. Dynamic versioning (set-version.js)
3. Robust PowerShell signing
4. Post-build verification
5. Platform-specific release jobs
6. Dynamic downloads page (template)
7. Azure cleanup script
8. Migration guide (MIGRATION-GITHUB-RELEASES.md)

### Pending

1. ⏭️ Merge PR #72 (después de lint fixes + AI Gatekeeper approval)
2. ⏭️ Trigger Windows build: `gh workflow run build-desktop.yml -f platform=windows`
3. ⏭️ Test en VM Windows
4. ⏭️ Deploy dynamic `/downloads` page (Fase 2 opcional)

---

## Rollback Plan

Si algo sale mal con los lint fixes:

```bash
# Revert commit
git revert HEAD

# O resetear
git reset --hard HEAD~1
git push --force origin chore/archive-fi-devtools
```

---

## Timeline

| Fase | Estimado | Bloqueador |
|------|----------|-----------|
| Fix #1: Auto-fix W293 | < 1 min | No |
| Fix #2: Manual RUF043 | < 1 min | No |
| Fix #3: Verify | < 1 min | No |
| Fix #4: Commit + Push | < 1 min | No |
| **Wait for CI** | ~2 min | **Sí** (wait for checks) |
| AI Gatekeeper runs | ~1 min | **Sí** (must comment) |
| **TOTAL Fase 0** | **~5-7 min** | - |
| Continue Fase 1 (Windows) | (original plan) | No |

---

## Next Steps

1. **Execute Fase 0 (Fix Lint)** - AHORA
2. Wait for PR checks to pass
3. Review AI Gatekeeper comment
4. If approved → Merge PR #72
5. Continue with Windows CI/CD testing

**Ready to execute Fix #1?**
