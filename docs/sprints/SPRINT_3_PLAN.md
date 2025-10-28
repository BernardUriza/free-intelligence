# Sprint 3 (SPR-2025W45-46) - Abstracción LLM

**Inicio**: 2025-10-28 (AHORA - Bernard tiene 5h disponibles)
**Fin**: 2025-10-29 (1-2 días, flexible)
**Tema**: "LLM Abstraction Layer - Preparación para Offline-First"
**Estado**: EN EJECUCIÓN ✅
**Roadmap**: Este es el **Sprint 1 del Roadmap Offline-First** (ver `ROADMAP_OFFLINE_FIRST.md`)

---

## 🎯 Visión del Sprint (ACTUALIZADA - Offline-First)

Sprint 3 marca la **transición crítica hacia autonomía arquitectónica**. No es solo "hacer funcionar Claude API" - es **diseñar la abstracción que nos libere de cualquier proveedor SaaS**.

**Cambio de Filosofía**:
- ❌ **Antes**: "Implementar Claude API y usarlo"
- ✅ **Ahora**: "Abstraer LLM para que Claude sea solo 1 de N proveedores"

**Objetivo Principal**:
1. **Interfaz única LLM**: `llm.generate()`, `llm.embed()`, `llm.summarize()`
2. **Router inteligente**: Selección de provider (Claude hoy, Ollama mañana)
3. **Policy-driven**: Presupuestos, timeouts, fallback en `fi.policy.yaml`
4. **Future-proof**: Cuando instalemos Ollama (Sprint 3 roadmap), solo cambiar config

**Flujo Objetivo**: **Prompt → Router → [Claude | Ollama | ...] → Corpus → Search/Export**

---

## 📊 Análisis Post-Sprint 2

### Velocity Observada

| Sprint | Horas Est | Horas Reales | Cards | Velocity |
|--------|-----------|--------------|-------|----------|
| Sprint 1 | 18h | 1.05h | 5 | 0.06 |
| Sprint 2 | ~40h | ~8h | 12 | 0.20 |
| **Promedio** | **~29h** | **~4.5h** | **8.5** | **0.13** |

**Observaciones**:
- Velocity mejoró 3.3x entre Sprint 1 y 2
- Sprint 2 se completó en **3/15 días** (20% del tiempo planificado)
- Bernard tiene alta capacidad de ejecución en sesiones concentradas
- Estimaciones consistentemente pesimistas (factor ~5-8x)

### Lecciones Aprendidas

✅ **Funcionó bien**:
- Cards pequeñas y bien definidas (1-5h est)
- Foco en políticas y enforcement (AST validators)
- Tests unitarios comprehensivos
- Documentación inline durante implementación
- Sprint-close automation

⚠️ **Mejorar**:
- Estimar con velocity real (~0.15-0.20, no 0.06)
- Menos buffer time (Bernard ejecuta rápido)
- Definir criterios de aceptación más específicos
- Testing E2E automatizado (no solo unit tests)

---

## 🏗️ Arquitectura Objetivo Sprint 3

```
┌─────────────────────────────────────────┐
│  Capa 5: User Interface (CLI)          │
│  ✅ Comandos básicos                    │
│  🎯 NEW: fi chat, fi search, fi export │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Capa 4: LLM Integration                │
│  🎯 NEW: LLM Router (anthropic)         │
│  🎯 NEW: Auto-audit logging             │
│  🎯 NEW: Cost tracking                  │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Capa 3: Data Operations                │
│  ✅ Append interaction (Sprint 1)       │
│  🎯 NEW: Semantic search (embeddings)   │
│  🎯 NEW: Export engines (MD, JSON)      │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Capa 2: Foundation (Sprint 1+2)        │
│  ✅ HDF5 Schema, Audit Logs, Policies   │
└─────────────────────────────────────────┘
```

---

## 📋 Cards Propuestas (Tier System)

### Tier 1: LLM Abstraction Layer (CRÍTICO) - 3 cards

#### FI-CORE-FEAT-001 - LLM Router con Abstracción Multi-Provider
**Prioridad**: P0 | **Estimado**: 6h → ~1.2h real

**Descripción**:
Implementar router LLM con **abstracción provider-agnostic**. Claude es provider inicial, pero diseño permite agregar Ollama/OpenAI sin cambiar API.

**Arquitectura**:
```python
# Interfaz abstracta
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        pass

# Implementaciones
class ClaudeProvider(LLMProvider):
    # Usa anthropic SDK

class OllamaProvider(LLMProvider):
    # Usa requests a OLLAMA_BASE_URL (futuro)

class OpenAIProvider(LLMProvider):
    # Usa openai SDK (futuro)

# Router
def get_provider(provider_name: str) -> LLMProvider:
    if provider_name == "claude":
        return ClaudeProvider()
    elif provider_name == "ollama":
        return OllamaProvider()
    # ...
```

