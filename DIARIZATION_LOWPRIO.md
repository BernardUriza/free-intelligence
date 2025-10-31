# Low-Priority Diarization Worker

**Card:** FI-RELIABILITY-IMPL-004
**Created:** 2025-10-31
**Status:** ✅ IMPLEMENTED

## Overview

Worker de baja prioridad para diarización que **NO bloquea el hilo principal** ni interfiere con eventos de Triage/Timeline.

### Features

✅ **CPU Scheduler**: Solo procesa cuando CPU idle ≥50% por 10s
✅ **HDF5 Storage Incremental**: Guarda chunks conforme se completan (`storage/diarization.h5`)
✅ **Non-Blocking**: Worker daemon en thread separado
✅ **Progress Tracking**: Endpoint con `chunks[]` array para polling en frontend
✅ **CORS Ready**: Configurado para `localhost:9000`

---

## Architecture

```
┌─────────────────────┐
│ Frontend (9000)     │
│ Polling /jobs/{id}  │
└──────────┬──────────┘
           │ GET (1.5s interval)
           ▼
┌─────────────────────┐
│ FastAPI (7001)      │
│ /api/diarization/   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      ┌──────────────────┐
│ Low-Prio Worker     │─────▶│ storage/         │
│ (background thread) │      │ diarization.h5   │
└──────────┬──────────┘      └──────────────────┘
           │
           ▼
┌─────────────────────┐
│ CPU Scheduler       │
│ psutil.cpu_percent()│
│ Idle ≥50% → Process │
└─────────────────────┘
```

---

## Configuration

### Environment Variables

```bash
# Low-Priority Worker
export DIARIZATION_LOWPRIO=true              # Enable low-priority mode (default: true)
export DIARIZATION_CPU_IDLE_THRESHOLD=50.0   # CPU idle % required (default: 50)
export DIARIZATION_CPU_IDLE_WINDOW=10        # Monitoring window in seconds (default: 10)
export DIARIZATION_CHUNK_SEC=30              # Chunk duration (default: 30s)
export DIARIZATION_OVERLAP_SEC=0.8           # Overlap between chunks (default: 0.8s)
export DIARIZATION_H5_PATH=storage/diarization.h5  # HDF5 storage path

# Whisper (faster-whisper)
export WHISPER_MODEL_SIZE=base               # Model: tiny, base, small, medium (default: base)
export WHISPER_DEVICE=cpu                    # Device: cpu or cuda (default: cpu)
export WHISPER_COMPUTE_TYPE=int8             # Quantization: int8, float16 (default: int8)
export ASR_NUM_WORKERS=1                     # Workers (default: 1 for low-priority)
```

### Legacy Modes

Para deshabilitar low-priority worker y usar pipelines anteriores:

```bash
export DIARIZATION_LOWPRIO=false             # Disable low-priority worker
export DIARIZATION_USE_V2=true               # Use V2 pipeline (parallel chunks)
# OR
export DIARIZATION_USE_V2=false              # Use V1 pipeline (sequential)
```

---

## API Usage

### 1. Upload Audio & Start Job

```bash
curl -X POST http://localhost:7001/api/diarization/upload \
  -H "X-Session-ID: $(uuidgen)" \
  -F "audio=@consulta.wav"
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "session_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "pending",
  "message": "Diarization job created. Poll /api/diarization/jobs/{job_id} for status."
}
```

### 2. Poll Job Status (Frontend: 1.5s interval)

```bash
curl http://localhost:7001/api/diarization/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response (in progress):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "session_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "in_progress",
  "progress_pct": 66,
  "total_chunks": 3,
  "processed_chunks": 2,
  "chunks": [
    {
      "chunk_idx": 0,
      "start_time": 0.0,
      "end_time": 30.0,
      "text": "Hola doctor, me duele la cabeza desde hace tres días.",
      "speaker": "DESCONOCIDO",
      "temperature": -0.52,
      "rtf": 0.23,
      "timestamp": "2025-10-31T12:00:15Z"
    },
    {
      "chunk_idx": 1,
      "start_time": 29.2,
      "end_time": 59.2,
      "text": "¿Desde cuándo tiene ese dolor? ¿Ha tomado algún medicamento?",
      "speaker": "DESCONOCIDO",
      "temperature": -0.48,
      "rtf": 0.21,
      "timestamp": "2025-10-31T12:00:45Z"
    }
  ],
  "created_at": "2025-10-31T12:00:00Z",
  "updated_at": "2025-10-31T12:00:45Z",
  "error": null
}
```

