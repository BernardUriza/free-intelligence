# Free Intelligence - Micro-Profiling Plan

**Created**: 2025-10-28
**Owner**: Bernard Uriza Orozco
**Status**: Draft v0.1
**Dependencies**: LATENCY_BUDGET.md

---

## Executive Summary

Este documento establece el **plan de micro-profiling** para identificar y optimizar cuellos de botella en el pipeline de Free Intelligence. El enfoque se centra en:

1. **uvloop vs asyncio** - Event loop performance
2. **ASGI workers** - Concurrency y paralelismo
3. **I/O zero-copy** - Reducir copias de memoria
4. **ffmpeg paralelo** - Procesamiento multimedia (futuro)
5. **Compression** - gzip vs lz4 vs zstd

---

## 1. Event Loop: uvloop vs asyncio

### Contexto

Free Intelligence usa FastAPI (basado en Starlette/ASGI), que por defecto usa el event loop estándar de Python (`asyncio`). **uvloop** es un reemplazo drop-in del event loop que usa `libuv` (la misma librería de Node.js), con mejoras de 2-4x en rendimiento.

### Benchmark Propuesto

```python
# benchmark_event_loop.py
import asyncio
import time
from typing import Literal

async def simulate_io_workload(n_requests: int = 1000):
    """Simula carga de I/O típica (HDF5 reads)."""
    async def single_request():
        await asyncio.sleep(0.001)  # Simula 1ms de I/O
        return {"status": "ok"}

    tasks = [single_request() for _ in range(n_requests)]
    return await asyncio.gather(*tasks)

def benchmark(loop_type: Literal['asyncio', 'uvloop']):
    if loop_type == 'uvloop':
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    start = time.perf_counter()
    asyncio.run(simulate_io_workload(1000))
    elapsed = (time.perf_counter() - start) * 1000  # ms

    print(f"{loop_type:10s}: {elapsed:6.2f}ms")

if __name__ == "__main__":
    benchmark('asyncio')
    benchmark('uvloop')
```

### Resultados Esperados

| Event Loop | 1K requests | 10K requests | Mejora |
|------------|-------------|--------------|--------|
| asyncio    | ~150ms      | ~1500ms      | -      |
| uvloop     | ~60ms       | ~600ms       | **2.5x** |

### Implementación

```python
# backend/fi_consult_service.py (modificado)
if __name__ == "__main__":
    import uvicorn
    import uvloop

    # Habilitar uvloop globalmente
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    uvicorn.run(
        "backend.fi_consult_service:app",
        host="127.0.0.1",
        port=7001,
        reload=True,
        loop="uvloop"  # Uvicorn soporta loop='uvloop' directamente
    )
```

**Requisitos**:
```bash
pip install uvloop
```

**Riesgos**: Muy bajo. uvloop es drop-in compatible con asyncio.

---

## 2. ASGI Workers: Concurrency Model

### Contexto

FastAPI puede correr con múltiples workers para aprovechar múltiples cores. Configuración actual: **1 worker** (single process). Para 100 sesiones/día (~4 sesiones/hora), esto puede ser suficiente. Para 1000+ sesiones/día, necesitamos escalar.

### Workers Configuration

```bash
# Desarrollo (actual)
uvicorn backend.fi_consult_service:app --reload --port 7001

# Producción (propuesto)
gunicorn backend.fi_consult_service:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 127.0.0.1:7001 \
    --timeout 30 \
    --graceful-timeout 10 \
    --log-level info
```

### Workers Formula

```
workers = (2 × CPU_cores) + 1
```

Para **NAS con 4 cores**: `workers = (2 × 4) + 1 = 9`

**Trade-off**:
- Más workers = Mayor throughput
- Más workers = Mayor uso de memoria (cada worker tiene su propio Python interpreter)

### Benchmark Propuesto

