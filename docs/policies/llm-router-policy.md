# LLM Router Policy - Free Intelligence

**Fecha**: 2025-10-25
**Task**: FI-CORE-FIX-001
**Sprint**: SPR-2025W44 (Sprint 2)
**Autor**: Bernard Uriza Orozco

---

## 🎯 Propósito

**TODA** llamada a LLM debe pasar por router centralizado. Sin excepciones.

Esta política garantiza:
- **Control centralizado**: Un solo punto de entrada para LLM calls
- **Logging automático**: El router maneja audit logs
- **Rate limiting**: Fácil agregar throttling/quotas
- **Model switching**: Cambiar providers sin tocar código
- **Cost tracking**: Monitoreo centralizado de uso

---

## 📋 Política

### Reglas Obligatorias

1. ❌ **PROHIBIDO**: Imports directos de librerías LLM
   ```python
   # ❌ PROHIBIDO
   import anthropic
   from openai import OpenAI
   import cohere
   ```

2. ❌ **PROHIBIDO**: Llamadas directas a APIs
   ```python
   # ❌ PROHIBIDO
   client.messages.create(...)
   openai.ChatCompletion.create(...)
   cohere.generate(...)
   ```

3. ✅ **OBLIGATORIO**: Uso de router centralizado
   ```python
   # ✅ PERMITIDO
   from llm_router import route_llm_call
   response = route_llm_call(prompt=..., model=...)
   ```

---

## 🔧 Implementación

### Router Centralizado (Futuro)

El módulo `llm_router.py` (a implementar en FI-CORE-FEAT-006) manejará:

```python
# backend/llm_router.py (futuro)
from llm_audit_policy import require_audit_log
from audit_logs import append_audit_log

@require_audit_log
def route_llm_call(
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    user_id: str = None,
    **kwargs
) -> str:
    """
    Router centralizado para TODAS las llamadas a LLM.

    Features:
    - Audit logging automático
    - Rate limiting
    - Model switching
    - Cost tracking
    - Error handling
    """
    # 1. Validar inputs
    # 2. Seleccionar provider (anthropic, openai, etc.)
    # 3. Ejecutar llamada
    # 4. Registrar en audit_logs
    # 5. Retornar resultado

    # AUDIT LOG (automático)
    append_audit_log(
        operation="LLM_CALL_ROUTED",
        user_id=user_id,
        endpoint="route_llm_call",
        payload=prompt,
        result=response,
        status="SUCCESS",
        metadata={"model": model, "tokens": token_count}
    )

    return response
```

### Uso en Aplicación

```python
# ✅ CORRECTO: Via router
from llm_router import route_llm_call

def generate_response(user_prompt: str, user_id: str) -> str:
    """
    Genera respuesta usando LLM via router.

    No necesita @require_audit_log porque el router
    ya lo maneja automáticamente.
    """
    response = route_llm_call(
        prompt=user_prompt,
        model="claude-3-5-sonnet-20241022",
        user_id=user_id
    )
    return response
```

---

## 🚫 Librerías Prohibidas

El validador detecta automáticamente imports de:

```python
FORBIDDEN_IMPORTS = {
    'anthropic',           # Anthropic Claude
    'openai',              # OpenAI GPT
    'cohere',              # Cohere
    'google.generativeai', # Google Gemini
    'huggingface_hub',     # HuggingFace
    'transformers',        # HuggingFace Transformers
}
```

### Llamadas Prohibidas

```python
FORBIDDEN_CALL_PATTERNS = {
    'messages.create',           # anthropic
    'chat.completions.create',   # openai
    'ChatCompletion.create',     # openai legacy
    'Completion.create',         # openai legacy
    'generate',                  # cohere, huggingface
    'generate_content',          # google
}
```

---

## 🔍 Validación

### Validación Estática (AST-based)

```bash
# Escanear directorio en busca de violaciones
python3 backend/llm_router_policy.py scan backend/

# Validar codebase (retorna exit code 0/1)
python3 backend/llm_router_policy.py validate backend/
```

**Output esperado** (sin violaciones):

```
✅ ROUTER POLICY VALIDATION PASSED
   No direct LLM API calls detected
   All LLM interactions must use centralized router
```

**Output con violaciones**:

```
❌ ROUTER POLICY VIOLATIONS DETECTED

📁 backend/llm_client.py
   🚫 Forbidden Imports:
      • Direct import of LLM library: 'anthropic'

   🚫 Direct API Calls:
      • Line 45: Direct LLM API call: 'messages.create'

Total violations: 2

Policy: ALL LLM calls must:
  1. Use centralized router (llm_router module)
  2. NO direct imports of anthropic, openai, etc.
  3. NO direct API calls (messages.create, etc.)
```

### Pre-commit Hook (Futuro)

En **FI-CICD-FEAT-001** se integrará en pipeline:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: llm-router-validation
      name: LLM Router Policy Validator
      entry: python3 backend/llm_router_policy.py validate backend/
      language: system
      pass_filenames: false
```

---

## 🎨 Patrones de Uso

### ❌ BAD: Import y llamada directa

```python
import anthropic

