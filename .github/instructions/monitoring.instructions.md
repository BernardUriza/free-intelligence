---
applyTo: "backend/**/*.py,apps/**/*.ts,apps/**/*.tsx"
---

# Monitoring & Observability - AURITY

## SLOs (Service Level Objectives)

### Performance Targets

| Service | p95 Latency | Error Rate | Key Metrics |
|---------|-------------|------------|-------------|
| **PUBLIC API** | 800ms | < 1% | `requests_total`, `latency_ms_bucket`, `errors_total`, `rate_limited_total` |
| **RealtimeTalk** | 5000ms | < 1% | `asr_ms`, `llm_ms`, `tts_ms`, `total_ms` |
| **SOAP Generation** | 1500ms | < 1% | `soap_latency_ms`, `soap_failures_total` |

### SLO Breakdown - RealtimeTalk

```
Total p95 target: ≤ 5000ms

Component breakdown:
├─ ASR (Deepgram):        ~500ms  (10%)
├─ LLM (Claude/Qwen):    ~2000ms  (40%)
├─ TTS (Cartesia):        ~500ms  (10%)
├─ Network/Overhead:      ~500ms  (10%)
└─ Buffer/Processing:    ~1500ms  (30%)
```

## Structured Logging

### Required Fields

```python
import structlog

logger = structlog.get_logger(__name__)

# Every log entry must include:
logger.info(
    "event_name",
    # Correlation IDs (REQUIRED)
    session_id=session_id,
    workflow_id=workflow_id,
    idempotency_key=idempotency_key,

    # Performance metrics
    latency_ms=elapsed_ms,

    # User context (NO PHI/PII)
    user_id=user.id,

    # Request tracking
    request_id=request.headers.get("X-Request-ID"),
)
```

### Event Naming Convention

```python
# Pattern: {resource}_{action}_{status}

# ✅ CORRECT
logger.info("session_created", session_id=id)
logger.info("transcription_started", session_id=id, job_id=job_id)
logger.info("transcription_completed", session_id=id, duration_ms=elapsed)
logger.error("transcription_failed", session_id=id, error_code="E_TIMEOUT")

# ❌ WRONG - Too vague
logger.info("success")
logger.info("processing")
logger.error("failed")
```

### Performance Logging

```python
import time
from contextlib import contextmanager

@contextmanager
def measure_latency(operation: str, **context):
    """Context manager for measuring operation latency."""
    start = time.perf_counter()

    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            f"{operation}_latency",
            operation=operation,
            latency_ms=round(elapsed_ms, 2),
            **context
        )

# Usage
async def transcribe_audio(session_id: str, audio: bytes):
    with measure_latency("transcription", session_id=session_id):
        result = await deepgram_client.transcribe(audio)

    return result
```

## Metrics Collection

### Prometheus-Style Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Request counters
requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"]
)

