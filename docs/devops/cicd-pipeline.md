# CI/CD Pipeline - Free Intelligence

**Fecha**: 2025-10-25
**Task**: FI-CICD-FEAT-001
**Sprint**: SPR-2025W44 (Sprint 2)
**Autor**: Bernard Uriza Orozco

---

## 🎯 Propósito

Enforcement automático de **calidad de código** y **políticas de seguridad** mediante pre-commit hooks.

**Garantiza**:
- ✅ Código validado antes de cada commit
- ✅ 183 tests pasan siempre
- ✅ Políticas de seguridad enforced
- ✅ Convenciones de código respetadas
- ✅ Zero commits rotos en main

---

## 📋 Pipeline de Integrity Gates

### Pre-commit Hooks (6 validadores)

```
┌──────────────────────────────────────┐
│  git commit                          │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  1. Event Validator                  │
│     → UPPER_SNAKE_CASE events        │
└──────────────┬───────────────────────┘
               │ ✅ PASS
               ▼
┌──────────────────────────────────────┐
│  2. Mutation Validator               │
│     → No update/delete functions     │
└──────────────┬───────────────────────┘
               │ ✅ PASS
               ▼
┌──────────────────────────────────────┐
│  3. LLM Audit Policy                 │
│     → All LLM calls must audit       │
└──────────────┬───────────────────────┘
               │ ✅ PASS
               ▼
┌──────────────────────────────────────┐
│  4. LLM Router Policy                │
│     → No direct API imports          │
└──────────────┬───────────────────────┘
               │ ✅ PASS
               ▼
┌──────────────────────────────────────┐
│  5. Unit Tests                       │
│     → 199 tests must pass            │
└──────────────┬───────────────────────┘
               │ ✅ PASS
               ▼
┌──────────────────────────────────────┐
│  6. Commit Message Format            │
│     → Conventional Commits           │
└──────────────┬───────────────────────┘
               │ ✅ PASS
               ▼
┌──────────────────────────────────────┐
│  ✅ COMMIT ACCEPTED                  │
└──────────────────────────────────────┘
```

---

## 🔧 Instalación

### Instalar Pre-commit

```bash
# Opción 1: Via pip
pip3 install pre-commit

# Opción 2: Via homebrew (macOS)
brew install pre-commit
```

### Instalar Hooks

```bash
# Usar script automático (Recomendado)
./scripts/install_hooks.sh

# O manualmente
pre-commit install
pre-commit install --hook-type commit-msg
```

### Verificar Instalación

```bash
# Ejecutar todos los hooks
pre-commit run --all-files
```

---

## 📝 Uso

### Workflow Normal

```bash
# 1. Hacer cambios
echo "new code" >> backend/new_feature.py

# 2. Stage changes
git add backend/new_feature.py

# 3. Commit (hooks se ejecutan automáticamente)
git commit -m "feat(core): add new feature"

# Output:
# Event Validator................................Passed
# Mutation Validator.............................Passed
# LLM Audit Policy...............................Passed
# LLM Router Policy..............................Passed
# Unit Tests.....................................Passed
# Commit Message Format..........................Passed
# [main abc1234] feat(core): add new feature
```

### Si un Hook Falla

```bash
git commit -m "feat: add feature"

# Output:
# Event Validator................................Passed
# Mutation Validator.............................Passed
# LLM Audit Policy...............................Failed
# - hook id: llm-audit-policy
# - exit code: 1
#
# ❌ LLM AUDIT VIOLATIONS DETECTED
#
# 📁 backend/new_feature.py
#    ❌ call_llm_api (line 45)
#       • Missing @require_audit_log decorator
#
# Fix the issue and try again
```

**Acción**: Arreglar el problema y volver a commit.

---

## 🚫 Skip Hooks (Solo Emergencias)

```bash
# ⚠️ SOLO usar en emergencias
git commit --no-verify -m "fix: emergency hotfix"
```

**⚠️ Advertencia**: Esto bypasea TODOS los checks de calidad.

---

## 📋 Hooks Disponibles

### 1. Event Validator
**Archivo**: `backend/event_validator.py`

**Valida**:
- Eventos en UPPER_SNAKE_CASE
- Formato: ENTITY_ACTION_PAST_PARTICIPLE
- Lista canónica de eventos

**Ejemplo**:
```python
# ✅ GOOD
logger.info("CORPUS_INITIALIZED", ...)

# ❌ BAD
logger.info("corpus_initialized", ...)  # lowercase
```

---

### 2. Mutation Validator
**Archivo**: `backend/mutation_validator.py`

**Valida**:
- No funciones con `update_*`, `delete_*`, `modify_*`
- Arquitectura event-sourced
- Append-only compliance

**Ejemplo**:
```python
# ✅ GOOD
def append_interaction(...):
    pass

# ❌ BAD
def update_interaction(...):  # Prohibido
    pass
```

---