```python
# benchmark_workers.py
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def single_request():
    response = requests.post(
        "http://127.0.0.1:7001/consultations",
        json={"user_id": "benchmark_user"}
    )
    return response.status_code == 201

def benchmark_throughput(n_requests: int, n_workers: int):
    """Mide throughput (requests/sec) con N workers."""
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(single_request) for _ in range(n_requests)]
        results = [f.result() for f in as_completed(futures)]

    elapsed = time.perf_counter() - start
    success_rate = sum(results) / len(results) * 100
    rps = n_requests / elapsed

    print(f"Workers: {n_workers} | RPS: {rps:.2f} | Success: {success_rate:.1f}%")

if __name__ == "__main__":
    # Ejecutar con diferentes configuraciones de workers
    for workers in [1, 2, 4, 8]:
        print(f"\n=== Testing with {workers} workers ===")
        # Reiniciar servidor con `--workers {workers}`
        benchmark_throughput(1000, workers)
```

### Resultados Esperados

| Workers | RPS (requests/sec) | Latency p95 | CPU Usage |
|---------|-------------------|-------------|-----------|
| 1       | ~100              | ~800ms      | ~25%      |
| 2       | ~180              | ~450ms      | ~50%      |
| 4       | ~320              | ~250ms      | ~90%      |
| 8       | ~350              | ~230ms      | ~100%     |

**Conclusión**: Sweet spot = **4 workers** (utilización óptima de CPU sin saturación).

---

## 3. I/O Zero-Copy: Reducir Copias de Memoria

### Contexto

En el pipeline actual, los datos se copian múltiples veces:

```
HTTP body → Python string → Pydantic dict → JSON string → HDF5 bytes
   (1)            (2)              (3)           (4)
```

Cada copia añade **latencia** (CPU) y **memoria**.

### Estrategias Zero-Copy

#### A. `ujson` / `orjson` (JSON parsing)

```python
# Actual (stdlib json)
import json
data = json.loads(request_body)  # Copia 1

# Propuesto (orjson)
import orjson
data = orjson.loads(request_body)  # 2-3x más rápido, menos copias
```

**Benchmark**:
```python
import json
import orjson
import time

payload = {"messages": [{"role": "user", "content": "x" * 1000}] * 100}
json_str = json.dumps(payload)

# Benchmark stdlib json
start = time.perf_counter()
for _ in range(1000):
    json.loads(json_str)
stdlib_time = (time.perf_counter() - start) * 1000

# Benchmark orjson
start = time.perf_counter()
for _ in range(1000):
    orjson.loads(json_str)
orjson_time = (time.perf_counter() - start) * 1000

print(f"stdlib json: {stdlib_time:.2f}ms")
print(f"orjson:      {orjson_time:.2f}ms (speedup: {stdlib_time/orjson_time:.2f}x)")
```

**Resultado esperado**: orjson ~3x más rápido.

#### B. Memory Views (HDF5 writes)

```python
# Actual (copia string → bytes)
event_json = event.model_dump_json()  # str
dataset[index] = event_json           # str → bytes (copia)

# Propuesto (usar memoryview)
event_bytes = event.model_dump_json().encode('utf-8')  # bytes
mv = memoryview(event_bytes)
dataset[index] = mv  # Sin copia (si HDF5 soporta)
```

**Nota**: HDF5 puede no soportar memoryview directamente. Evaluar con benchmarks.

#### C. Streaming uploads (FastAPI)

```python
from fastapi import UploadFile

@app.post("/consultations/{id}/events/stream")
async def append_event_stream(file: UploadFile):
    """Accept event stream sin cargar todo en memoria."""
    async for chunk in file:
        # Procesar chunk por chunk (útil para archivos grandes)
        pass
```

---

## 4. ffmpeg Paralelo: Procesamiento Multimedia (Futuro)

### Contexto

Aunque Free Intelligence no procesa video en la fase actual, el roadmap incluye:
- Cámaras de seguridad (CCTV)
- Video consultations
- Audio transcription (ASR)

ffmpeg puede ser un bottleneck si se ejecuta de forma síncrona.

### Estrategia de Paralelización

#### A. Multi-threading con `ffmpeg-python`

