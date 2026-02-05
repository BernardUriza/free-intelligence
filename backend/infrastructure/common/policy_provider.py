"""PolicyLoader dependency provider - extracted to avoid circular imports.

This module is imported by both:
- backend.services.llm.dependencies
- backend.services.workflow.dependencies
- backend.api.routers.llm.internal.llm.chat

Moving it here prevents circular import issues.

Author: Claude Code
Created: 2026-02-02
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.policy.interfaces.ipolicy_loader import IPolicyLoader


@lru_cache(maxsize=1)
def _get_policy_loader_singleton() -> "IPolicyLoader":
    """Internal singleton factory for PolicyLoader.

    Uses @lru_cache to ensure only ONE instance is created.

    Returns:
        IPolicyLoader singleton instance with policy loaded
    """
    from backend.policy.policy_loader import PolicyLoader

    loader = PolicyLoader()
    loader.load()
    return loader


def get_policy_loader_dep() -> "IPolicyLoader":
    """Get policy loader singleton for workers and endpoints.

    Returns:
        IPolicyLoader singleton (same instance for all calls)

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
        Single instance created on first call, reused thereafter.

    Note:
        Workers and endpoints receive this as a dependency via DI.
    """
    return _get_policy_loader_singleton()
