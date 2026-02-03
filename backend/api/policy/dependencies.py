"""Policy API Dependencies - FastAPI DI providers.

Provides IPolicyLoader dependency for the policy router.

Created: 2026-02-01 (Phase 2.3 Urano - DI migration)
Updated: 2026-02-02 (Phase 2.3 Fase 6 - re-export canonical factory)
"""

from __future__ import annotations

# Phase 2.3 Fase 6: Re-export canonical factory from infrastructure.common.policy_provider
# This avoids circular imports and ensures singleton caching works globally.
from backend.infrastructure.common.policy_provider import get_policy_loader_dep

__all__ = ["get_policy_loader_dep"]
