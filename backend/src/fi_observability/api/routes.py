# fi_observability/api/routes.py
# API routes for LLM observability

from dataclasses import asdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fi_observability.database import cleanup_old_records, get_db_stats
from fi_observability.logger import get_llm_logger
from fi_observability.models import CallStatus
from pydantic import BaseModel

router = APIRouter(prefix="/api/observability", tags=["observability"])


# Response models
class CallResponse(BaseModel):
    id: str
    timestamp: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    status: str
    error_message: Optional[str] = None
    prompt_preview: str
    response_preview: str
    client_id: Optional[str] = None
    session_id: Optional[str] = None
    persona: Optional[str] = None

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_calls: int
    success_calls: int
    error_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    calls_by_model: dict
    calls_by_client: dict


class ClientReportResponse(BaseModel):
    client_id: str
    period_start: str
    period_end: str
    total_calls: int
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    calls_by_model: dict
    calls_by_persona: dict
    avg_latency_ms: float
    error_rate: float
    estimated_cost_usd: float
    recent_calls: list


class DbStatsResponse(BaseModel):
    total_records: int
    db_size_bytes: int
    db_size_mb: float
    db_path: str
    oldest_record: Optional[str]
    newest_record: Optional[str]


# Routes

@router.get("/health")
async def health():
    """Health check for observability service."""
    return {"status": "ok", "service": "fi_observability"}


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
):
    """Get aggregated statistics for LLM calls."""
    logger = get_llm_logger()
    stats = logger.get_stats(hours=hours, client_id=client_id)

    return StatsResponse(
        total_calls=stats.total_calls,
        success_calls=stats.success_calls,
        error_calls=stats.error_calls,
        total_prompt_tokens=stats.total_prompt_tokens,
        total_completion_tokens=stats.total_completion_tokens,
        avg_latency_ms=stats.avg_latency_ms,
        p50_latency_ms=stats.p50_latency_ms,
        p95_latency_ms=stats.p95_latency_ms,
        calls_by_model=stats.calls_by_model,
        calls_by_client=stats.calls_by_client,
    )


@router.get("/calls/recent", response_model=list[CallResponse])
async def get_recent_calls(
    limit: int = Query(5, ge=1, le=100, description="Number of calls to return"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    model: Optional[str] = Query(None, description="Filter by model"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """Get most recent LLM calls."""
    logger = get_llm_logger()

    status_enum = None
    if status:
        try:
            status_enum = CallStatus(status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    calls = logger.get_recent_calls(
        limit=limit,
        client_id=client_id,
        model=model,
        status=status_enum,
    )

    return [
        CallResponse(
            id=c.id,
            timestamp=c.timestamp.isoformat(),
            model=c.model,
            provider=c.provider,
            prompt_tokens=c.prompt_tokens,
            completion_tokens=c.completion_tokens,
            latency_ms=c.latency_ms,
            status=c.status.value,
            error_message=c.error_message,
            prompt_preview=c.prompt_preview,
            response_preview=c.response_preview,
            client_id=c.client_id,
            session_id=c.session_id,
            persona=c.persona,
        )
        for c in calls
    ]


@router.get("/calls/{call_id}", response_model=CallResponse)
async def get_call(call_id: str):
    """Get a specific call by ID."""
    logger = get_llm_logger()
    call = logger.get_call(call_id)

    if not call:
        raise HTTPException(404, f"Call not found: {call_id}")

    return CallResponse(
        id=call.id,
        timestamp=call.timestamp.isoformat(),
        model=call.model,
        provider=call.provider,
        prompt_tokens=call.prompt_tokens,
        completion_tokens=call.completion_tokens,
        latency_ms=call.latency_ms,
        status=call.status.value,
        error_message=call.error_message,
        prompt_preview=call.prompt_preview,
        response_preview=call.response_preview,
        client_id=call.client_id,
        session_id=call.session_id,
        persona=call.persona,
    )


@router.get("/calls/search")
async def search_calls(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search calls by content."""
    logger = get_llm_logger()
    calls = logger.search_calls(query=q, limit=limit)

    return [
        CallResponse(
            id=c.id,
            timestamp=c.timestamp.isoformat(),
            model=c.model,
            provider=c.provider,
            prompt_tokens=c.prompt_tokens,
            completion_tokens=c.completion_tokens,
            latency_ms=c.latency_ms,
            status=c.status.value,
            error_message=c.error_message,
            prompt_preview=c.prompt_preview,
            response_preview=c.response_preview,
            client_id=c.client_id,
            session_id=c.session_id,
            persona=c.persona,
        )
        for c in calls
    ]


@router.get("/clients/{client_id}/report", response_model=ClientReportResponse)
async def get_client_report(
    client_id: str,
    days: int = Query(30, ge=1, le=365, description="Days to look back"),
):
    """Generate a detailed report for a client."""
    logger = get_llm_logger()
    report = logger.get_client_report(client_id=client_id, days=days)

    return ClientReportResponse(
        client_id=report.client_id,
        period_start=report.period_start.isoformat(),
        period_end=report.period_end.isoformat(),
        total_calls=report.total_calls,
        total_tokens=report.total_tokens,
        total_prompt_tokens=report.total_prompt_tokens,
        total_completion_tokens=report.total_completion_tokens,
        calls_by_model=report.calls_by_model,
        calls_by_persona=report.calls_by_persona,
        avg_latency_ms=report.avg_latency_ms,
        error_rate=report.error_rate,
        estimated_cost_usd=report.estimated_cost_usd,
        recent_calls=[
            CallResponse(
                id=c.id,
                timestamp=c.timestamp.isoformat(),
                model=c.model,
                provider=c.provider,
                prompt_tokens=c.prompt_tokens,
                completion_tokens=c.completion_tokens,
                latency_ms=c.latency_ms,
                status=c.status.value,
                error_message=c.error_message,
                prompt_preview=c.prompt_preview,
                response_preview=c.response_preview,
                client_id=c.client_id,
                session_id=c.session_id,
                persona=c.persona,
            )
            for c in report.recent_calls
        ],
    )


@router.get("/db/stats", response_model=DbStatsResponse)
async def get_database_stats():
    """Get database statistics."""
    stats = get_db_stats()
    return DbStatsResponse(**stats)


@router.post("/db/cleanup")
async def cleanup_database(
    days: int = Query(30, ge=7, le=365, description="Keep records newer than N days"),
):
    """Clean up old records from the database."""
    deleted = cleanup_old_records(days=days)
    return {"deleted": deleted, "kept_days": days}
