"""KPI Infrastructure Module.

Provides KPI aggregation and metrics endpoints for system monitoring.

Architecture:
- api/internal/router.py: Internal KPI endpoints (no auth required)
- api/public/kpis.py: Public KPI endpoints (auth required)
- dependencies.py: DI factory for IKPIsAggregator

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/kpi/
"""