# Latency histograms
latency_histogram = Histogram(
    "api_latency_seconds",
    "API request latency",
    ["endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Active sessions gauge
active_sessions = Gauge(
    "active_sessions_total",
    "Number of active sessions"
)

# Usage in endpoint
@router.post("/api/workflows/aurity/sessions")
async def create_session(request: SessionRequest):
    with latency_histogram.labels(endpoint="create_session").time():
        try:
            result = await session_service.create(request)
            requests_total.labels(
                method="POST",
                endpoint="create_session",
                status="success"
            ).inc()
            active_sessions.inc()
            return result

        except Exception as e:
            requests_total.labels(
                method="POST",
                endpoint="create_session",
                status="error"
            ).inc()
            raise
```

## Dashboards

### Key Dashboards (Grafana/Similar)

1. **API Latency Dashboard**
   - p50, p95, p99 latency by endpoint
   - Request rate (req/s)
   - Error rate (%)
   - Top 10 slowest endpoints

2. **Error Budget Dashboard**
   - SLO compliance per service
   - Error budget remaining
   - Incident timeline
   - MTTR (Mean Time To Recovery)

3. **Voice Pipeline Dashboard**
   - RealtimeTalk end-to-end latency
   - Component breakdown (ASR, LLM, TTS)
   - Dropout rate
   - Active voice sessions

## Alerting

### Alert Rules

```yaml
# Prometheus AlertManager config
groups:
  - name: slo_violations
    interval: 1m
    rules:
      - alert: PublicAPILatencyHigh
        expr: histogram_quantile(0.95, api_latency_seconds) > 0.8
        for: 3m
        labels:
          severity: page
        annotations:
          summary: "PUBLIC API p95 latency exceeded SLO"
          description: "p95 latency is {{ $value }}s (SLO: 800ms)"

      - alert: RealtimeTalkLatencyHigh
        expr: histogram_quantile(0.95, realtime_talk_latency_seconds) > 5.0
        for: 3m
        labels:
          severity: page
        annotations:
          summary: "RealtimeTalk p95 latency exceeded SLO"
          description: "p95 latency is {{ $value }}s (SLO: 5000ms)"

      - alert: ErrorRateHigh
        expr: rate(api_requests_total{status="error"}[5m]) > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Error rate exceeded 1%"
          description: "Current error rate: {{ $value | humanizePercentage }}"
```

## Distributed Tracing

### Correlation IDs

```python
from fastapi import Request
import uuid

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all requests."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

    # Inject into structlog context
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        request_id=str(uuid.uuid4())
    )

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id

    return response
```

### Tracing Workflow

```python
# Propagate IDs through workflow layers

# PUBLIC layer
@router.post("/api/workflows/aurity/sessions/{id}/transcribe")
async def start_transcription(id: str, workflow_id: str = None):
    workflow_id = workflow_id or str(uuid.uuid4())

    logger.info(
        "transcription_workflow_started",
        session_id=id,
        workflow_id=workflow_id
    )

    # Pass to INTERNAL layer
    return await internal_transcribe(id, workflow_id)

# INTERNAL layer
async def internal_transcribe(session_id: str, workflow_id: str):
    logger.info(
        "internal_transcription_started",
        session_id=session_id,
        workflow_id=workflow_id
    )

    # Submit to WORKER
    job_id = await worker_pool.submit(
        transcribe_task,
        session_id,
        workflow_id
    )

    return {"job_id": job_id, "workflow_id": workflow_id}

# WORKER layer
def transcribe_task(session_id: str, workflow_id: str):
    logger.info(
        "worker_transcription_started",
        session_id=session_id,
        workflow_id=workflow_id
    )

    # Perform transcription
    result = perform_transcription()

    logger.info(
        "worker_transcription_completed",
        session_id=session_id,
        workflow_id=workflow_id
    )

    return result
```

## Health Checks

### Endpoint Implementation

```python
from fastapi import status
from datetime import datetime, UTC

@router.get("/api/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "0.3.0"
    }

@router.get("/api/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependencies."""
    checks = {
        "database": await check_database(),
        "hdf5_storage": await check_hdf5_storage(),
        "deepgram": await check_deepgram(),
        "worker_pool": check_worker_pool(),
    }

    all_healthy = all(check["status"] == "healthy" for check in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks
    }
```

## Error Tracking

### Structured Error Logging

```python
import traceback
import sys

def log_exception(exc: Exception, context: dict):
    """Log exception with full context."""
    exc_type, exc_value, exc_traceback = sys.exc_info()

    logger.error(
        "exception_occurred",
        exc_type=exc_type.__name__,
        exc_message=str(exc_value),
        exc_traceback=traceback.format_tb(exc_traceback),
        **context
    )

# Usage
try:
    result = await risky_operation(session_id)
except Exception as e:
    log_exception(e, {
        "session_id": session_id,
        "operation": "risky_operation"
    })
    raise
```

## Success Checklist

- [ ] All logs include correlation IDs (session_id, workflow_id)
- [ ] Performance metrics collected (latency_ms)
- [ ] No PHI/PII in logs
- [ ] Event names follow {resource}_{action}_{status} pattern
- [ ] SLO targets configured for each service
- [ ] Alerts configured for SLO violations
- [ ] Health check endpoints implemented
- [ ] Error tracking with full context
- [ ] Dashboards created for key metrics
