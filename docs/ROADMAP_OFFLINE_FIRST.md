# Free Intelligence - Roadmap Offline-First

**Visión**: Transición de Claude API → LLM Offline (chino) en NAS
**Objetivo**: Costo ↓≥60%, 0 PHI externo, estabilidad 99.5%, rollback one-switch
**Timeline**: 6 sprints (Sprint 0 → Sprint 6)

---

## 🎯 Filosofía Core

**Autonomía Arquitectónica**: No depender de SaaS para pensar.

**Estrategia de Migración**:
```
Sprint 0-2: Claude SDK (MVP rápido, validación)
Sprint 3-4: LLM offline (Qwen2/DeepSeek en NAS)
Sprint 5-6: Optimización y escala (calidad ≤10% Δ vs Claude)
```

---

## 📋 Roadmap Detallado

### Sprint 0: FI-base (Fundación con Claude) ✅ PARCIALMENTE

**Objetivo**: Ingesta A/V, manifest+SHA256, router LLM v0 → Claude SDK

**Cards Completadas** (Sprints 1-2):
- ✅ Manifest + SHA256 (Export Policy)
- ✅ Audit logs + append-only
- ✅ Políticas de seguridad
- ✅ Redacción local (claude.md bitácora)

**Cards Pendientes**:
- ⏳ **FI-CORE-FEAT-001**: Router LLM v0 → Claude SDK (CLAUDE_API_KEY)
- ⏳ **FI-INGRESS-FEAT-001**: Ingesta A/V (audio/video transcription)
- ⏳ **FI-UI-FEAT-001**: Panel básico (dashboard local)

**Política de Egreso**:
- Egreso = DENY salvo `/llm` (solo llamadas LLM permitidas)
- Todo lo demás: procesamiento local

---

### Sprint 1: Abstracción LLM (Interfaz Única) 🎯 PRÓXIMO

**Objetivo**: Interfaz única para cualquier LLM (Claude hoy, Ollama mañana)

**Cards**:

1. **FI-CORE-FEAT-002** - Interfaz Abstracta LLM
   - `llm.generate(prompt, **kwargs) → str`
   - `llm.embed(text) → ndarray`
   - `llm.summarize(text, max_tokens) → str`
   - Backend: `LLMProvider` enum (CLAUDE, OLLAMA, OPENAI)
   - Router selecciona provider según config

2. **FI-CONFIG-FEAT-002** - fi.policy.yaml
   - Presupuestos: `max_cost_per_day`, `max_tokens_per_request`
   - Timeouts: `llm_timeout_seconds`, `embedding_timeout_seconds`
   - Fallback: `fallback_provider` (si primary falla)
   - Logging: `log_level`, `log_all_prompts`

3. **FI-PROMPT-FEAT-001** - Prompt Templates Versionados
   - Templates en `prompts/` con versionamiento
   - Formato: `{template_name}-v{version}.yaml`
   - Variables: `{{user_input}}`, `{{context}}`
   - Metadata: descripción, author, changelog

**Tests**:
- Unit tests con mocks de cada provider
- Integration tests con Claude (real API, ≤10 calls)

---

### Sprint 2: Evaluación (Golden Set) 📊

**Objetivo**: Medir calidad de Claude (baseline para comparar offline LLM)

**Cards**:

1. **FI-EVAL-FEAT-001** - Golden Set Creation
   - 50 prompts de telemedicina (NO-PHI)
   - Categorías: diagnóstico general, farmacología, síntomas
   - Ground truth: respuestas esperadas (revisadas por médico)
   - Formato HDF5: `/eval/golden_set/`

2. **FI-EVAL-FEAT-002** - Métricas de Evaluación
   - **Adecuación**: BLEU score, ROUGE-L vs ground truth
   - **Factualidad**: Hallucination detection (heurística)
   - **Latencia**: p50, p95, p99 (ms)
   - **Costo**: $ per request, $ per 1K tokens

3. **FI-EVAL-FEAT-003** - Dashboard de Evaluación
   - Resultados en `/eval/results.h5`
   - Visualización: gráficos de calidad, latencia, costo
   - Comparación provider A vs B

**Baseline Claude**:
- Ejecutar golden set con Claude 3.5 Sonnet
- Guardar métricas como referencia

---

### Sprint 3: Offline CPU (LLM Chino en NAS) 🇨🇳

**Objetivo**: Instalar Ollama en NAS/DELL con modelo chino cuantizado

**Cards**:

1. **FI-INFRA-FEAT-001** - Ollama en NAS
   - Instalar Ollama en Synology RS4021xs+ o DELL server
   - Configurar OLLAMA_BASE_URL en router
   - Health check: `/api/tags` endpoint
   - Tests de conectividad desde FI

