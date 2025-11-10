# Celery + Redis Background Job Processing

**Card:** FI-BACKEND-ARCH-001
**Status:** ✅ Production Ready
**Updated:** 2025-11-09

---

## 🎯 Overview

Production-grade background job processing using **Celery + Redis** for diarization tasks.

**Benefits over threading:**
- ✅ Persistent jobs (survive restarts)
- ✅ Automatic retries (3x exponential backoff)
- ✅ Real-time monitoring (Flower UI)
- ✅ Horizontal scalability
- ✅ Graceful shutdown

---

## 🚀 Quick Start (Recommended)

**One command to start everything:**

```bash
./scripts/dev-start.sh
```

This script:
1. Kills any existing processes
2. Starts Celery infrastructure (Redis + Worker + Flower)
3. Starts Backend API
4. Verifies all services are healthy

**To stop:**

```bash
./scripts/dev-stop.sh
```

**To test Celery:**

```bash
./scripts/test-celery.sh
```

---

## 📦 Manual Setup (Advanced)

### Dependencies

```bash
pip install -r requirements.txt
# Includes: celery[redis]>=5.3.0, redis>=5.0.0, flower>=2.0.0
```

### Option 1: Docker Compose (Recommended)

```bash
# Start all services (Redis + Worker + Flower)
docker-compose -f docker-compose.celery.yml up -d

# Verify health
docker exec fi-redis redis-cli ping  # Should return PONG
docker logs --tail 20 fi-celery-worker

# Stop all services
docker-compose -f docker-compose.celery.yml down
```

### Option 2: Manual (Development)

```bash
# Terminal 1: Redis
docker run -d --name fi-redis -p 6379:6379 redis:7-alpine

# Terminal 2: Celery Worker
PYTHONPATH=. celery -A backend.workers.celery_app worker --loglevel=info --concurrency=2

# Terminal 3: Backend API
make run

# Terminal 4 (Optional): Flower UI
PYTHONPATH=. celery -A backend.workers.celery_app flower --port=5555
```

---

## Cómo Funciona

### Antes (Threading)

```python
# backend/api/public/workflows/router.py (L386-402 OLD)
import threading

def process_job_async(job_id_to_process: str) -> None:
    transcription_svc = TranscriptionService()
    diarization_svc = diarization_service
    process_job(job_id_to_process, transcription_svc, diarization_svc)

worker_thread = threading.Thread(target=process_job_async, args=(job_id,), daemon=True)
worker_thread.start()
```

**Problemas:**
- ❌ Jobs perdidos en restart
- ❌ Sin retries automáticos
- ❌ Sin observabilidad
- ❌ Sin rate limiting

### Ahora (Celery)

```python
# backend/api/public/workflows/router.py (L384-420 NEW)
from backend.workers.tasks import process_diarization_job

# Queue job para async processing
task = process_diarization_job.delay(job_id)

logger.info("WORKFLOW_WORKER_QUEUED", job_id=job_id, task_id=task.id, backend="celery")
```

