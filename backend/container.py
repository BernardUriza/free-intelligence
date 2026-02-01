"""Backend container module.

DEPRECATED: This module is deprecated as of Phase 2.3 Plutón.

Use FastAPI Depends() with factories from:
- backend.services.workflow.dependencies
- backend.api.policy.dependencies
- backend.api.routers.kpi.dependencies
- backend.domain.session.dependencies

Updated: 2026-02-01 (Phase 2.3 Plutón - marked as deprecated)
"""

from __future__ import annotations

import warnings

from backend.infrastructure.common.container import Container


def get_container() -> Container:
    """DEPRECATED: Get the application dependency injection container.

    ⚠️  This function is DEPRECATED. Use FastAPI Depends() with DI factories:
    - get_task_repository() from backend.domain.session.dependencies
    - get_policy_loader_dep() from backend.api.policy.dependencies
    - get_kpis_aggregator_dep() from backend.api.routers.kpi.dependencies

    .. deprecated::
        Phase 2.3 Plutón - use specific DI factories instead of this container.
    """
    warnings.warn(
        "get_container() is deprecated. Use specific DI factories from "
        "backend.services.workflow.dependencies or domain-specific dependencies modules",
        DeprecationWarning,
        stacklevel=2,
    )
    return Container()