### 3. LLM Audit Policy
**Archivo**: `backend/llm_audit_policy.py`

**Valida**:
- Funciones LLM tienen `@require_audit_log`
- Funciones LLM llaman `append_audit_log()`

**Ejemplo**:
```python
# ✅ GOOD
@require_audit_log
def call_claude_api(prompt):
    response = claude.complete(prompt)
    append_audit_log(...)
    return response

# ❌ BAD
def call_claude_api(prompt):  # Sin decorator
    return claude.complete(prompt)
```

---

### 4. LLM Router Policy
**Archivo**: `backend/llm_router_policy.py`

**Valida**:
- No imports directos: `anthropic`, `openai`, `cohere`
- No llamadas directas: `messages.create()`, etc.
- Uso obligatorio de router centralizado

**Ejemplo**:
```python
# ✅ GOOD
from llm_router import route_llm_call
response = route_llm_call(prompt=...)

# ❌ BAD
import anthropic  # Import directo prohibido
client = anthropic.Anthropic()
```

---

### 5. Unit Tests
**Comando**: `python3 -m unittest discover tests/`

**Valida**:
- 199 tests pasan (100%)
- Coverage completo
- Sin tests rotos

**Falla si**:
- Cualquier test falla
- Syntax errors en tests
- Import errors

---

### 6. Commit Message Format
**Archivo**: `scripts/validate_commit_message.py`

**Valida**:
- Conventional Commits format
- Tipos válidos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Mensaje en lowercase (excepto nombres propios)

**Formato**:
```
<type>(<scope>): <message>

feat(security): add LLM audit policy
fix: resolve mutation validator bug
docs: update installation guide
```

**Tipos válidos**:
- `feat`: Nueva feature
- `fix`: Bug fix
- `docs`: Documentación
- `refactor`: Refactoring
- `test`: Tests
- `chore`: Maintenance
- `perf`: Performance
- `ci`: CI/CD
- `build`: Build system

---

## 🧪 Testing Manual de Hooks

### Test Individual

```bash
# Ejecutar solo un hook
pre-commit run event-validator --all-files
pre-commit run mutation-validator --all-files
pre-commit run llm-audit-policy --all-files
pre-commit run unit-tests --all-files
```

### Test Todos los Hooks

```bash
pre-commit run --all-files
```

---

## 📊 Estadísticas

### Hooks Stats

```bash
# Ver historial de ejecuciones
pre-commit gc

# Limpiar cache
pre-commit clean
```

---

## 🔄 Actualizar Hooks

```bash
# Actualizar versiones
pre-commit autoupdate

# Reinstalar
pre-commit uninstall
pre-commit install
```

---

## 🚀 CI/CD Futura (GitHub Actions)

### Workflow Propuesto

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run pre-commit
        run: |
          pip install pre-commit
          pre-commit run --all-files
```

---

## 📈 Benefits

### Antes de Pre-commit Hooks
```
❌ Commits con tests rotos
❌ Violations de políticas
❌ Código inconsistente
❌ Mensajes de commit no estándares
```

### Con Pre-commit Hooks
```
✅ TODOS los commits tienen tests passing
✅ TODAS las políticas enforced
✅ Código consistente
✅ Mensajes de commit estándares
✅ Zero commits rotos en main
```

---

## 🐛 Troubleshooting

### Hook falla pero código es correcto

```bash
# Ver output completo del hook
pre-commit run <hook-id> --verbose

# Ejemplo
pre-commit run mutation-validator --verbose
```

### Hooks no se ejecutan

```bash
# Reinstalar
pre-commit uninstall
pre-commit install
pre-commit install --hook-type commit-msg

# Verificar
ls -la .git/hooks/
```

### Pre-commit muy lento

```bash
# Ejecutar solo en archivos staged
pre-commit run  # (sin --all-files)

# Desactivar hooks pesados temporalmente
# (editar .pre-commit-config.yaml)
```

---

## ✅ Success Criteria

Pre-commit hooks están funcionando si:

1. ✅ Se ejecutan automáticamente en cada commit
2. ✅ Bloquean commits con violations
3. ✅ 199 tests pasan siempre
4. ✅ Mensajes de commit son Conventional Commits
5. ✅ Código cumple políticas de seguridad

---

## 📚 Referencias

- **Pre-commit**: https://pre-commit.com/
- **Conventional Commits**: https://www.conventionalcommits.org/
- **Políticas**:
  - `docs/llm-audit-policy.md`
  - `docs/llm-router-policy.md`
  - `docs/no-mutation-policy.md`
  - `docs/events.md`

---

## 🎯 Status

- **Implementación**: Completa ✅
- **Hooks instalados**: 6 validadores
- **Tests**: 16/16 passing (commit validator)
- **Total tests proyecto**: 199/199 ✅
- **Documentación**: Completa ✅

**Free Intelligence ahora tiene enforcement automático de calidad** 🚀