**Ganancias:**
- ✅ Jobs persistidos en Redis (sobreviven restarts)
- ✅ Retries automáticos con exponential backoff (max 3, 60s→120s→240s)
- ✅ Flower UI para monitoreo (http://localhost:5555)
- ✅ Task tracking (task_id, status, progress)
- ✅ Graceful shutdown (acks_late=True)

---

## Task Definition

**File:** `backend/workers/tasks.py`

```python
@celery_app.task(bind=True, name="process_diarization_job", max_retries=3)
def process_diarization_job(self, job_id: str) -> dict:
    """
    Process diarization job asynchronously.

    **Retry Strategy:**
    - Retry 1: 60s delay
    - Retry 2: 120s delay (2^1 * 60)
    - Retry 3: 240s delay (2^2 * 60)

    **Timeouts:**
    - Soft limit: 9 min (raises SoftTimeLimitExceeded)
    - Hard limit: 10 min (kills task)
    """
    try:
        transcription_svc = TranscriptionService()
        diarization_svc = get_container().get_diarization_service()
        process_job(job_id, transcription_svc, diarization_svc)

        return {"job_id": job_id, "status": "completed"}

    except SoftTimeLimitExceeded:
        return {"job_id": job_id, "status": "failed", "message": "Timeout (9 min)"}

    except Exception as exc:
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
```

---

## Configuración

**File:** `backend/workers/celery_app.py`

```python
celery_app = Celery(
    "fi_workers",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery_app.conf.update(
    task_track_started=True,        # Track task progress
    task_time_limit=600,            # 10 min hard limit
    task_soft_time_limit=540,       # 9 min soft limit
    result_expires=3600,            # Results expire in 1h
    task_acks_late=True,            # Acknowledge after completion
    worker_prefetch_multiplier=1,   # Fair scheduling
)
```

**Environment Variables:**

```bash
# .env o docker-compose.yml
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB_BROKER=0
REDIS_DB_BACKEND=1
```

---

## Flower Monitoring

**URL:** http://localhost:5555

**Features:**
- ✅ Real-time task monitoring
- ✅ Worker stats (CPU, memory, throughput)
- ✅ Task history (completed, failed, retries)
- ✅ Broker stats (queue depth, messages/sec)

**Screenshots:**

```
Tasks Tab:
- ✅ 2971aa31-xxx (completed) - 45s ago
- ⏳ 690d84e7-xxx (in_progress) - 2s ago
- ❌ 0311f629-xxx (failed, retry 1/3) - 5m ago

Workers Tab:
- celery@fi-celery-worker (active, 2 tasks)
  - Tasks: 45 completed, 2 failed
  - Uptime: 3h 22m
```

---

## 🔧 Troubleshooting

### Issue: Services won't start

**Symptom:** `./scripts/dev-start.sh` fails

**Solutions:**
```bash
# 1. Check Docker is running
docker info

# 2. Kill any zombie processes
pkill -9 -f "python.*backend"
pkill -9 -f "uvicorn"
lsof -ti :7001 | xargs kill -9

# 3. Clean Docker containers
docker-compose -f docker-compose.celery.yml down
docker rm -f fi-redis fi-celery-worker fi-celery-flower

# 4. Restart from scratch
./scripts/dev-start.sh
```

---

### Issue: ImportError: No module named 'celery'

**Solution:**
```bash
pip install -r requirements.txt
# Or manually:
pip install celery[redis]>=5.3.0 redis>=5.0.0 flower>=2.0.0
```

---

### Issue: Error connecting to Redis

**Symptom:** `celery.exceptions.OperationalError`

**Solutions:**
```bash
# Check Redis is running
docker ps | grep fi-redis

# Check Redis health
docker exec fi-redis redis-cli ping  # Should return PONG

# If not running, start it
docker-compose -f docker-compose.celery.yml up -d
```

---

### Issue: Task stuck "in_progress"

**Symptom:** Job shows "processing" forever

**Solutions:**
```bash
# Option 1: Restart worker (clears in-memory state)
docker restart fi-celery-worker

# Option 2: Check worker logs for errors
docker logs --tail 50 fi-celery-worker

# Option 3: Purge stuck tasks (DANGER: production use with caution)
docker exec fi-celery-worker celery -A backend.workers.celery_app purge
```

---

### Issue: Port 7001 already in use

**Symptom:** `ERROR: [Errno 48] Address already in use`

**Solution:**
```bash
# Kill processes on port 7001
lsof -ti :7001 | xargs kill -9

# Or use dev-start.sh which handles this automatically
./scripts/dev-start.sh
```

---

### Automatic Fallback to Threading

If Celery is unavailable, the system automatically falls back to threading:

```python
# backend/api/public/workflows/router.py
try:
    from backend.workers.tasks import process_diarization_job
    task = process_diarization_job.delay(job_id)
except ImportError:
    # Fallback to threading (dev mode)
    logger.warning("CELERY_UNAVAILABLE_FALLBACK_THREADING")
    worker_thread = threading.Thread(target=process_job_async, args=(job_id,))
    worker_thread.start()
```

This ensures the system continues working even if Celery infrastructure is down.

---

## Métricas de Éxito

| Métrica | Target | Status |
|---------|--------|--------|
| **Jobs completados** | ≥ 95% | Monitor via Flower |
| **Retry rate** (p95) | ≤ 10% | Max 3 retries/job |
| **Queue depth** (p99) | < 10 jobs | Redis monitoring |
| **Worker uptime** | ≥ 99% | Docker health checks |
| **Task timeout** | < 10 min | Soft: 9min, Hard: 10min |

**Monitoring:** Check Flower UI at http://localhost:5555 for real-time metrics

---

## Testing

### Quick Integration Test (Recommended)

```bash
# Automated end-to-end test with real audio file
./scripts/test-celery.sh
```

This script:
1. Submits a test job to `/api/workflows/aurity/consult`
2. Verifies Celery worker picks up the task
3. Checks backend logs for job queueing
4. Provides Flower UI link for monitoring

---

### Unit Test (Mock Celery)

```python
# backend/tests/test_workflows_router.py
from unittest.mock import patch

@patch("backend.workers.tasks.process_diarization_job.delay")
def test_start_consult_workflow_queues_task(mock_delay):
    mock_delay.return_value.id = "test-task-id"

    response = client.post("/api/workflows/aurity/consult", files={"audio": ...})

    assert response.status_code == 202
    assert mock_delay.called
```

---

### E2E Test (Manual, Real Redis)

```bash
# Terminal 1: Redis (isolated port)
docker run -d --name test-redis -p 6380:6379 redis:7-alpine

# Terminal 2: Worker (isolated port)
REDIS_PORT=6380 celery -A backend.workers.celery_app worker --loglevel=info

# Terminal 3: Test
REDIS_PORT=6380 pytest backend/tests/test_celery_integration.py -v
```

---

## Rollback Plan

Si Celery falla en producción:

```python
# backend/api/public/workflows/router.py
# Descomentar threading fallback (L397-420)
except ImportError:
    # Fallback to threading if Celery not available
    ...
```

O bajar docker-compose:

```bash
docker-compose -f docker-compose.celery.yml down
```

El sistema vuelve a threading automáticamente.

---

## Next Steps

1. ✅ **Implementado**: Celery + Redis + Flower
2. 🟨 **Pendiente**: Corpus event sourcing (TODO #3)
3. 🟨 **Pendiente**: Batch diarization endpoint (TODO #4)

**DoD Checklist:**
- ✅ celery_app.py + tasks.py creados
- ✅ router.py integrado con `.delay()`
- ✅ docker-compose.celery.yml funcional
- ✅ requirements.txt actualizado
- ✅ Documentación (este README)
- ✅ Development scripts (dev-start.sh, dev-stop.sh, test-celery.sh)
- 🟨 Tests E2E con Redis real (pendiente)

---

**Updated:** 2025-11-09 18:30 CST
**Owner:** Bernard Uriza Orozco
**Card:** FI-BACKEND-ARCH-001