```python
import ffmpeg
import concurrent.futures

def process_video_segment(input_path, output_path, start_time, duration):
    """Procesar segmento de video en paralelo."""
    (
        ffmpeg
        .input(input_path, ss=start_time, t=duration)
        .output(output_path, vcodec='h264', acodec='aac')
        .run(quiet=True)
    )

def parallel_video_processing(input_path, num_segments=4):
    """Dividir video en N segmentos y procesarlos en paralelo."""
    probe = ffmpeg.probe(input_path)
    duration = float(probe['format']['duration'])
    segment_duration = duration / num_segments

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_segments) as executor:
        futures = []
        for i in range(num_segments):
            start_time = i * segment_duration
            output_path = f"segment_{i}.mp4"
            futures.append(
                executor.submit(process_video_segment, input_path, output_path, start_time, segment_duration)
            )

        # Wait for all segments
        concurrent.futures.wait(futures)

    # Concatenar segmentos
    # (usar ffmpeg concat demuxer)
```

#### B. Hardware Acceleration (NVIDIA NVENC)

```bash
# CPU encoding (slow)
ffmpeg -i input.mp4 -c:v h264 -c:a aac output.mp4

# GPU encoding (fast, requiere NVIDIA GPU)
ffmpeg -i input.mp4 -c:v h264_nvenc -c:a aac output.mp4
```

**Speedup esperado**: 5-10x con GPU vs CPU.

**Requisitos**:
- NVIDIA GPU con NVENC support
- ffmpeg compilado con `--enable-nvenc`

---

## 5. Compression: gzip vs lz4 vs zstd

### Contexto

Actual: HDF5 usa **gzip level 4** para compresión de datasets.

**Trade-off**:
- Mayor compresión = Menor espacio en disco, pero mayor latencia
- Menor compresión = Mayor espacio en disco, pero menor latencia

### Benchmark Propuesto

```python
# benchmark_compression.py
import h5py
import numpy as np
import time

def benchmark_compression(compression, compression_opts=None):
    """Benchmark HDF5 compression."""
    filename = f"test_{compression}.h5"

    # Generate test data (1000 events, ~1KB each)
    data = [f"event_{i}_" + "x" * 1000 for i in range(1000)]

    # Write benchmark
    start = time.perf_counter()
    with h5py.File(filename, 'w') as f:
        dt = h5py.special_dtype(vlen=str)
        dataset = f.create_dataset(
            'events',
            shape=(1000,),
            dtype=dt,
            compression=compression,
            compression_opts=compression_opts
        )
        for i, event in enumerate(data):
            dataset[i] = event
    write_time = (time.perf_counter() - start) * 1000

    # Read benchmark
    start = time.perf_counter()
    with h5py.File(filename, 'r') as f:
        events = list(f['events'])
    read_time = (time.perf_counter() - start) * 1000

    # File size
    import os
    file_size = os.path.getsize(filename) / 1024  # KB

    print(f"{compression:15s} | Write: {write_time:6.2f}ms | Read: {read_time:6.2f}ms | Size: {file_size:6.2f}KB")

    os.remove(filename)

if __name__ == "__main__":
    print("Compression     | Write (ms)  | Read (ms)   | Size (KB)")
    print("-" * 70)
    benchmark_compression(None)                 # No compression
    benchmark_compression('gzip', 1)            # gzip level 1 (fast)
    benchmark_compression('gzip', 4)            # gzip level 4 (actual)
    benchmark_compression('gzip', 9)            # gzip level 9 (max)
    benchmark_compression('lzf')                # lzf (fast, built-in)
    # Note: lz4/zstd requieren h5py-compiled con plugin support
```

### Resultados Esperados

| Compression    | Write (ms) | Read (ms) | Size (KB) | Ratio |
|----------------|-----------|-----------|-----------|-------|
| None           | 50        | 20        | 1000      | 1.0x  |
| gzip-1         | 150       | 40        | 300       | 3.3x  |
| gzip-4 (actual)| 300       | 60        | 250       | 4.0x  |
| gzip-9         | 800       | 80        | 230       | 4.3x  |
| lzf            | 80        | 30        | 400       | 2.5x  |
| lz4 (ideal)    | 60        | 25        | 380       | 2.6x  |
| zstd-3         | 100       | 35        | 280       | 3.6x  |

