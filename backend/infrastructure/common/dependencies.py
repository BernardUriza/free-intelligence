from __future__ import annotations

"""
Free Intelligence - FastAPI Dependencies

Dependency injection providers for FastAPI routes and services.
Direct service instantiation - no service locator (Phase 4B).

File: backend/dependencies.py
Created: 2025-10-30
Updated: 2026-01-29 (Fix #1 - centralized config)
Purpose: Replace global singletons with DI pattern
"""

from backend.policy.policy_enforcer import PolicyEnforcer

# Import singleton factory from centralized location
from backend.infrastructure.common.repository_singletons import (
    get_task_repository,
)


def get_transcription_service():
    """Get TranscriptionService instance - direct instantiation (Phase 4B).

    Returns:
        TranscriptionService with injected task_repository

    Note:
        No longer uses service locator (get_container).
        Direct import to avoid circular dependencies.
    """
    from backend.services.transcription.services.transcription_service import (
        TranscriptionService,
    )

    return TranscriptionService(task_repository=get_task_repository())


def get_policy_enforcer(
    policy_path: str = "config/fi.policy.yaml",
    redaction_path: str = "config/redaction_style.yaml",
) -> PolicyEnforcer:
    """
    FastAPI dependency for PolicyEnforcer.

    Creates a new PolicyEnforcer instance with specified config paths.
    For performance-critical paths, consider caching at app startup.

    Args:
        policy_path: Path to policy YAML config
        redaction_path: Path to redaction style YAML

    Returns:
        PolicyEnforcer instance

    Usage:
        from fastapi import Depends

        def my_route(policy: PolicyEnforcer = Depends(get_policy_enforcer)):
            policy.check_egress("https://api.example.com")
    """
    return PolicyEnforcer(policy_path=policy_path, redaction_path=redaction_path)