2. **FI-MODEL-FEAT-001** - Deploy Modelo Chino
   - **Opción A**: Qwen2-7B (q4_0) - 4.1GB RAM
   - **Opción B**: DeepSeek-R1-Distill-7B (q4_0) - 4.3GB RAM
   - Pull model: `ollama pull qwen2:7b-instruct-q4_0`
   - Benchmark: latencia en ~200 tokens

3. **FI-ROUTER-FEAT-001** - A/B Testing (90% Claude / 10% Offline)
   - Router decision: random 90/10 split
   - Log provider usado en audit_logs
   - Comparación side-by-side en eval

**Target**:
- Latencia p95 ≤ 8-12s para 200 tokens (CPU)
- Calidad: medir con golden set

---

### Sprint 4: Gatekeeper (Ruteo Inteligente) 🚦

**Objetivo**: Ruteo progresivo según calidad y latencia

**Cards**:

1. **FI-ROUTER-FEAT-002** - Gatekeeper Heurístico
   - Evaluar respuesta offline con heurística:
     - Length check (no demasiado corto/largo)
     - Sentiment check (no negativo en health queries)
     - Keyword presence (términos médicos esperados)
   - Score: 0-100
   - Threshold: score < 70 → fallback Claude

2. **FI-ROUTER-FEAT-003** - Ruteo Progresivo
   - Inicio: 10% offline
   - Si score promedio > 75 durante 7 días → 50% offline
   - Si score promedio > 85 durante 7 días → 100% offline
   - Rollback automático si score cae < 70

3. **FI-CACHE-FEAT-001** - Cache Local de Completions
   - Cache en `/cache/completions.h5`
   - Key: SHA256(prompt + model + params)
   - TTL: 7 días
   - Eviction: LRU (max 1GB cache)

**Fallback Policy**:
- Timeout offline (>12s) → Claude
- Score bajo → Claude
- Error de Ollama → Claude

---

### Sprint 5: Calidad y Optimización 🔧

**Objetivo**: Δcalidad ≤10% vs Claude, p95 ≤8-12s/200toks

**Cards**:

1. **FI-PROMPT-FEAT-002** - Afinado de Prompts
   - Template específico para modelo offline
   - Few-shot examples en prompts (mejora calidad)
   - System prompt optimizado para telemedicina

2. **FI-CONTEXT-FEAT-001** - Truncado Inteligente de Contexto
   - Max context: 2048 tokens (modelo 7B)
   - Truncado: priorizar mensajes recientes
   - Summarization de contexto antiguo

3. **FI-SEARCH-FEAT-002** - Reranker Liviano (e5/bge)
   - Model: `bge-reranker-base` on-prem
   - Rerank top 20 results → top 5 most relevant
   - Latency overhead: <500ms

4. **FI-MODEL-OPT-001** - Cuantización y Threads
   - Probar q5_0, q5_1 (mejor calidad que q4_0)
   - Ajustar `num_threads` en Ollama
   - Benchmark: trade-off calidad/latencia

**Targets**:
- Δcalidad ≤10% vs Claude en golden set
- p95 ≤8-12s/200 tokens (CPU)
- Cache hit rate >30%

---

### Sprint 6: Escala y Guardrails 🚀

**Objetivo**: RS4021xs+ + GPU opcional, guardrails PII, estabilidad 99.5%

**Cards**:

1. **FI-INFRA-FEAT-002** - GPU Opcional (Escala a 14B/32B)
   - Evaluar GPU: NVIDIA RTX 3060 (12GB VRAM)
   - Deploy modelo 14B (DeepSeek-R1-14B-q5_0)
   - Benchmark: latencia con GPU vs CPU

2. **FI-SEC-FEAT-005** - Guardrails PII
   - Filtro pre-LLM: detectar PII (nombres, DNI, emails)
   - Regex + NER simple (spaCy)
   - Redacción automática: `[REDACTED_NAME]`
   - Audit log: PII_DETECTED events

3. **FI-SEC-FEAT-006** - Límites de Longitud
   - Max prompt length: 2048 tokens
   - Max response length: 1024 tokens
   - Truncado automático con advertencia

4. **FI-AUDIT-FEAT-001** - Auditoría Completa
   - Logging de TODOS los requests (prompt hash, provider, latency, cost)
   - Dashboard de uso: requests/día, cost/día, provider split
   - Alertas: cost > $10/día, latency p95 > 15s