**Criterios de Aceptación**:
- [ ] `backend/llm_router.py` con:
  - [ ] `LLMProvider` abstract class
  - [ ] `ClaudeProvider` implementation
  - [ ] `get_provider(name)` factory
  - [ ] `llm_generate(prompt, provider, **kwargs) → str`
  - [ ] `llm_embed(text, provider) → ndarray`
- [ ] `ClaudeProvider` usa `anthropic` library
- [ ] Auto-logging en `/audit_logs/` con `@require_audit_log`
- [ ] Manejo de errors: rate limits, API down, timeout
- [ ] Environment variable `CLAUDE_API_KEY` desde `.env`
- [ ] Tests unitarios (15+ tests):
  - [ ] Mocks de ClaudeProvider
  - [ ] Factory pattern
  - [ ] Error handling
  - [ ] Audit logging
- [ ] Cost tracking: tokens used, $ estimado

**Dependencias**:
- Requiere API key de Claude (Bernard configurará en `.env`)
- Librería: `anthropic>=0.8.0`

**Notas Importantes**:
- 🎯 **NO hardcodear Claude** - todo debe pasar por abstracción
- 🎯 Provider selection desde config (no hardcoded)
- 🎯 Easy to add Ollama en Sprint 3 del roadmap

---

#### FI-CORE-FEAT-002 - CLI Interactivo `fi chat`
**Prioridad**: P0 | **Estimado**: 4h → ~0.8h real

**Descripción**:
Comando `fi chat` para interacción directa con LLM, guardando automáticamente en corpus.

**Criterios de Aceptación**:
- [ ] CLI script `scripts/fi_cli.py` con subcomando `chat`
- [ ] Interfaz: `fi chat [--model MODEL] [--session SESSION_ID]`
- [ ] Flujo: Prompt → LLM Router → Append to HDF5
- [ ] Muestra respuesta en terminal con syntax highlighting
- [ ] Auto-genera `session_id` si no se provee
- [ ] Muestra stats al final: tokens used, cost estimado
- [ ] Tests de integración (E2E con mock LLM)

**Ejemplo de uso**:
```bash
$ fi chat --model claude-3-5-sonnet-20241022
> ¿Qué es Free Intelligence?
[Respuesta del LLM]
---
Tokens: 150 | Cost: $0.003 | Session: session_20251029_143022
```

---

#### FI-CONFIG-FEAT-002 - fi.policy.yaml (LLM Policies)
**Prioridad**: P0 | **Estimado**: 3h → ~0.6h real

**Descripción**:
Archivo de configuración para políticas de LLM: presupuestos, timeouts, fallback, provider selection.

**Schema YAML**:
```yaml
llm:
  primary_provider: "claude"      # claude | ollama | openai
  fallback_provider: "claude"     # Si primary falla
  enable_offline: false           # true cuando Ollama esté ready

  providers:
    claude:
      model: "claude-3-5-sonnet-20241022"
      api_key_env: "CLAUDE_API_KEY"
      timeout_seconds: 30
      max_tokens: 4096
      temperature: 0.7

    ollama:
      base_url: "http://192.168.1.100:11434"  # NAS IP
      model: "qwen2:7b-instruct-q4_0"
      timeout_seconds: 12
      max_tokens: 2048

  budgets:
    max_cost_per_day: 10.0         # USD
    max_requests_per_hour: 100
    alert_threshold: 0.8           # Alert at 80% budget

  fallback_rules:
    - condition: "timeout"
      action: "use_fallback"
    - condition: "rate_limit"
      action: "exponential_backoff"
    - condition: "api_error"
      action: "use_fallback"

  logging:
    log_all_prompts: true
    log_all_responses: true
    log_token_usage: true
```

**Criterios de Aceptación**:
- [ ] `config/fi.policy.yaml` creado con schema completo
- [ ] `backend/policy_loader.py` con:
  - [ ] `load_llm_policy() → dict`
  - [ ] Validación de schema (required fields)
  - [ ] Defaults si faltan valores
- [ ] Integración con `llm_router.py`:
  - [ ] Leer `primary_provider` desde policy
  - [ ] Aplicar timeouts, max_tokens
  - [ ] Verificar budgets antes de llamada
- [ ] Tests unitarios (10+ tests):
  - [ ] Load valid policy
  - [ ] Missing fields → defaults
  - [ ] Invalid provider → error
  - [ ] Budget enforcement
- [ ] Documentación: docs/llm-policy.md

**Notas**:
- 🎯 Policy-driven design = easy to change provider sin tocar código
- 🎯 Budgets previenen costos runaway
- 🎯 Fallback rules para resiliencia

---