**Response (completed):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "session_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "completed",
  "progress_pct": 100,
  "total_chunks": 3,
  "processed_chunks": 3,
  "chunks": [
    /* all 3 chunks */
  ],
  "created_at": "2025-10-31T12:00:00Z",
  "updated_at": "2025-10-31T12:01:30Z",
  "error": null
}
```

---

## HDF5 Storage Structure

```
storage/diarization.h5
└─ /diarization/
   ├─ /{job_id}/
   │  ├─ metadata (attrs)
   │  │  ├─ session_id
   │  │  ├─ audio_path
   │  │  ├─ audio_hash
   │  │  ├─ created_at
   │  │  ├─ total_chunks
   │  │  ├─ status
   │  │  ├─ progress_pct
   │  │  └─ updated_at
   │  └─ chunks (dataset)
   │     ├─ chunk_idx (int)
   │     ├─ start_time (float)
   │     ├─ end_time (float)
   │     ├─ text (str)
   │     ├─ speaker (str)
   │     ├─ temperature (float)
   │     ├─ rtf (float)
   │     └─ timestamp (str)
```

### Read HDF5 Manually

```python
import h5py

with h5py.File("storage/diarization.h5", "r") as h5:
    job_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    # Read metadata
    job_group = h5[f"diarization/{job_id}"]
    print("Status:", job_group.attrs["status"])
    print("Progress:", job_group.attrs["progress_pct"])

    # Read chunks
    chunks = job_group["chunks"]
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}: {chunk['text']}")
```

---

## CPU Scheduling Behavior

1. **Idle Detection**:
   - Samples CPU usage every 1s for 10s window
   - Calculates average idle %: `100 - cpu_percent()`
   - Only starts processing if `avg_idle ≥ 50%`

2. **Chunk Processing**:
   - Processes **1 chunk at a time** (30-45s audio)
   - Saves to HDF5 after each chunk (incremental)
   - Re-checks CPU idle before next chunk

3. **Priority**:
   - Does **NOT** preempt Triage/Timeline APIs
   - Runs in background thread (daemon)
   - Can be paused/stopped cleanly

---

## Frontend Integration (Example)

```typescript
// Poll job status every 1.5s
async function pollDiarizationStatus(jobId: string) {
  const interval = setInterval(async () => {
    const response = await fetch(
      `http://localhost:7001/api/diarization/jobs/${jobId}`
    );
    const status = await response.json();

    console.log(`Progress: ${status.progress_pct}%`);
    console.log(`Chunks processed: ${status.processed_chunks}/${status.total_chunks}`);

    // Display chunks incrementally
    status.chunks.forEach((chunk) => {
      console.log(`[${chunk.start_time}s - ${chunk.end_time}s] ${chunk.text}`);
    });

    if (status.status === "completed") {
      clearInterval(interval);
      console.log("Diarization complete!");
    } else if (status.status === "failed") {
      clearInterval(interval);
      console.error("Diarization failed:", status.error);
    }
  }, 1500); // Poll every 1.5s
}
```

---

## Testing

### Unit Tests

```bash
# Install dependencies
pip install psutil pytest pytest-asyncio

# Run tests
pytest tests/test_diarization_lowprio.py -v

# Run specific test
pytest tests/test_diarization_lowprio.py::test_cpu_scheduler_idle_detected -v

# Run with coverage
pytest tests/test_diarization_lowprio.py --cov=backend.diarization_worker_lowprio
```

### Manual Testing

```bash
# Terminal 1: Start backend (low-priority mode)
export DIARIZATION_LOWPRIO=true
export DIARIZATION_CPU_IDLE_THRESHOLD=50.0
uvicorn backend.fi_consult_service:app --reload --port 7001

