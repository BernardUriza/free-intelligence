"""Celery application instance.

Asynchronous task queue for Free Intelligence.

File: backend/app/celery_app.py
Card: AUR-PROMPT-3.1
Created: 2025-11-09
"""

from __future__ import annotations

import os

from celery import Celery

# Read broker/backend from environment
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "free_intelligence",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["backend.app.tasks"],
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Mexico_City",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 min soft limit
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
)
