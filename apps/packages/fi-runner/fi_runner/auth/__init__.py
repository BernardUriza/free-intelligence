"""fi-runner auth — opt-in Auth0 (RS256/JWKS) token validation for consumers.

The framework's reusable identity layer: a consumer (e.g. a FastAPI app) builds
an ``Auth0Validator`` from its tenant config and gates routes with the dependency
from ``make_auth_dependency``, getting back a verified ``Principal``. Requires the
``auth`` extra (``fi-runner[auth]`` → PyJWT + cryptography). The framework stays
strictly more capable: nothing here is imported unless the consumer opts in.
"""

from __future__ import annotations

from .auth0 import AuthConfig, AuthError, Auth0Validator
from .fastapi import make_auth_dependency
from .principal import LEGACY_BEARER_SUB, Principal, legacy_principal

__all__ = [
    "AuthConfig",
    "AuthError",
    "Auth0Validator",
    "Principal",
    "LEGACY_BEARER_SUB",
    "legacy_principal",
    "make_auth_dependency",
]
