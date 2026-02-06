from __future__ import annotations

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...domain import IAuthProvider, User
from ...services.local_auth_provider import LocalAuthProvider
from ...services.local_token_service import LocalTokenService

logger = structlog.get_logger(__name__)

security = HTTPBearer(auto_error=False)
_provider: "IAuthProvider | None" = None


def _build_default_provider() -> LocalAuthProvider:
    token_service = LocalTokenService()
    return LocalAuthProvider(token_service=token_service)


def get_auth_provider() -> IAuthProvider:
    global _provider
    if _provider is None:
        _provider = _build_default_provider()
    return _provider


def set_auth_provider(provider: IAuthProvider) -> None:
    global _provider
    _provider = provider


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    provider: IAuthProvider = Depends(get_auth_provider),
) -> User:
    """Validate JWT token and return the authenticated user."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        user = await provider.validate_token(token)
    except Exception as exc:  # Convert provider errors into 401 to avoid 500 leaks
        logger.exception("Token validation failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    provider: IAuthProvider = Depends(get_auth_provider),
) -> User | None:
    """Return user if authenticated, None if onboarding mode or no token.

    Used for endpoints that support both authenticated and anonymous access.
    Onboarding flow uses X-Onboarding-Mode header to bypass auth.
    """
    # Check for onboarding bypass header
    if request.headers.get("X-Onboarding-Mode") == "true":
        logger.debug("Onboarding mode detected, allowing anonymous access")
        return None

    # No credentials = anonymous access
    if not credentials or not credentials.credentials:
        return None

    # Try to validate token, return None on failure (don't raise)
    try:
        user = await provider.validate_token(credentials.credentials)
        return user if user else None
    except Exception as exc:
        logger.debug("Token validation failed, allowing anonymous", error=str(exc))
        return None
