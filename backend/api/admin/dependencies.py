"""Admin API Dependencies - FastAPI DI providers.

Provides IAuth0ManagementService dependency for admin routers.

Created: 2026-02-01 (Phase 2.3 K-Potasio - DI migration)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.infrastructure.auth.interfaces.iauth0_management import (
        IAuth0ManagementService,
    )


def get_auth0_service_dep() -> "IAuth0ManagementService":
    """Get Auth0 Management Service for admin endpoints.

    Returns:
        IAuth0ManagementService instance

    Note:
        Creates new instance per call. Auth0ManagementService handles
        token caching internally, so this is efficient.
    """
    from backend.infrastructure.auth.services.auth0_management import (
        Auth0ManagementService,
    )

    return Auth0ManagementService()
