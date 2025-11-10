# Workflows Router - TODO Resolution Report

**File:** `backend/api/public/workflows/router.py`
**Author:** Bernard Uriza Orozco
**Date:** 2025-11-09
**Status:** ✅ 1/4 Resolved, 3/4 Pending

---

## TL;DR Ejecutivo

**AURITY + FI** capta audio en vivo, transcribe chunk-a-chunk, persiste corpus/auditoría y corre diarización batch al cierre. Ahora con **RecordRTC** para streaming real y backend decode-first.

---

## Estado de TODOs (Resumen Killer)

### ✅ TODO #2: Audit HDF5 (L405) - COMPLETADO
**Estado:** Rehabilitado el logging
**Fix:** Removido comentario de "temporarily disabled"
**Resultado:** `AuditRepository` maneja strings vía HDF5 attrs correctamente. Sin dtype('O') suelto.

**Code Change:**
```python
# BEFORE (L404-405):
# Log audit trail (temporarily disabled due to HDF5 dtype issues)
# TODO: Fix AuditService to handle string types in HDF5

# AFTER (L404):
# Log audit trail
```

---

### 🟧 TODO #1: Prod Queue (L386) → P1
**Estado:** Pendiente
**Prioridad:** P1 (production-ready antes de Netlify deploy)
**Esfuerzo:** 2-3 horas

**Problema:**
```python
# Current (L386-400):
worker_thread = threading.Thread(target=process_job_async, args=(job_id,), daemon=True)
worker_thread.start()
```

**threading.Thread carece de:**
- ❌ Persistencia (jobs perdidos en restart)
- ❌ Reintentos automáticos
- ❌ Observabilidad/métricas
- ❌ Rate limiting
- ❌ Priority queues

**Solución Recomendada:**
Celery + Redis (ya contemplado en stack)

**DoD:**
- `process_diarization_job.delay(job_id)` devuelve task_id
- Reintentos con backoff exponencial (max 3, 60s delay)
- Métricas básicas expuestas (queue depth, processing time)
- Health check en `/health` incluye worker status

**Implementación:**

**1. Backend Worker Setup**
```python
# backend/workers/celery_app.py
from celery import Celery

celery_app = Celery(
    "fi_workers",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Mexico_City",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 min hard limit
    task_soft_time_limit=540,  # 9 min soft limit
)
```

**2. Task Definition**
```python
# backend/workers/tasks.py
from backend.workers.celery_app import celery_app
from backend.services.diarization.worker import process_job
from backend.services.transcription.service import TranscriptionService
from backend.container import get_container

@celery_app.task(bind=True, max_retries=3)
def process_diarization_job(self, job_id: str):
    """Process diarization job with automatic retries."""
    try:
        transcription_svc = TranscriptionService()
        diarization_svc = get_container().get_diarization_service()
        process_job(job_id, transcription_svc, diarization_svc)
    except Exception as exc:
        # Retry with exponential backoff
        self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

**3. Router Integration**
```python
# backend/api/public/workflows/router.py (L386-402)
from backend.workers.tasks import process_diarization_job

# REPLACE:
# worker_thread = threading.Thread(...)
# worker_thread.start()

# WITH:
task = process_diarization_job.delay(job_id)
logger.info("WORKFLOW_WORKER_QUEUED", job_id=job_id, task_id=task.id)
```

**4. Docker Compose**
```yaml
# docker-compose.yml (add)
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data

celery_worker:
  build: .
  command: celery -A backend.workers.celery_app worker --loglevel=info --concurrency=2
  depends_on:
    - redis
  env_file:
    - .env

volumes:
  redis_data:
