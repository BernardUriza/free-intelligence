"""KPI API Dependencies - FastAPI DI providers.

Provides IKPIsAggregator dependency for KPI routers and middleware.

Python 2026 patterns:
- Type hints with `|` union syntax
- TYPE_CHECKING for lazy imports
- Module-level singleton (aggregator maintains in-memory state)

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/kpi/dependencies.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.kpi.interfaces.ikpis_aggregator import IKPIsAggregator

_aggregator_instance: "IKPIsAggregator | None" = None


def get_kpis_aggregator_dep() -> "IKPIsAggregator":
    """Get KPIs aggregator for API endpoints - singleton factory.

    Returns:
        IKPIsAggregator instance (singleton for metric continuity)

    Note:
        Unlike other DI factories, this returns a singleton because
        the KPIs aggregator maintains in-memory state (metric buckets).
        Each request should contribute to the same aggregator.
    """
    global _aggregator_instance

    if _aggregator_instance is None:
        from backend.services.kpi.services.kpis_aggregator import KPIsAggregator

        _aggregator_instance = KPIsAggregator()

    return _aggregator_instance
