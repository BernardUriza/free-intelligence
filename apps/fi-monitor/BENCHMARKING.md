# FI Monitor - Sistema de Benchmarking Integrado

## Objetivo

Herramienta de benchmarking integrada en FI Monitor para medir performance de **RAG Service**, **Ollama** y **Gateway** en tiempo real durante desarrollo (`pnpm tauri:dev`).

**Target:** Suite completo en <2 minutos, con resultados guardados automáticamente y UI clara de pass/fail.

---

## Arquitectura

### Backend Rust (`src-tauri/src/main.rs`)

**Estructuras de Datos:**
- `RagBenchmark` - Métricas de RAG Service (latency, throughput, GPU info)
- `OllamaBenchmark` - Métricas de Ollama (tokens/sec, latency)
- `GatewayBenchmark` - Métricas de Gateway (routing overhead)
- `BenchmarkSuite` - Suite completo con timestamp
- `BenchmarkHistory` - Histórico de últimos 50 resultados

**Comandos Tauri:**
- `benchmark_rag_service()` - Benchmark RAG Service (8-15s)
- `benchmark_ollama()` - Benchmark Ollama (15-30s)
- `benchmark_gateway()` - Benchmark Gateway (1-2s)
- `benchmark_all()` - Suite completo (25-50s)
- `get_benchmark_history()` - Cargar histórico

**Persistence:**
- Path: `~/.config/fi-monitor/benchmarks.json`
- Formato: JSON con array de resultados (últimos 50)
- Auto-saved después de cada run

### Frontend React (`src/App.tsx`)

**State Management:**
- `benchmarkResults` - Resultado actual
- `isBenchmarking` - Progress indicator
- `benchmarkHistory` - Histórico (para features futuras)

**UI Components:**
- Benchmark header con botón "Run Suite"
- Progress indicator durante ejecución
- Tabla de resultados con thresholds
- Metadata (duration, timestamp)

---

## Thresholds de Pass/Fail

| Métrica | Threshold | Status |
|---------|-----------|--------|
| **RAG Service** |
| Single Query | <50ms | ✅ Pass / ⚠️ Warning |
| Batch 32 | <1000ms | ✅ Pass / ⚠️ Warning |
| Throughput | >200 qps | ✅ Pass / ⚠️ Warning |
| Device | `cuda` o `mps` | ✅ Pass / ❌ Fail (CPU) |
| **Ollama** |
| Tokens/sec | >50 t/s | ✅ Pass / ⚠️ Warning |
| **Gateway** |
| Health Check | <10ms | ✅ Pass / ⚠️ Warning |

---

## Uso

### 1. Start Development Environment

```bash
cd apps/fi-monitor
pnpm tauri:dev
```

### 2. Verificar Servicios

Antes de correr benchmark, asegurar que los servicios estén activos:

- ✅ **Ollama** status: Activo (port 11434)
- ✅ **RAG Service** status: Activo (port 11435)
- ✅ **Gateway** status: Activo (port 11400)

### 3. Ejecutar Benchmark

1. Click botón **"▶ Run Suite"** en sección "Performance Benchmark"
2. Esperar 30-60 segundos (progress indicator visible)
3. Revisar tabla de resultados con status icons (✅/⚠️/❌)

### 4. Verificar Resultados

**Results Table:**
- **RAG Service**: 6 métricas (single query, batch 10/32/100, throughput, device)
- **Ollama**: 2 métricas (single query, tokens/sec)
- **Gateway**: 1 métrica (health check)

**Metadata:**
- Total duration (ms)
- Timestamp (ISO 8601)

### 5. Revisar Histórico

```bash
cat ~/.config/fi-monitor/benchmarks.json
```

Últimos 50 resultados guardados automáticamente.

---

## Flujo de Ejecución

```
User Click "Run Suite"
  ↓
Frontend: runBenchmark() → invoke('benchmark_all')
  ↓
Backend Rust: benchmark_all()
  ├─ benchmark_rag_service() (8-15s)
  │  ├─ GET /rag/health → GPU info
  │  ├─ POST /rag/embed (1 text) → single_query_ms
  │  ├─ POST /rag/embed (10 texts) → batch_10_ms
  │  ├─ POST /rag/embed (32 texts) → batch_32_ms
  │  ├─ POST /rag/embed (100 texts) → batch_100_ms
  │  └─ Calculate throughput_qps
  │
  ├─ benchmark_ollama() (15-30s)
  │  ├─ POST /api/generate (1 query) → single_query_ms
  │  ├─ POST /api/generate (5 queries) → batch_5_avg_ms
  │  └─ Extract tokens_per_sec from eval_duration
  │
  └─ benchmark_gateway() (1-2s)
     ├─ GET /gateway/health → health_check_ms
     └─ Compare gateway vs direct → routing_overhead_ms
  ↓
save_benchmark_result() → ~/.config/fi-monitor/benchmarks.json
  ↓
app.emit('benchmark-complete') → Frontend
  ↓
UI actualiza tabla + metadata
```

