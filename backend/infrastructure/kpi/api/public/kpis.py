"""Public KPIs API Router.

Provides system metrics and performance KPIs for AURITY dashboard.

Python 2026 patterns:
- Annotated[T, Depends(...)] for cleaner dependency injection
- `|` union syntax for type hints
- Literal types for constrained string values
- match/case for cleaner branching

Architecture: PUBLIC (auth required) -> KPIsAggregator service

Endpoints:
- GET /kpis - Get KPIs for authenticated users

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/kpi/public/kpis.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.infrastructure.kpi.dependencies import get_kpis_aggregator_dep
from backend.utils.common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.services.kpi.interfaces.ikpis_aggregator import IKPIsAggregator

logger = get_logger(__name__)

router = APIRouter(prefix="/kpis", tags=["kpis"])

type TimeWindow = Literal["1m", "5m", "15m", "1h", "24h"]
type ViewMode = Literal["summary", "chips", "timeseries"]


@router.get("")
async def get_kpis(
    aggregator: Annotated["IKPIsAggregator", Depends(get_kpis_aggregator_dep)],
    audit_service: Annotated[DIAuditService, Depends(get_audit_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    window: TimeWindow = Query("5m", description="Time window: 1m, 5m, 15m, 1h, 24h"),
    view: ViewMode = Query("summary", description="View: summary, chips, timeseries"),
    route: str | None = Query(None, description="Filter by route (e.g., /api/sessions)"),
    provider: str | None = Query(None, description="Filter by provider (e.g., anthropic)"),
):
    """Get KPIs metrics (PUBLIC endpoint for dashboard).

    Args:
        aggregator: KPIs aggregator service (injected)
        audit_service: Audit service (injected)
        current_user: Authenticated user (injected)
        window: Time window (1m, 5m, 15m, 1h, 24h) - default 5m
        view: Output format (summary, chips, timeseries) - default summary
        route: Filter by route (optional)
        provider: Filter by provider (optional)

    Returns:
        KPIs data in requested format

    Examples:
        GET /api/aurity/kpis?window=5m&view=summary
        GET /api/aurity/kpis?window=5m&view=chips
        GET /api/aurity/kpis?window=15m&view=timeseries
        GET /api/aurity/kpis?window=5m&provider=anthropic
    """
    try:
        logger.info(
            "KPIS_API_REQUEST",
            window=window,
            view=view,
            route_filter=route,
            provider_filter=provider,
            user_id=current_user.id,
        )

        match view:
            case "summary":
                return aggregator.get_summary(
                    window=window,
                    route_filter=route,
                    provider_filter=provider,
                )
            case "chips":
                return aggregator.get_chips(window=window)
            case "timeseries":
                return aggregator.get_timeseries(window=window)

    except ValueError as e:
        logger.warning("KPIS_VALIDATION_FAILED", error=str(e), window=window, view=view)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        audit_service.log_action(
            action="kpis_export_failed",
            user_id=current_user.id,
            resource="kpis",
            result="failure",
            details={"error": str(e), "window": window, "view": view},
        )
        raise HTTPException(status_code=500, detail="Failed to aggregate metrics") from e
