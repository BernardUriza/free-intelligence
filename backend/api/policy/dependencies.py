"""Policy API Dependencies - FastAPI DI providers.

Provides IPolicyLoader dependency for the policy router.
Separated to avoid circular imports with workflow dependencies.

Created: 2026-02-01 (Phase 2.3 Urano - DI migration)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.policy.interfaces.ipolicy_loader import IPolicyLoader


def get_policy_loader_dep() -> "IPolicyLoader":
    """Get policy loader for API endpoints - direct instantiation.

    Returns:
        IPolicyLoader instance with policy already loaded

    Note:
        This is a local copy of the factory to avoid circular imports.
        The policy router imports this directly instead of from workflow.dependencies.
    """
    from backend.policy.policy_loader import PolicyLoader

    loader = PolicyLoader()
    loader.load()
    return loader
