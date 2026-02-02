"""Prometheus metrics - Observability for production SLOs.

Philosophy:
  - Observability = measure everything that matters
  - SLOs require metrics (latency, error rate, throughput)
  - Prometheus = industry standard for metrics
  - Dashboards require structured metrics

Architecture:
  - Counter: monotonic increasing (requests, errors, events)
  - Histogram: distributions (latency, duration)
  - Gauge: point-in-time values (queue depth, in-progress)
  - Summary: percentiles (p50, p95, p99)

Metrics:
  - http_requests_total{method, endpoint, status}
  - http_request_duration_seconds{method, endpoint}
  - workflow_tasks_total{task_type, status}
  - workflow_task_duration_seconds{task_type}
  - circuit_breaker_state{name, state}
  - llm_requests_total{provider, model}
  - llm_request_duration_seconds{provider, model}

Created: 2025-12-03
Pattern: Prometheus Metrics + Structured Observability
"""

from __future__ import annotations

from backend.utils.common.logging.logger import get_logger
from prometheus_client import Counter, Gauge, Histogram

logger = get_logger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HTTP METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Total HTTP requests
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

# HTTP request duration (histogram for percentiles)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0],
)

# HTTP requests in progress
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WORKFLOW METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Workflow task completions
workflow_tasks_total = Counter(
    "workflow_tasks_total",
    "Total workflow tasks completed",
    ["task_type", "status"],
)

# Workflow task duration
workflow_task_duration_seconds = Histogram(
    "workflow_task_duration_seconds",
    "Workflow task duration in seconds",
    ["task_type"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# Workflow tasks in progress
workflow_tasks_in_progress = Gauge(
    "workflow_tasks_in_progress",
    "Workflow tasks currently executing",
    ["task_type"],
)

# Workflow completion rate (workflows with all tasks done)
workflow_completions_total = Counter(
    "workflow_completions_total",
    "Total workflow completions (all tasks done)",
    ["status"],  # completed, failed, partial
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM PROVIDER METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# LLM API calls
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"],
)

# LLM request duration
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM API request latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0],
)

# LLM token usage
llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["provider", "model", "token_type"],  # prompt, completion, total
)

# LLM requests in progress
llm_requests_in_progress = Gauge(
    "llm_requests_in_progress",
    "LLM requests currently in progress",
    ["provider", "model"],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CIRCUIT BREAKER METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Circuit breaker state (0=closed, 1=half_open, 2=open)
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["name"],
)

# Circuit breaker transitions
circuit_breaker_transitions_total = Counter(
    "circuit_breaker_transitions_total",
    "Circuit breaker state transitions",
    ["name", "from_state", "to_state"],
)

# Circuit breaker rejections (calls rejected due to open circuit)
circuit_breaker_rejections_total = Counter(
    "circuit_breaker_rejections_total",
    "Calls rejected by circuit breaker",
    ["name"],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STORAGE METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# HDF5 operations
hdf5_operations_total = Counter(
    "hdf5_operations_total",
    "Total HDF5 operations",
    ["operation", "status"],  # operation: read, write, delete
)

# HDF5 operation duration
hdf5_operation_duration_seconds = Histogram(
    "hdf5_operation_duration_seconds",
    "HDF5 operation duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# Session file count
session_files_total = Gauge(
    "session_files_total",
    "Total session HDF5 files",
)

# Session file size
session_files_size_bytes = Gauge(
    "session_files_size_bytes",
    "Total size of session HDF5 files in bytes",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IDEMPOTENCY METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Idempotency cache hits
idempotency_cache_hits_total = Counter(
    "idempotency_cache_hits_total",
    "Idempotency cache hits (duplicate requests prevented)",
    ["path"],
)

# Idempotency cache misses
idempotency_cache_misses_total = Counter(
    "idempotency_cache_misses_total",
    "Idempotency cache misses (new requests)",
    ["path"],
)

# Idempotency cache size
idempotency_cache_size = Gauge(
    "idempotency_cache_size",
    "Current idempotency cache size (number of entries)",
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RETRY METRICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Retry attempts
retry_attempts_total = Counter(
    "retry_attempts_total",
    "Total retry attempts",
    ["function", "attempt"],
)

# Retry successes (succeeded after retry)
retry_successes_total = Counter(
    "retry_successes_total",
    "Successful retries (operation succeeded after failure)",
    ["function"],
)

# Retry exhaustion (all retries failed)
retry_exhausted_total = Counter(
    "retry_exhausted_total",
    "Exhausted retries (all attempts failed)",
    ["function"],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# METRICS ENDPOINT SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def setup_metrics_endpoint(app):
    """
    Add /metrics endpoint to FastAPI app for Prometheus scraping.

    Usage:
        from backend.app.main import create_app
        from backend.utils.metrics import setup_metrics_endpoint

        app = create_app()
        setup_metrics_endpoint(app)

    Prometheus config:
        scrape_configs:
          - job_name: 'free-intelligence'
            static_configs:
              - targets: ['localhost:7001']
            metrics_path: '/metrics'
    """
    from fastapi import Response
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    logger.info("METRICS_ENDPOINT_REGISTERED", path="/metrics")