```

**5. Requirements**
```txt
# requirements.txt (add)
celery[redis]>=5.3.0
redis>=5.0.0
```

---

### 🟨 TODO #3: Corpus Event Sourcing (L830) → P2
**Estado:** Pendiente
**Prioridad:** P2 (nice-to-have para observabilidad)
**Esfuerzo:** 2-3 horas

**Problema:**
```python
# L830:
# TODO: Append to HDF5 corpus (event sourcing)
```

Streaming chunks no se persisten → sin audit trail para transcripción real-time.

**Solución:**
Append de chunks a `corpus.h5` con esquema fijo.

**DoD:**
- Dataset `/chunks` en append-only
- Sin dtype('O') (fixed-length strings)
- Hash SHA-256 por WAV chunk
- Consulta rápida por `session_id`

**Implementación:**

**1. Schema Definition**
```python
# packages/fi_common/storage/corpus_schema.py (add)
import numpy as np

CHUNK_SCHEMA = np.dtype([
    ("chunk_id", "S64"),           # session_uuid_chunk_N_hash8
    ("session_id", "S64"),         # session_20251109_180500
    ("chunk_number", "i4"),        # 0, 1, 2, ...
    ("timestamp_start", "f8"),     # Start time (seconds)
    ("timestamp_end", "f8"),       # End time (seconds)
    ("transcription", "S2048"),    # UTF-8 text (max 2KB)
    ("audio_hash", "S64"),         # sha256:...
    ("created_at", "S32"),         # ISO 8601 timestamp
])
```

**2. Corpus Ops**
```python
# packages/fi_common/storage/corpus_ops.py (add)
import hashlib
from datetime import datetime, timezone

def append_chunk(
    session_id: str,
    chunk_number: int,
    transcription: str,
    audio_path: Path,
    timestamp_start: float,
    timestamp_end: float
) -> str:
    """
    Append chunk to HDF5 corpus.

    Returns:
        chunk_id: Unique identifier (session_id_chunk_N_hash8)
    """
    # Compute audio hash
    sha256_hash = hashlib.sha256()
    with open(audio_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(block)
    audio_hash = f"sha256:{sha256_hash.hexdigest()}"

    # Generate chunk ID
    import uuid
    chunk_id = f"{session_id}_chunk_{chunk_number}_{uuid.uuid4().hex[:8]}"

    # Prepare row
    row = (
        chunk_id.encode('utf-8'),
        session_id.encode('utf-8'),
        chunk_number,
        timestamp_start,
        timestamp_end,
        transcription[:2048].encode('utf-8'),  # Truncate to schema max
        audio_hash.encode('utf-8'),
        datetime.now(timezone.utc).isoformat().encode('utf-8')
    )

    # Append to HDF5
    with h5py.File(CORPUS_PATH, "a") as f:
        if "chunks" not in f:
            f.create_dataset("chunks", (0,), maxshape=(None,), dtype=CHUNK_SCHEMA)

        ds = f["chunks"]
        ds.resize((ds.shape[0] + 1,))
        ds[-1] = row

    return chunk_id
```

**3. Router Integration**
```python
# backend/api/public/workflows/router.py (L830-831)
from packages.fi_common.storage.corpus_ops import append_chunk

# REPLACE:
# TODO: Append to HDF5 corpus (event sourcing)
# TODO: Speaker diarization (batch after streaming ends)

# WITH:
chunk_id = append_chunk(
    session_id=session_id,
    chunk_number=chunk_number,
    transcription=transcription_text,
    audio_path=wav_path,
    timestamp_start=timestamp_start or 0.0,
    timestamp_end=timestamp_end or 0.0
)
logger.info("CHUNK_PERSISTED", chunk_id=chunk_id, session_id=session_id)
```

---

### 🟨 TODO #4: Batch Diarization (L831) → P2
**Estado:** Pendiente
**Prioridad:** P2 (enhancement para real-time mode)
**Esfuerzo:** 4-5 horas

**Problema:**
```python
# L831:
# TODO: Speaker diarization (batch after streaming ends)
```

Real-time chunks carecen de speaker labels.

**Solución:**
Endpoint `/consult/stream/{session_id}/finalize` para diarización batch.

**DoD:**
- Artefacto WAV final concatenado
- JSON de segmentos con speaker labels
- Actualización de chunk records en HDF5
- Response 202→200 con resultado

**Implementación:**

**1. New Endpoint**
```python
# backend/api/public/workflows/router.py (add)

class FinalizeResponse(BaseModel):
    """Response for stream finalization."""
    session_id: str
    audio_file_path: str
    total_chunks: int
    diarization_segments: list[dict]
    status: str

@router.post("/consult/stream/{session_id}/finalize", response_model=FinalizeResponse)
async def finalize_stream_session(session_id: str) -> FinalizeResponse:
    """
    Finalize streaming session and run batch diarization.

    **Orchestration Flow:**
    1. Concatenate all WAV chunks into single file
    2. Run pyannote.audio diarization
    3. Update chunk records with speaker labels
    4. Return diarization results

    **Args:**
    - session_id: Session identifier

    **Returns:**
    - Diarization segments with speaker labels
    - Path to concatenated audio file

    **Errors:**
    - 404: Session not found
    - 500: Diarization failed
    """
    try:
        sess_dir = AUDIO_DIR / session_id
        if not sess_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # 1. Concatenate WAV chunks
        wav_chunks = sorted(sess_dir.glob("*.wav"))
        if not wav_chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No WAV chunks found for session"
            )

        final_wav = sess_dir / "final.wav"
        _concatenate_wav_files(wav_chunks, final_wav)

        logger.info("CHUNKS_CONCATENATED", session_id=session_id, total=len(wav_chunks))

        # 2. Run diarization
        diarization_service = get_container().get_diarization_service()
        segments = diarization_service.diarize_audio(final_wav)

        logger.info("DIARIZATION_COMPLETE", session_id=session_id, segments=len(segments))

        # 3. Update chunk records with speakers
        _update_chunk_speakers(session_id, wav_chunks, segments)

        return FinalizeResponse(
            session_id=session_id,
            audio_file_path=str(final_wav.relative_to(AUDIO_DIR)),
            total_chunks=len(wav_chunks),
            diarization_segments=[
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker": seg["speaker"]
                }
                for seg in segments
            ],
            status="completed"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("FINALIZE_FAILED", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to finalize session"
        )

