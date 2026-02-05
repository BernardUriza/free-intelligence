"""
Observability API - Public endpoints for metrics collection

Endpoints:
- POST /api/observability/audio/metrics - Receive frontend audio metrics
- GET /api/observability/audio/metrics - Get current metrics (JSON)
- GET /api/observability/audio/prometheus - Get metrics in Prometheus format

Module: fi_observability.api.public.observability
"""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend.utils.common.logging.logger import get_logger
from ...audio_metrics import audio_metrics

logger = get_logger(__name__)

router = APIRouter(prefix="/api/observability", tags=["observability"])


class FrontendAudioMetrics(BaseModel):
    """
    Frontend audio metrics payload

    Sent periodically from AudioPlayerProvider (every 60s)
    """

    cache_size: int
    cache_max: int
    queue_depth: int | None = 0
    cache_hit_rate: float | None = None
    timestamp: int


@router.post("/audio/metrics")
async def receive_audio_metrics(metrics: FrontendAudioMetrics):
    """
    Receive audio metrics from frontend

    Updates global metrics collector with frontend data.

    Args:
        metrics: Frontend audio metrics payload

    Returns:
        Success confirmation
    """
    # Update gauges
    audio_metrics.update_cache_size(metrics.cache_size)
    audio_metrics.update_queue_depth(metrics.queue_depth or 0)

    return {
        "status": "ok",
        "message": "Metrics received",
        "timestamp": metrics.timestamp,
    }


@router.get("/audio/metrics")
async def get_audio_metrics() -> dict[str, Any]:
    """
    Get current audio metrics in JSON format

    Returns:
        Dictionary with all current metrics
    """
    return audio_metrics.get_metrics_dict()


@router.get("/audio/prometheus", response_class=PlainTextResponse)
async def get_audio_metrics_prometheus():
    """
    Get audio metrics in Prometheus text format

    Returns:
        Prometheus exposition format (text/plain)
    """
    return audio_metrics.get_prometheus_format()


@router.post("/audio/events")
async def log_audio_event(event: dict[str, Any]):
    """
    Log audio event (errors, state transitions, etc.)

    Currently just logs to console. In production, would send to
    logging infrastructure (structlog, Sentry, etc.)

    Args:
        event: Audio event payload

    Returns:
        Success confirmation
    """
    logger.info(
        "AUDIO_EVENT",
        code=event.get("code", "UNKNOWN"),
        message=event.get("message", ""),
    )

    # Record error if it's an error event
    if "error" in event.get("code", "").lower():
        audio_metrics.record_error(event.get("code", "UNKNOWN_ERROR"))

    return {
        "status": "ok",
        "message": "Event logged",
    }