**Recomendación**:
- **Quick win**: gzip-1 (2x más rápido que gzip-4, 80% del ratio)
- **Best balance**: lzf (built-in, 4x más rápido que gzip-4)
- **Future**: zstd-3 (mejor ratio que lzf, más rápido que gzip)

---

## 6. Profiling Tools Stack

### A. cProfile (Built-in)

```python
# profile_endpoint.py
import cProfile
import pstats
import requests

def profile_append_event():
    """Profile single append event."""
    response = requests.post(
        "http://127.0.0.1:7001/consultations/test-id/events",
        json={
            "event_type": "MESSAGE_RECEIVED",
            "payload": {"message": "test"},
            "user_id": "profiling_user"
        }
    )
    return response

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    for _ in range(100):
        profile_append_event()

    profiler.disable()

    # Print stats
    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 funciones
```

### B. py-spy (Sampling profiler)

```bash
# Install
pip install py-spy

# Profile running process (sin modificar código)
py-spy record -o profile.svg --pid $(pgrep -f fi_consult_service)

# Generate flamegraph
py-spy record -o profile.svg --duration 30 --rate 100 -- python -m uvicorn backend.fi_consult_service:app
```

**Output**: `profile.svg` - Flamegraph interactivo.

### C. line_profiler (Line-by-line)

```python
# Install
pip install line_profiler

# Decorador
from line_profiler import profile

@profile
def append_event(self, consultation_id, event):
    # ... código a perfilar
    pass

# Run
kernprof -l -v backend/fi_event_store.py
```

### D. memory_profiler

```bash
pip install memory-profiler

# Decorador
from memory_profiler import profile

@profile
def append_event():
    pass

# Run
python -m memory_profiler backend/fi_event_store.py
```

---

## 7. Profiling Roadmap

### Fase 1: Baseline Profiling (1 día)

- [ ] Ejecutar cProfile en endpoint `/consultations/{id}/events`
- [ ] Identificar top 10 funciones por tiempo acumulado
- [ ] Generar flamegraph con py-spy (30s sampling)
- [ ] Medir memory usage con memory_profiler

**Deliverable**: `docs/PROFILING_BASELINE.md` con flamegraphs.

### Fase 2: Targeted Optimizations (2-3 días)

- [ ] Benchmark uvloop vs asyncio
- [ ] Benchmark orjson vs stdlib json
- [ ] Benchmark compression (gzip-1, lzf, gzip-4)
- [ ] Benchmark workers (1, 2, 4, 8)

**Deliverable**: `docs/OPTIMIZATION_RESULTS.md` con tablas comparativas.

### Fase 3: Integration (1-2 días)

- [ ] Integrar uvloop en producción
- [ ] Reemplazar json por orjson
- [ ] Cambiar compression a lzf (o gzip-1)
- [ ] Configurar gunicorn con 4 workers

**Deliverable**: Deployment con optimizaciones aplicadas.

---

## 8. Success Metrics

| Métrica | Baseline | Target | Método |
|---------|----------|--------|--------|
| **p95 latency** | 2000ms | <500ms | cProfile + load testing |
| **Throughput** | 10 req/s | 100 req/s | ab (Apache Bench) |
| **CPU usage** | 25% | <80% | htop durante load test |
| **Memory usage** | 200MB | <500MB | memory_profiler |

---

## Referencias

- **uvloop**: https://github.com/MagicStack/uvloop
- **orjson**: https://github.com/ijl/orjson
- **py-spy**: https://github.com/benfred/py-spy
- **HDF5 compression**: https://docs.h5py.org/en/stable/high/dataset.html#filter-pipeline
- **FastAPI performance**: https://fastapi.tiangolo.com/deployment/concepts/

---

**Version History**:
- v0.1 (2025-10-28): Documento inicial con benchmarks propuestos