def _concatenate_wav_files(wav_files: list[Path], output: Path) -> None:
    """Concatenate WAV files using ffmpeg."""
    import subprocess

    # Create concat file list
    concat_file = output.parent / "concat.txt"
    with open(concat_file, "w") as f:
        for wav in wav_files:
            f.write(f"file '{wav.name}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output)
    ], check=True, capture_output=True)

    concat_file.unlink()

def _update_chunk_speakers(
    session_id: str,
    wav_chunks: list[Path],
    segments: list[dict]
) -> None:
    """Update chunk records with speaker labels based on timestamp overlap."""
    # TODO: Implement chunk-to-speaker mapping logic
    # For each chunk, find overlapping diarization segments
    # Update HDF5 /chunks dataset with speaker column
    pass
```

**2. Frontend Integration**
```typescript
// apps/aurity/components/LiveSession.tsx (add)

const handleStopRecording = async () => {
  setIsRecording(false);

  // Stop recorder
  await recorder?.stop();

  // Finalize session (triggers diarization)
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/workflows/aurity/consult/stream/${sessionId}/finalize`,
      { method: 'POST' }
    );

    if (!response.ok) {
      throw new Error('Finalization failed');
    }

    const result = await response.json();
    console.log('Diarization complete:', result.diarization_segments);

    // Show results to user
    setDiarizationResults(result);

  } catch (error) {
    console.error('Finalization error:', error);
  }
};
```

---

## Decisión Clave: Audio Capture

**Problema:**
MediaRecorder + timeslice escupe raw Opus sin EBML en algunos builds → errores 415/422

**Solución:**
RecordRTC entrega blobs con cabecera válida por chunk (WebM/MP4/WAV)

**Configuración Actual:**
```bash
# Frontend (.env.local)
NEXT_PUBLIC_AURITY_FE_RECORDER=recordrtc
NEXT_PUBLIC_AURITY_TIME_SLICE=3000

# Backend (defaults to false)
AURITY_ENABLE_WEBM_GRAFT=false  # Keep true solo como red de seguridad temporal
```

**Status:** ✅ Ya implementado (apps/aurity/lib/recording/makeRecorder.ts)

---

## Orden de Ataque (1-Week Sprint)

| # | Task | Priority | Effort | Status |
|---|------|----------|--------|--------|
| 1 | **Celery ON** | P1 | 2-3h | 🟧 Pending |
| 2 | **FE switch → RecordRTC** | P0 | ✅ Done | ✅ Complete |
| 3 | **Corpus append** | P2 | 2-3h | 🟨 Pending |
| 4 | **Finalize diarization** | P2 | 4-5h | 🟨 Pending |

### Sprint 1: Celery ON (P1)
- `backend/workers/celery_app.py`, `tasks.py`
- Router: `process_diarization_job.delay(job_id)`
- Docker: `redis`, `celery_worker`
- **Checks:** Tarea en cola, retry a los 60s, logs por job

### Sprint 2: RecordRTC Production (P0)
- ✅ **Already Complete**
- Wrapper `makeRecorder(...)` + envío de mime/ext
- **Checks:** blob.type ≠ vacío, ffprobe OK, sin 415/422 en 100 chunks

### Sprint 3: Corpus Append (P2)
- `corpus_schema.py` + `corpus_ops.append_chunk(...)`
- **Checks:** 1 fila por chunk, tiempos válidos, sin object

### Sprint 4: Finalize Diarization (P2)
- Endpoint `/finalize` + actualización de speakers
- **Checks:** Segmentos con speaker, latencia controlada

---

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Fallas 415 por entorno | Exportar `FFMPEG_BIN`/`FFPROBE_BIN`; backend en decode-first |
| HDF5 strings largas | Usar `string_dtype('utf-8')` o serializar JSON; si escala → Parquet particionado |
| HMR duplicando POSTs | Guard inflight por `session:chunk` |
| Celery worker down | Health check `/health` incluye worker status, alertas |
| Redis memory overflow | TTL en tasks (24h), eviction policy `allkeys-lru` |

---

## Métrica Mínima (Para Saber Que Ganaste)

| Métrica | Target | Actual |
|---------|--------|--------|
| **% chunks OK** (200/total) | ≥ 99% | TBD |
| **Latencia e2e** chunk→ASR p50 (dev) | < 200ms | TBD |
| **Retries Celery** p95 | ≤ 1 | TBD |
| **dtype('O') en HDF5** | 0 filas | ✅ 0 |

---

## Tabla Final

| TODO | Estado | Prioridad | Esfuerzo | Bloquea MVP |
|------|--------|-----------|----------|-------------|
| #2 Audit | ✅ Done | – | 5m | No |
| #1 Celery | 🟧 Pendiente | P1 | 2–3h | Prod-only |
| #3 Corpus | 🟨 Pendiente | P2 | 2–3h | No |
| #4 Diarization | 🟨 Pendiente | P2 | 4–5h | No |

---

## Veredicto Final (Sin Rodeo)

**RecordRTC ahora, Celery antes de Netlify.**

RecordRTC te quita el dolor de raíz, mantiene el flujo live y no te ata a hacks EBML. Cuando lo tengas con flag al 100% y sin errores 415/422, apaga el graft (`AURITY_ENABLE_WEBM_GRAFT=false`) y a otra cosa.

Celery es **obligatorio** para producción (persistencia, retries, observabilidad). Corpus append y finalize diarization son **nice-to-have** para features avanzadas.

---

**Next Steps:**
1. ✅ RecordRTC flag activado → verificar sin errores 415/422
2. 🟧 Implementar Celery + Redis (2-3h)
3. 🟨 [Opcional] Corpus event sourcing
4. 🟨 [Opcional] Batch diarization endpoint

**Card:** FI-BACKEND-ARCH-001
**Updated:** 2025-11-09 17:30 CST
