from __future__ import annotations

"""
Free Intelligence - FastAPI Dependencies

Dependency injection providers for FastAPI routes and services.

File: backend/dependencies.py
Created: 2025-10-30
Purpose: Replace global singletons with DI pattern
"""

from backend.policy_enforcer import PolicyEnforcer


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
