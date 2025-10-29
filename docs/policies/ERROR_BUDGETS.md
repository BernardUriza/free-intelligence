# Error Budgets & SLO Policy

**Card**: FI-RELIABILITY-STR-001
**Axioma**: Materia = Glitch Elegante
**Owner**: SRE / Platform Team
**Version**: 1.0.0
**Date**: 2025-10-29

---

## Filosofía

> _"La materia es glitch elegante. No combatimos la entropía, la administramos."_

Free Intelligence adopta error budgets como reconocimiento de que **100% uptime es mentira**. En lugar de promesas imposibles, establecemos presupuestos realistas de fallas permitidas.

---

## Service Level Objectives (SLOs)

| Servicio | Métrica | Target (SLO) | Error Budget | Ventana |
|----------|---------|--------------|-------------|---------|
| **Ingestion API** | p95 latency | <2s | 5% de requests pueden fallar | 30 días |
| **Timeline API** | p99 latency | <100ms | 1% pueden exceder | 7 días |
| **Verify API** | p95 latency | <500ms | 3% pueden fallar | 30 días |
| **Corpus HDF5 writes** | Success rate | 99.9% | 0.1% fallos permitidos | 30 días |
| **LLM routing** | Timeout rate | <1% | 1% requests pueden timeout | 7 días |

---

## Cálculo de Error Budget

**Fórmula**:
```
Error Budget = (1 - SLO) × Total Requests
```

**Ejemplo**: Timeline API
- SLO: 99% de requests <100ms (p99)
- Requests mensuales: 100,000
- Error budget: (1 - 0.99) × 100,000 = **1,000 requests lentos permitidos**

**Consumo**:
- Si en la semana 1 tuvimos 300 requests >100ms, consumimos 30% del budget mensual
- Quedan 700 requests "lentos" permitidos para el resto del mes

---

## Acciones por Consumo de Budget

| Budget Restante | Acción | Owner | Ejemplo |
|-----------------|--------|-------|---------|
| **>75%** | ✅ Normal operations | Dev team | Deployments sin restricción |
| **50-75%** | ⚠️ Monitor closely | SRE | Review logs diarios, alertas Slack |
| **25-50%** | 🚨 Freeze risky deployments | Tech Lead | Solo hotfixes críticos |
| **<25%** | 🔴 **Emergency mode** | CTO | Rollback, incident post-mortem |

---

## Políticas de Degradación Suave

### 1. **Back-Pressure en Ingestion**
**Trigger**: p95 latency >3s (150% del SLO)
**Acción**:
- Activar rate limiting (50 req/s → 25 req/s)
- Retornar HTTP 429 con `Retry-After` header
- Log en audit trail: `BACKPRESSURE_ACTIVATED`

**Código**:
```python
if p95_latency > 3.0:
    rate_limiter.reduce_by(50%)
    logger.warn("BACKPRESSURE_ACTIVATED", latency=p95_latency)
```

---

### 2. **Circuit Breaker en LLM Router**
**Trigger**: Timeout rate >2% en 5min
**Acción**:
- Abrir circuit breaker
- Fallback a cached responses (si disponible)
- Modo degradado: respuestas simplificadas

**Duración**: 1 minuto antes de retry half-open

---

### 3. **Queue Shedding en Corpus Writes**
**Trigger**: Queue depth >10,000 items
**Acción**:
- Shed lowest-priority items (analytics, embeddings)
- Preservar writes críticos (interactions, metadata)
- Alert: `QUEUE_SHEDDING_ACTIVE`

**Prioridad**:
1. Interactions (crítico)
2. Metadata (alto)
3. Embeddings (medio)
4. Analytics (bajo)

---

## Chaos Engineering Drills

### Drill Schedule (Mensual)

| Mes | Drill Type | Objetivo | Owner | Fecha |
|-----|-----------|----------|-------|-------|
| Nov 2025 | **Network partition** | Verificar queue resilience | SRE | 2025-11-15 |
| Dec 2025 | **Corpus file lock** | Test retry logic | Backend | 2025-12-20 |
| Jan 2026 | **LLM API timeout** | Validate circuit breaker | ML Ops | 2026-01-17 |
| Feb 2026 | **Disk full (90%)** | Log rotation & cleanup | Infra | 2026-02-14 |

### Drill Protocol

**Pre-drill** (1 semana antes):
1. Announce en #sre canal
2. Crear rollback plan
3. Definir success criteria
4. Preparar monitoring dashboards

**During drill** (30-60 min):
1. Ejecutar chaos injection (ej. `iptables DROP`)
2. Monitor dashboards en tiempo real
3. Validar auto-recovery
4. Documentar observaciones

**Post-drill** (1-2 días después):
1. Write post-mortem (incluso si fue exitoso)
2. Update runbooks con learnings
3. File issues para mejoras detectadas
4. Update ERROR_BUDGETS.md con nuevos SLOs si necesario

---

## Monitoring & Alerting

### Dashboards Requeridos

**1. Error Budget Dashboard**
- Budget restante (gauge)
- Consumo semanal (line chart)
- Top 5 endpoints consumidores
- Proyección de agotamiento (si continúa trend)

**2. Latency Heatmap**
- p50, p95, p99 por endpoint
- Color coding: verde <SLO, amarillo 100-150% SLO, rojo >150%

**3. Incident Timeline**
- Eventos de backpressure
- Circuit breaker activations
- Queue shedding episodes

### Alertas (Slack + Email)

| Condición | Severidad | Destinatarios | Ejemplo |
|-----------|-----------|---------------|---------|
| Budget <50% | WARNING | #sre | "Timeline API budget at 48% (12 days remaining)" |
| Budget <25% | CRITICAL | @tech-lead, #incidents | "EMERGENCY: Ingestion budget at 18%" |
| SLO breach >2h | INCIDENT | @oncall, @cto | "p95 latency >2s for 2.5h" |
| Chaos drill start | INFO | #general | "🔥 Chaos drill: Network partition starting" |

---

## Revisión & Ajuste

**Frecuencia**: Trimestral

**Preguntas**:
1. ¿Los SLOs son muy estrictos? (budget siempre >90%)
2. ¿Muy laxos? (budget agotándose constantemente)
3. ¿Nuevos servicios requieren SLOs?
4. ¿Chaos drills revelaron gaps en policies?

**Output**: Updated ERROR_BUDGETS.md con nuevos targets

---

## Referencias

- **Axioma**: `docs/PHILOSOPHY_CORPUS.md` (Materia = Glitch Elegante)
- **Mapping**: `docs/PHI_MAPPING.md`
- **Incident Runbooks**: `docs/runbooks/`
- **SRE Handbook**: Google SRE Book, Chapter 3-4

---

## Anexo: Ejemplo de Post-Mortem

**Incident**: Timeline API p99 >500ms durante 3h (2025-10-15)

**Impact**: 20% de error budget consumido en 1 día

**Root Cause**: Corpus file lock contention (10+ concurrent reads)

**Resolution**: Implemented read-side caching (Redis) para metadata

**Prevention**: Added drill "Corpus lock storm" para Feb 2026

**Action Items**:
- [x] Deploy Redis cache (FI-PERF-FEAT-001)
- [x] Add cache hit rate to dashboard
- [ ] Benchmark with 100 concurrent reads (FI-TEST-PERF-002)

---

_"El glitch no es el enemigo. El enemigo es no tener presupuesto para él."_