def call_claude(prompt):
    # ❌ Import directo + llamada directa
    client = anthropic.Anthropic(api_key="...")
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

### ❌ BAD: Solo import directo

```python
from openai import OpenAI

def call_openai(prompt):
    # ❌ Aunque uses router después, el import está prohibido
    client = OpenAI()
    return client.chat.completions.create(...)
```

### ✅ GOOD: Via router

```python
from llm_router import route_llm_call

def generate_text(prompt, user_id):
    # ✅ Router centralizado
    # Audit logging automático
    # Rate limiting automático
    # Cost tracking automático
    return route_llm_call(
        prompt=prompt,
        model="claude-3-5-sonnet-20241022",
        user_id=user_id
    )
```

### ✅ GOOD: Con configuración

```python
from llm_router import route_llm_call, LLMConfig

def generate_with_config(prompt, user_id):
    # ✅ Con configuración avanzada
    config = LLMConfig(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        temperature=0.7
    )

    return route_llm_call(
        prompt=prompt,
        user_id=user_id,
        config=config
    )
```

---

## 🧪 Tests

### Cobertura

- ✅ Detección de imports prohibidos (anthropic, openai, etc.)
- ✅ Detección de llamadas directas a APIs
- ✅ Extracción de imports con `from` y `import`
- ✅ Extracción de attribute calls anidados
- ✅ Escaneo de archivos individuales
- ✅ Escaneo recursivo de directorios
- ✅ Validación de codebase completo
- ✅ Manejo de syntax errors

**Total**: 27 tests passing (0.006s)

```bash
# Ejecutar tests
python3 -m unittest tests.test_llm_router_policy -v
```

---

## 📊 Beneficios del Router

### 1. Control Centralizado

```
┌─────────────────────────────────────┐
│  Application Code                   │
│  ├─ Feature A: route_llm_call()     │
│  ├─ Feature B: route_llm_call()     │
│  └─ Feature C: route_llm_call()     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  LLM Router (single entry point)    │
│  ├─ Audit logging                   │
│  ├─ Rate limiting                   │
│  ├─ Cost tracking                   │
│  ├─ Error handling                  │
│  └─ Model switching                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  LLM Providers                      │
│  ├─ Anthropic (Claude)              │
│  ├─ OpenAI (GPT)                    │
│  └─ Cohere                          │
└─────────────────────────────────────┘
```

### 2. Cambio de Provider sin Código

```python
# Cambiar de Claude a GPT sin tocar código de aplicación
# Solo modificar router:

# backend/llm_router.py
def route_llm_call(prompt, model="gpt-4", **kwargs):
    # Cambio automático sin refactor
    if model.startswith("claude"):
        return _call_anthropic(prompt, model, **kwargs)
    elif model.startswith("gpt"):
        return _call_openai(prompt, model, **kwargs)
```

### 3. Audit Trail Automático

```python
# ANTES (sin router): Cada función debe hacer append_audit_log()
@require_audit_log
def call_claude(prompt):
    response = client.messages.create(...)
    append_audit_log(...)  # ❌ Fácil olvidar
    return response

# DESPUÉS (con router): Router lo hace automático
def generate_text(prompt):
    return route_llm_call(prompt=prompt)  # ✅ Audit automático
```

### 4. Rate Limiting Global

```python
# Router puede implementar throttling global
def route_llm_call(prompt, model, user_id, **kwargs):
    # Check rate limit
    if not rate_limiter.check(user_id):
        raise RateLimitExceeded(f"User {user_id} exceeded quota")

    # Proceed with call
    return _execute_llm_call(...)
```

---

## 📈 Roadmap

### Fase 1 (Actual): Detección Estática ✅

- Validador AST para imports y calls
- CLI para escaneo de código
- Tests completos
- Documentación

### Fase 2 (Futuro): Implementación de Router

- Módulo `llm_router.py` (FI-CORE-FEAT-006)
- Support para Anthropic, OpenAI, Cohere
- Audit logging automático
- Rate limiting básico

### Fase 3 (Futuro): Features Avanzadas

- Cost tracking en tiempo real
- Model fallback automático
- Caching de responses
- Streaming support
- Retry logic con backoff

---

## 🔗 Referencias

- **LLM Audit Policy**: `docs/llm-audit-policy.md` (FI-CORE-FEAT-004)
- **Audit Logs**: `backend/audit_logs.py` (FI-SEC-FEAT-003)
- **Event Validator**: `backend/event_validator.py` (FI-API-FEAT-001)

---

## ✅ Status Actual

- **Implementación**: Validador completo ✅
- **Tests**: 27/27 passing ✅
- **Documentación**: Completa ✅
- **Validación**: Backend actual 0 violaciones ✅

**Próximo paso**: Implementar `llm_router.py` en FI-CORE-FEAT-006 (Sprint futuro)

**Nota**: Por ahora el backend NO tiene llamadas a LLM (infraestructura pura), por lo que la validación pasa. Cuando se implemente FI-CORE-FEAT-001 (Middleware LLM), DEBE usar el router.