# Terminal 2: Upload audio
SESSION_ID=$(uuidgen)
curl -X POST http://localhost:7001/api/diarization/upload \
  -H "X-Session-ID: $SESSION_ID" \
  -F "audio=@demo/consultas/consulta_001_audio.wav" \
  | jq -r '.job_id'

# Store job_id from response
JOB_ID="<paste-job-id-here>"

# Terminal 3: Poll status (watch progress)
watch -n 1.5 "curl -s http://localhost:7001/api/diarization/jobs/$JOB_ID | jq"

# Terminal 4: Monitor CPU usage
watch -n 1 "top -l 1 | grep 'CPU usage'"
```

---

## Performance Metrics

### Low-Priority Mode
- **CPU Usage**: <50% (waits for idle)
- **Processing Time**: Variable (depends on CPU availability)
- **Chunk RTF**: ~0.2-0.3 (faster-whisper base, int8, CPU)
- **Memory**: ~200MB (base model)
- **UI Blocking**: 0ms (non-blocking)

### Legacy V2 Mode (for comparison)
- **CPU Usage**: ~80% (aggressive parallel)
- **Processing Time**: ~3-4 min for 7.4 min audio
- **Chunk RTF**: ~0.15-0.25
- **Memory**: ~300MB
- **UI Blocking**: Minor (background task)

---

## Troubleshooting

### Worker Not Starting
**Symptom**: Jobs stay in `pending` forever

**Fix**:
```bash
# Check worker started
grep "WORKER_STARTED" backend.log

# Restart backend
pkill -f uvicorn
uvicorn backend.fi_consult_service:app --reload --port 7001
```

### CPU Never Idle
**Symptom**: Jobs never progress

**Fix**:
```bash
# Lower threshold
export DIARIZATION_CPU_IDLE_THRESHOLD=30.0  # 30% idle

# OR disable CPU check (process immediately)
export DIARIZATION_CPU_IDLE_WINDOW=1
```

### HDF5 File Locked
**Symptom**: `OSError: Unable to open file (unable to lock file)`

**Fix**:
```bash
# Check for stale locks
lsof storage/diarization.h5

# Kill processes holding lock
kill -9 <PID>
```

### Whisper Model Not Loading
**Symptom**: `RuntimeError: Whisper model not loaded`

**Fix**:
```bash
# Check model cache
ls -lh ~/.cache/huggingface/hub/

# Download model manually
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
```

---

## Migration from Legacy Pipelines

### V1 → Low-Priority

```diff
- export DIARIZATION_USE_V2=false
+ export DIARIZATION_LOWPRIO=true
+ export DIARIZATION_CPU_IDLE_THRESHOLD=50.0
```

### V2 → Low-Priority

```diff
- export DIARIZATION_USE_V2=true
- export DIARIZATION_PARALLEL_CHUNKS=2
+ export DIARIZATION_LOWPRIO=true
+ export DIARIZATION_CPU_IDLE_THRESHOLD=50.0
```

**Notes**:
- Low-priority mode uses HDF5 storage (not in-memory)
- Jobs survive backend restarts (persistent state)
- Polling endpoint returns `chunks[]` array (incremental progress)

---

## Roadmap

### v0.2.0
- [ ] Speaker classification (LLM-based, optional)
- [ ] Merge consecutive segments from same speaker
- [ ] Export results to JSON/Markdown

### v0.3.0
- [ ] WebSocket streaming (alternative to polling)
- [ ] Priority queue (high-priority jobs bypass CPU check)
- [ ] Multi-worker support (process multiple jobs concurrently)

---

## References

- **Card**: FI-RELIABILITY-IMPL-004
- **Worker**: `backend/diarization_worker_lowprio.py`
- **API**: `backend/api/diarization.py`
- **Tests**: `tests/test_diarization_lowprio.py`
- **Storage**: `storage/diarization.h5`

---

## License

MIT
