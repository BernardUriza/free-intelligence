"""Public KPIs API Router.

Provides system metrics and performance KPIs for AURITY dashboard.

Architecture: PUBLIC → KPIsAggregator service (internal)
Created: 2025-11-17
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.logger import get_logger
from backend.services.kpis_aggregator import get_kpis_aggregator

logger = get_logger(__name__)

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("")
async def get_kpis(
    window: str = Query("5m", description="Time window: Union[1m, 5m, 15m]|Union[1h, 24h]"),
    view: str = Query("summary", description="View: Union[summary, chips, timeseries]"),
    route: Optional[str] = Query(None, description="Filter by route (e.g., /api/sessions)"),
    provider: Optional[str] = Query(None, description="Filter by provider (e.g., anthropic)"),
):
    """
    Get KPIs metrics (PUBLIC endpoint for dashboard).

    Args:
        window: Time window (1m, 5m, 15m, 1h, 24h) - default 5m
        view: Output format (summary, chips, timeseries) - default summary
        route: Filter by route (optional)
        provider: Filter by provider (optional)

    Returns:
        KPIs data in requested format

    Examples:
        GET /api/workflows/aurity/kpis?window=5m&view=summary
        GET /api/workflows/aurity/kpis?window=5m&view=chips
        GET /api/workflows/aurity/kpis?window=15m&view=timeseries
        GET /api/workflows/aurity/kpis?window=5m&provider=anthropic
    """
    # Validate window parameter
    valid_windows = {"1m", "5m", "15m", "1h", "24h"}
    if window not in valid_windows:
        logger.warning("KPIS_INVALID_WINDOW", window=window)
        raise HTTPException(
            status_code=400, detail=f"Invalid window. Must be one of: {', '.join(valid_windows)}"
        )

    try:
        aggregator = get_kpis_aggregator()

        logger.info(
            "KPIS_API_REQUEST",
            window=window,
            view=view,
            route_filter=route,
            provider_filter=provider,
        )

        if view == "summary":
            return aggregator.get_summary(
                window=window,
                route_filter=route,
                provider_filter=provider,
            )
        elif view == "chips":
            return aggregator.get_chips(window=window)
        elif view == "timeseries":
            return aggregator.get_timeseries(window=window)
        else:
            logger.warning("KPIS_INVALID_VIEW", view=view, fallback="summary")
            return aggregator.get_summary(window=window)

    except ValueError as e:
        logger.warning("KPIS_VALIDATION_FAILED", error=str(e), window=window, view=view)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("KPIS_AGGREGATION_FAILED", error=str(e), window=window, view=view)
        raise HTTPException(status_code=500, detail="Failed to aggregate metrics") from e
