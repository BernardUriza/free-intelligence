# LLM Audit Policy - Free Intelligence

**Fecha**: 2025-10-25
**Task**: FI-CORE-FEAT-004
**Sprint**: SPR-2025W44 (Sprint 2)
**Autor**: Bernard Uriza Orozco

---

## 🎯 Propósito

**TODA** llamada a LLM debe estar auditada. Sin excepciones.

Esta política garantiza:
- **Trazabilidad completa**: Cada inferencia queda registrada
- **Non-repudiation**: Logs inmutables en `/audit_logs/`
- **Compliance**: Base para análisis de uso y costos
- **Seguridad**: Detección de uso indebido o anomalías

---

## 📋 Política

### Reglas Obligatorias

1. ✅ **Toda función LLM debe tener `@require_audit_log`**
   - Decorator marca la función como requiriendo audit
   - Validación estática detecta funciones sin decorator

2. ✅ **Toda función LLM debe llamar `append_audit_log()`**
   - Registro en `/audit_logs/` antes de retornar
   - Incluir: operation, user_id, payload_hash, result_hash

3. ❌ **Prohibido**: LLM calls sin decorator
4. ❌ **Prohibido**: LLM calls sin audit log

---

## 🔧 Implementación

### 1. Decorator `@require_audit_log`

```python
from llm_audit_policy import require_audit_log
from audit_logs import append_audit_log

@require_audit_log
def call_claude_api(prompt: str, user_id: str) -> str:
    """
    Llamada a Claude API con audit logging.

    DEBE llamar append_audit_log() antes de retornar.
    """
    # 1. Ejecutar llamada a LLM
    response = claude_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.content[0].text

    # 2. OBLIGATORIO: Registrar en audit_logs
    append_audit_log(
        corpus_path="storage/corpus.h5",
        operation="CLAUDE_API_CALLED",
        user_id=user_id,
        endpoint="call_claude_api",
        payload=prompt,
        result=result,
        status="SUCCESS"
    )

    # 3. Retornar resultado
    return result
```

### 2. Detección de Funciones LLM

El validador detecta automáticamente funciones que sugieren llamadas a LLM:

**Prefixes detectados**:
- `call_*` (call_claude_api, call_openai)
- `invoke_*` (invoke_model, invoke_llm)
- `query_*` (query_llm, query_api)
- `generate_*` (generate_text, generate_completion)
- `infer_*`, `predict_*`, `complete_*`

**Keywords detectados**:
- `*claude*`, `*anthropic*`, `*openai*`, `*gpt*`
- `*llm*`, `*model*`, `*ai_*`, `*ml_*`

**Ejemplo**:
```python
# ❌ VIOLATION: Sin decorator, sin audit
def call_claude_api(prompt):
    return claude.complete(prompt)

# ❌ VIOLATION: Con decorator pero sin audit call
@require_audit_log
def invoke_llm(prompt):
    return llm.generate(prompt)

# ✅ COMPLIANT: Decorator + audit call
@require_audit_log
def query_llm(prompt):
    result = llm.query(prompt)
    append_audit_log(...)
    return result
```

---

## 🔍 Validación

### Validación Estática (AST-based)

```bash
# Escanear directorio en busca de violaciones
python3 backend/llm_audit_policy.py scan backend/

# Validar codebase (retorna exit code 0/1)
python3 backend/llm_audit_policy.py validate backend/
```

**Output esperado** (sin violaciones):

```
✅ LLM AUDIT VALIDATION PASSED
   All LLM functions comply with audit policy
   Total LLM functions: 3
   All have @require_audit_log and call append_audit_log()
```

**Output con violaciones**:

```
❌ LLM AUDIT VIOLATIONS DETECTED

📁 backend/llm_client.py
   ❌ call_claude_api (line 45)
      • Missing @require_audit_log decorator
      • Missing append_audit_log() call

Total violations: 1

Policy: ALL LLM functions must:
  1. Have @require_audit_log decorator
  2. Call append_audit_log() before returning
```

### Pre-commit Hook (Futuro)