---

## Expected Results (M1 Mac con MPS)

### RAG Service
- Single query: **28-35ms** ✅
- Batch 32: **850-950ms** ✅
- Throughput: **350-400 qps** ✅
- GPU memory: **127MB**
- Device: **mps** ✅
- GPU name: **Apple Silicon (MPS)** ✅

### Ollama (qwen3:1.7b)
- Single query: **400-600ms** ✅
- Tokens/sec: **70-90 t/s** ✅

### Gateway
- Health check: **3-8ms** ✅
- Routing overhead: **1-3ms** ✅

---

## Troubleshooting

### Error: "Services not running"

**Solución:**
1. Verificar que RAG Service esté activo en puerto 11435
2. Verificar que Ollama esté activo en puerto 11434
3. Verificar que Gateway esté activo en puerto 11400

### Error: "RAG Service skipped"

**Causa:** RAG Service no responde o GPU no disponible

**Logs:**
```
[FI Monitor] ⚠️ RAG Service skipped: Health check failed: connection refused
```

**Solución:**
- Start RAG Service manualmente
- Verificar que GPU esté disponible (`device: cuda` o `device: mps`)

### Error: "Ollama skipped"

**Causa:** Ollama no responde o modelo no disponible

**Logs:**
```
[FI Monitor] ⚠️ Ollama skipped: Single query failed: connection refused
```

**Solución:**
- Start Ollama manualmente
- Verificar que modelo `qwen3:1.7b` esté instalado

### Warning: Device is "cpu" (❌)

**Causa:** RAG Service corriendo en CPU en vez de GPU

**Solución:**
- Verificar instalación de CUDA (NVIDIA) o MPS (Apple Silicon)
- Reinstalar RAG Service con GPU support

---

## Console Logs Esperados

```
[FI Monitor] Starting benchmark suite...
[FI Monitor] Starting RAG Service benchmark...
[FI Monitor] ✅ RAG Service benchmark complete
[FI Monitor] Starting Ollama benchmark...
[FI Monitor] ✅ Ollama benchmark complete
[FI Monitor] Starting Gateway benchmark...
[FI Monitor] ✅ Gateway benchmark complete
[FI Monitor] Benchmark saved to ~/.config/fi-monitor/benchmarks.json
[FI Monitor] ✅ Benchmark suite complete in 42350ms
```

---

## Future Enhancements (Out of Scope)

Ideas para después del MVP:

1. **Historical Graph:** Chart.js para visualizar latency over time
2. **Export Results:** Download JSON o copy to clipboard
3. **Continuous Benchmarking:** Auto-run cada N minutos con alertas
4. **Comparative Analysis:** Comparar run actual vs anterior (delta indicators)
5. **Memory Profiling:** Track Rust app memory usage durante benchmark

---

## Archivos Modificados

| Archivo | Cambios | Líneas |
|---------|---------|--------|
| `src-tauri/src/main.rs` | 6 structs + 3 persistence + 5 commands | +450 |
| `src/App.tsx` | 5 interfaces + state + UI | +180 |
| `src/styles.css` | Estilos benchmark section | +80 |
| **Total** | **3 archivos** | **~710 líneas** |

---

## Dependencies

**No se requieren nuevas dependencies:**
- ✅ Rust: `reqwest`, `serde`, `tokio`, `chrono` (ya en Cargo.toml)
- ✅ React: `@tauri-apps/api` (ya en package.json)

---

## Success Criteria

✅ **Implementación exitosa cuando:**

1. Suite completo corre en <2 minutos
2. Results se guardan automáticamente en `~/.config/fi-monitor/benchmarks.json`
3. UI muestra progress durante ejecución
4. Cada métrica tiene threshold claro (✅/⚠️/❌)
5. Compatible con CUDA (Windows/Linux) y MPS (macOS)
6. Funciona gracefully cuando servicios no están corriendo (skip con warning)
7. Results table es clara y escaneable
8. Metadata muestra total duration + timestamp
9. History se acumula correctamente (últimos 50 results)
10. Console logs son claros y útiles para debugging