5. **FI-NET-FEAT-001** - Egreso Total DENY
   - Firewall rules: DENY all outbound except:
     - `api.anthropic.com` (solo si Claude enabled)
     - `*.synology.com` (NAS updates)
   - Validar con `iptables` o NAS firewall

**Criterios de Salida Sprint 6**:
- ✅ Costo ↓≥60% vs all-Claude baseline
- ✅ 0 PHI externo (todo procesado on-prem)
- ✅ Estabilidad 99.5% (uptime + success rate)
- ✅ Rollback one-switch (Claude enable/disable en config)

---

## 📊 Métricas de Éxito (Sprint 0 → Sprint 6)

| Métrica | Sprint 0 (Claude) | Sprint 6 (Offline) | Target |
|---------|-------------------|---------------------|--------|
| **Costo/1K tokens** | $0.003 | $0 (amortizado) | ↓100% |
| **Costo/mes (1M tokens)** | ~$3,000 | ~$0 | ↓≥60% |
| **Latencia p95** | 2-4s | 8-12s | ≤12s |
| **Calidad (BLEU)** | 0.85 (baseline) | ≥0.75 | Δ≤10% |
| **PHI externo** | Sí (API) | No (on-prem) | 0 |
| **Uptime** | 99.9% (Anthropic) | 99.5% (NAS) | ≥99.5% |

---

## 🛠️ Stack Tecnológico

### LLM Providers
- **Claude API**: Anthropic SDK (`anthropic>=0.8.0`)
- **Ollama**: Local inference (`requests` to OLLAMA_BASE_URL)
- **Futuro**: OpenAI, Google Gemini (si necesario)

### Modelos Offline (Opciones)
1. **Qwen2-7B-Instruct** (Alibaba)
   - Size: 4.1GB (q4_0)
   - Context: 32K tokens
   - Languages: EN, ZH, ES (good multilingual)

2. **DeepSeek-R1-Distill-7B** (DeepSeek)
   - Size: 4.3GB (q4_0)
   - Context: 16K tokens
   - Strength: Reasoning tasks

3. **Future**: LLaMA 3.1 8B, Mistral 7B (si modelos chinos no funcionan)

### Hardware
- **Actual**: Synology RS4021xs+ (AMD Ryzen V1780B, 64GB RAM)
- **CPU Inference**: 8-12s/200 tokens con q4_0
- **Futuro**: NVIDIA RTX 3060 (12GB VRAM) → 14B/32B models

---

## 🔄 Rollback Strategy

**One-Switch Rollback**:
```yaml
# config/fi.policy.yaml
llm:
  primary_provider: "ollama"  # Change to "claude" for instant rollback
  fallback_provider: "claude"
  enable_offline: true         # Set to false for all-Claude
```

**Triggers para Rollback**:
- Quality score < 70 promedio por 3 días
- Latency p95 > 15s por 2 días
- Ollama uptime < 95% en 7 días
- Incident crítico (ej: respuesta médica incorrecta)

---

## 📅 Timeline Estimado

| Sprint | Duración | Objetivo | Horas Est |
|--------|----------|----------|-----------|
| Sprint 0 | 2-3 días | FI-base + Claude SDK | ~5h |
| Sprint 1 | 2-3 días | Abstracción LLM | ~6h |
| Sprint 2 | 2-3 días | Golden set + eval | ~7h |
| Sprint 3 | 3-4 días | Ollama + modelo chino | ~8h |
| Sprint 4 | 3-4 días | Gatekeeper + A/B | ~8h |
| Sprint 5 | 3-4 días | Optimización | ~8h |
| Sprint 6 | 4-5 días | Escala + guardrails | ~10h |
| **Total** | **~4-6 semanas** | **Offline-first completo** | **~52h** |

---

## 🎯 Estado Actual (Post-Sprint 2)

**Completado**:
- ✅ HDF5 schema con audit logs
- ✅ Append-only policy + no-mutation
- ✅ Export policy con manifests
- ✅ Event sourcing completo
- ✅ Pre-commit hooks (6 validadores)

**Siguiente (Sprint 3 → Sprint 1 del roadmap)**:
- 🎯 Abstracción LLM con interfaz única
- 🎯 Router con Claude como provider inicial
- 🎯 fi.policy.yaml con presupuestos y timeouts

**Pendiente (Sprints posteriores)**:
- ⏳ Golden set telemedicina
- ⏳ Ollama en NAS
- ⏳ Modelo chino (Qwen2/DeepSeek)
- ⏳ Guardrails PII
- ⏳ Egreso total DENY

---

**Última actualización**: 2025-10-28
**Autor**: Bernard Uriza Orozco
**Status**: Roadmap aprobado, Sprint 0 (parcial) + Sprint 1 en ejecución

---
