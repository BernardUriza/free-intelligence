"""Celery Application Configuration.

Card: FI-BACKEND-ARCH-001 (TODO #1)

Provides production-grade background task processing with:
- Redis broker for task queue
- Redis backend for result storage
- Task tracking and monitoring
- Automatic retries with exponential backoff
- Timezone support (America/Mexico_City)

File: backend/workers/celery_app.py
Created: 2025-11-09
"""

from __future__ import annotations

import os

from celery import Celery, signals

# Redis configuration from environment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB_BROKER = int(os.getenv("REDIS_DB_BROKER", "0"))
REDIS_DB_BACKEND = int(os.getenv("REDIS_DB_BACKEND", "1"))

BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_BROKER}"
BACKEND_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_BACKEND}"

# Create Celery app
celery_app = Celery(
    "fi_workers",
    broker=BROKER_URL,
    backend=BACKEND_URL,
)

# Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="America/Mexico_City",
    enable_utc=True,
    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,
    # Time limits (prevent zombie tasks)
    task_time_limit=600,  # 10 min hard limit
    task_soft_time_limit=540,  # 9 min soft limit (raises SoftTimeLimitExceeded)
    # Result expiration
    result_expires=3600,  # 1 hour
    # Worker configuration
    worker_prefetch_multiplier=1,  # Fair scheduling (1 task per worker at a time)
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (memory leak prevention)
    # Retry configuration
    task_acks_late=True,  # Acknowledge after task completion (ensures retry on failure)
    task_reject_on_worker_lost=True,  # Requeue task if worker crashes
)

# Auto-discover tasks in backend.workers.tasks module
celery_app.autodiscover_tasks(["backend.workers"])


# Worker process initialization signal - warm up heavy services
@signals.worker_process_init.connect
def warmup_worker(**kwargs) -> None:
    """
    Warm-up heavy singleton services when worker process starts.

    This runs ONCE per worker fork, NOT per task.
    Prevents deadlocks from initializing ML models in task execution.
    """
    from backend.workers import warmup_worker_services

    warmup_worker_services()