En **FI-CICD-FEAT-001** se integrará en pipeline:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: llm-audit-validation
      name: LLM Audit Policy Validator
      entry: python3 backend/llm_audit_policy.py validate backend/
      language: system
      pass_filenames: false
```

---

## 📊 Eventos de Audit Log

Toda función LLM debe registrar al menos estos campos:

```python
append_audit_log(
    corpus_path="storage/corpus.h5",
    operation="CLAUDE_API_CALLED",      # Nombre de operación (UPPER_SNAKE_CASE)
    user_id="user_hash_prefix",         # Identificador de usuario
    endpoint="call_claude_api",         # Nombre de función
    payload=prompt,                     # Input (se hará hash SHA256)
    result=response,                    # Output (se hará hash SHA256)
    status="SUCCESS",                   # SUCCESS, FAILED, BLOCKED
    metadata={"model": "claude-3-5-sonnet", "tokens": 1234}  # Opcional
)
```

**Campos en `/audit_logs/`**:
- `audit_id`: UUID v4
- `timestamp`: ISO 8601 con timezone
- `operation`: Nombre de operación
- `user_id`: Identificador de usuario
- `endpoint`: Función/endpoint
- `payload_hash`: SHA256 de input
- `result_hash`: SHA256 de output
- `status`: SUCCESS, FAILED, BLOCKED
- `metadata`: JSON opcional

---

## 🚫 Anti-Patterns

### ❌ BAD: LLM call sin audit

```python
def generate_response(prompt):
    # ❌ Sin decorator, sin audit log
    return llm.complete(prompt)
```

### ❌ BAD: Decorator pero sin audit call

```python
@require_audit_log
def call_api(prompt):
    # ❌ Tiene decorator pero no llama append_audit_log()
    return api.query(prompt)
```

### ❌ BAD: Audit condicional

```python
@require_audit_log
def invoke_model(prompt, log=True):
    result = model.generate(prompt)

    # ❌ Audit condicional no permitido
    if log:
        append_audit_log(...)

    return result
```

### ✅ GOOD: Audit siempre

```python
@require_audit_log
def call_claude(prompt, user_id):
    result = claude.complete(prompt)

    # ✅ SIEMPRE registrar, sin condicionales
    append_audit_log(
        operation="CLAUDE_API_CALLED",
        user_id=user_id,
        payload=prompt,
        result=result,
        status="SUCCESS"
    )

    return result
```

---

## 🧪 Tests

### Cobertura

- ✅ Decorator marca función correctamente
- ✅ Detección de nombres de función LLM
- ✅ Detección de decorator en AST
- ✅ Detección de `append_audit_log()` call
- ✅ Escaneo de archivos individuales
- ✅ Escaneo recursivo de directorios
- ✅ Validación de codebase completo
- ✅ Manejo de syntax errors

**Total**: 27 tests passing (0.005s)

```bash
# Ejecutar tests
python3 -m unittest tests.test_llm_audit_policy -v
```

---

## 📈 Roadmap

### Fase 1 (Actual): Detección Estática ✅

- Decorator `@require_audit_log` como marker
- Validador AST para detección
- CLI para escaneo de código
- Tests completos

### Fase 2 (Futuro): Runtime Validation

- Decorator verifica que se llamó `append_audit_log()`
- Raise `LLMAuditViolation` si no se auditó
- Context manager para auto-audit
- Métricas de compliance en tiempo real

### Fase 3 (Futuro): Pre-commit Integration

- Hook que bloquea commits con violaciones
- Integration con CI/CD pipeline
- Dashboard de compliance

---

## 🔗 Referencias

- **Audit Logs**: `backend/audit_logs.py` (FI-SEC-FEAT-003)
- **Append-Only Policy**: `docs/no-mutation-policy.md` (FI-DATA-FIX-001)
- **Event Validator**: `backend/event_validator.py` (FI-API-FEAT-001)

---

## ✅ Status Actual

- **Implementación**: Completa ✅
- **Tests**: 27/27 passing ✅
- **Documentación**: Completa ✅
- **Validación**: Backend actual 0 violaciones ✅

**Próximo paso**: Integrar en pre-commit hooks (FI-CICD-FEAT-001)
