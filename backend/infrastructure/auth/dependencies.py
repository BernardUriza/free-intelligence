"""FastAPI Dependency Injection providers for Auth infrastructure.

Provides singleton Gatekeeper dependency for authorization.

Author: Claude Code
Created: 2026-02-02 (Phase 2.3 - DI Refactor - Circular Import Fix)
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.infrastructure.auth.services.gatekeeper import Gatekeeper

# Import policy_loader from its canonical location to avoid circular imports
from backend.infrastructure.common.policy_provider import get_policy_loader_dep


@lru_cache(maxsize=1)
def _get_gatekeeper_singleton() -> "Gatekeeper":
    """Internal singleton factory for Gatekeeper."""
    from backend.infrastructure.auth.services.gatekeeper import Gatekeeper

    return Gatekeeper(policy_loader=get_policy_loader_dep())


def get_gatekeeper_dep() -> "Gatekeeper":
    """Get Gatekeeper singleton with injected dependencies.

    Phase 2.3 Fase 6: Replaces Gatekeeper() with no-args constructor.

    Returns:
        Gatekeeper singleton instance with policy_loader injected

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_gatekeeper_singleton()


__all__ = ["get_gatekeeper_dep"]
