"""FastAPI dependency factory for the auth layer.

The dual-accept (Auth0 JWT OR a legacy shared bearer) lives HERE as a
configurable level so a consumer can cut over without downtime: pass
``legacy_bearer`` during transition (a matching bearer yields the synthetic
legacy principal), drop it for Auth0-only. FastAPI is imported lazily so a
non-FastAPI consumer of fi-runner.auth never pays for it.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable

from .auth0 import Auth0Validator, AuthError
from .principal import Principal, legacy_principal


def make_auth_dependency(
    validator: Auth0Validator | None,
    *,
    legacy_bearer: str | None = None,
) -> Callable[..., Principal]:
    """Build a FastAPI dependency that returns the authenticated ``Principal``.

    A request authenticates if EITHER its bearer matches ``legacy_bearer`` (when
    set — the transition path) OR it carries a valid Auth0 JWT. Otherwise 401.
    """
    from fastapi import Header, HTTPException

    def _unauthorized() -> HTTPException:
        return HTTPException(status_code=401, detail="invalid or missing credentials")

    def dependency(authorization: str | None = Header(default=None)) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise _unauthorized()
        token = authorization[len("Bearer ") :]
        if legacy_bearer is not None and hmac.compare_digest(token, legacy_bearer):
            return legacy_principal()
        if validator is None:
            raise _unauthorized()
        try:
            return validator.validate(token)
        except AuthError:
            raise _unauthorized() from None

    return dependency