#### FI-DATA-FEAT-002 - Append Interaction End-to-End
**Prioridad**: P0 | **Estimado**: 2h → ~0.4h real

**Descripción**:
Completar flujo de `append_interaction()` con embeddings automáticos usando provider de LLM.

**Criterios de Aceptación**:
- [ ] `corpus_ops.append_interaction()` recibe prompt + response
- [ ] Embedding generation:
  - [ ] Llamar a `llm_embed(prompt + response)` usando provider
  - [ ] Si provider no soporta embed → usar sentence-transformers local
- [ ] Llama a `append_embedding()` automáticamente
- [ ] Logging de INTERACTION_APPENDED + EMBEDDING_APPENDED
- [ ] Tests con verificación de corpus stats incrementales
- [ ] Documentación de pipeline completo

**Notas**:
- Ya existe esqueleto en Sprint 1, solo falta integrar con LLM router
- Sentence-transformers como fallback si provider no tiene embeddings

---

### Tier 2: Search & Export (IMPORTANTE) - 3 cards

#### FI-SEARCH-FEAT-001 - Buscador Semántico Básico
**Prioridad**: P1 | **Estimado**: 4h → ~0.8h real

**Descripción**:
Búsqueda semántica sobre embeddings con cosine similarity.

**Criterios de Aceptación**:
- [ ] `backend/search.py` con función `semantic_search(query, top_k=5)`
- [ ] Genera embedding de query
- [ ] Calcula cosine similarity vs todos los embeddings en corpus
- [ ] Retorna top_k interactions con scores
- [ ] CLI: `fi search "query text"`
- [ ] Tests con corpus sintético (10 interactions)

---

#### FI-EXPORT-FEAT-001 - Exportador Markdown
**Prioridad**: P1 | **Estimado**: 3h → ~0.6h real

**Descripción**:
Exportar interacciones a Markdown con manifest obligatorio (Export Policy).

**Criterios de Aceptación**:
- [ ] `backend/exporter.py` con `export_to_markdown(filters, output_path)`
- [ ] Genera manifest con `export_policy.create_export_manifest()`
- [ ] Formato Markdown: `# Session XXXX\n## Interaction 1\n**Prompt**: ...\n**Response**: ...`
- [ ] Guarda manifest JSON junto al .md
- [ ] Append audit log (EXPORT_COMPLETED)
- [ ] CLI: `fi export markdown --session SESSION_ID --output exports/`
- [ ] Tests de formato y manifest validation

---

#### FI-EXPORT-FEAT-002 - Exportador JSON
**Prioridad**: P2 | **Estimado**: 2h → ~0.4h real

**Descripción**:
Exportar interacciones a JSON estructurado.

**Criterios de Aceptación**:
- [ ] `exporter.py` con `export_to_json(filters, output_path)`
- [ ] Schema JSON:
```json
{
  "export_id": "...",
  "timestamp": "...",
  "interactions": [
    {
      "interaction_id": "...",
      "session_id": "...",
      "timestamp": "...",
      "prompt": "...",
      "response": "...",
      "model": "...",
      "tokens": 123
    }
  ]
}
```
- [ ] Manifest obligatorio
- [ ] CLI: `fi export json`
- [ ] Tests JSON schema validation

---

### Tier 3: Observability & Polish (NICE TO HAVE) - 2 cards

#### FI-CLI-FEAT-001 - CLI de Gestión Completa
**Prioridad**: P2 | **Estimado**: 3h → ~0.6h real

**Descripción**:
Unificar comandos CLI bajo `fi` tool.

**Criterios de Aceptación**:
- [ ] Script `fi` en raíz del proyecto (Python)
- [ ] Subcomandos: chat, search, export, stats, init, validate
- [ ] Help integrado: `fi --help`, `fi chat --help`
- [ ] Tests de CLI con subprocess

---

#### FI-DATA-FEAT-008 - Corpus Stats Dashboard
**Prioridad**: P2 | **Estimado**: 2h → ~0.4h real

**Descripción**:
CLI para ver estadísticas del corpus.

**Criterios de Aceptación**:
- [ ] CLI: `fi stats [--detailed]`
- [ ] Muestra: Total interactions, sessions, embeddings, corpus size (MB)
- [ ] Breakdown por model used
- [ ] Audit logs stats (operations by type, last 7 days)
- [ ] Tests con corpus sintético

---

## 📊 Resumen de Carga

| Tier | Cards | Est Original | Est Real (vel 0.20) | Prioridad |
|------|-------|--------------|---------------------|-----------|
| **Tier 1** | 3 | 12h | ~2.4h | P0 (Crítico) |
| **Tier 2** | 3 | 9h | ~1.8h | P1 (Importante) |
| **Tier 3** | 2 | 5h | ~1h | P2 (Nice to have) |
| **Total** | **8** | **26h** | **~5.2h** | - |

**Capacidad Sprint 3**: 60h planificadas → **~10-12h reales** con velocity 0.15-0.20

**Conclusión**: Scope es conservador. **Tier 1+2 (6 cards) son el MVP**. Tier 3 es bonus.

---

## 🎯 Definition of Done (DoD)

Antes de mover card a "Done":

1. **Implementación**:
   - [ ] Código implementado y funcional
   - [ ] Integrado con políticas existentes (append-only, audit, etc.)
   - [ ] Logs con eventos canónicos UPPER_SNAKE_CASE

2. **Testing**:
   - [ ] Tests unitarios (cobertura >80%)
   - [ ] Tests de integración para flujos E2E
   - [ ] Validadores AST ejecutados sin violaciones

3. **Documentación**:
   - [ ] Docstrings completos en funciones públicas
   - [ ] README.md actualizado si es feature visible
   - [ ] docs/ actualizado si hay nueva política o convención

4. **Validación**:
   - [ ] Pre-commit hooks pasan (6 validadores)
   - [ ] Tests completos pasan (259+ tests)
   - [ ] Demo manual ejecutado exitosamente

---

## 🔐 Requisitos Previos

### Environment Setup

Bernard deberá:
1. Crear archivo `.env` en raíz (gitignored):
   ```bash
   CLAUDE_API_KEY=sk-ant-api03-...
   ```
2. Instalar dependencias adicionales:
   ```bash
   pip3 install anthropic>=0.8.0 sentence-transformers>=2.2.0
   ```
3. Actualizar `requirements.txt` con versiones pinned

### API Key Security

⚠️ **CRÍTICO**:
- ❌ NUNCA commitear `.env`
- ❌ NUNCA poner API key en código
- ✅ Verificar `.gitignore` incluye `.env`
- ✅ Usar `os.getenv("CLAUDE_API_KEY")` siempre

---

## 📅 Timeline Sugerido (Flexible)

| Días | Objetivo | Cards |
|------|----------|-------|
| Día 1-2 | LLM Integration | FI-CORE-FEAT-001, FI-CORE-FEAT-002 |
| Día 3 | Data Operations | FI-DATA-FEAT-002 |
| Día 4-5 | Search & Export | FI-SEARCH-FEAT-001, FI-EXPORT-FEAT-001 |
| Día 6 | Polish | FI-EXPORT-FEAT-002 (opcional) |
| Día 7 | CLI Unification | FI-CLI-FEAT-001 (opcional) |

**Nota**: Con velocity 0.20, Tier 1+2 se completa en **~2-3 días reales** si hay foco.

---

## 🚀 Siguientes Fases (Post-Sprint 3)

### Sprint 4: UI & Visualization
- Dashboard local con timeline
- Visor de interacciones
- Gráficos de uso y costos

### Sprint 5: Advanced Features
- Context window management
- Thread tracking
- Multi-model support (GPT-4, etc.)

### Sprint 6: Deployment & Scaling
- NAS deployment scripts
- Backup automation avanzado
- Network isolation (firewall rules)

---

## 🤔 Decisiones Pendientes (para Bernard)

1. **¿Iniciar Sprint 3 ahora o tomar break?**
   - Sprint 2 completado 11-12 días adelante del plan
   - Opción: Descanso de 1-2 semanas antes de Sprint 3

2. **¿Qué cards de Tier 3 incluir?**
   - FI-CLI-FEAT-001 unifica comandos (recomendado)
   - FI-DATA-FEAT-008 stats dashboard (visual, nice to have)

3. **¿Model default para Sprint 3?**
   - `claude-3-5-sonnet-20241022` (balance cost/calidad)
   - O `claude-3-5-haiku` para desarrollo (más barato)

4. **¿Testing strategy?**
   - ¿Usar mocks de anthropic o hacer calls reales (con cost)?
   - Recomendación: Mocks para unit tests, 1-2 calls reales para E2E

---

## ✅ Checklist de Inicio Sprint 3

Antes de empezar:
- [ ] Bernard aprueba este plan (revisar scope, timeline)
- [ ] API key de Claude configurada en `.env`
- [ ] Dependencies instaladas: `anthropic`, `sentence-transformers`
- [ ] `requirements.txt` actualizado con nuevas deps
- [ ] `.gitignore` verificado (incluye `.env`)
- [ ] Crear cards en Trello (To Do Sprint column)
- [ ] Crear SPRINT_3_TRACKER.md (basado en template Sprint 2)
- [ ] Tag v0.3.0 verificado (ya existe)

---

**Última actualización**: 2025-10-28
**Estado**: Borrador - Pendiente aprobación Bernard
**Siguiente acción**: Bernard revisa plan → Aprueba/ajusta → Inicia Sprint 3

---

