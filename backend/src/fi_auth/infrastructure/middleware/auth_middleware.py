from __future__ import annotations

import os
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...domain import IAuthProvider, User, UserRole
from ...infrastructure.auth0 import Auth0Provider, load_auth0_config
from ...infrastructure.jwt import JWKSFetcher, JWTValidator

logger = structlog.get_logger(__name__)

security = HTTPBearer(auto_error=False)
_provider: "IAuthProvider | None" = None


def _build_default_provider() -> Auth0Provider:
    config = load_auth0_config()
    jwks_fetcher = JWKSFetcher(config.jwks_url)
    token_service = JWTValidator(
        issuer=config.issuer,
        audience=config.audience,
        algorithms=config.algorithms,
        roles_claim_key=config.roles_claim_key,
        jwks_fetcher=jwks_fetcher,
    )
    return Auth0Provider(config=config, token_service=token_service)


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
) -> User:
    # Offline desktop mode: allow bypass when DESKTOP_OFFLINE=1 or AUTH_OFFLINE_BYPASS=1
    desktop_offline = os.getenv("DESKTOP_OFFLINE") or os.getenv("AUTH_OFFLINE_BYPASS")
    if desktop_offline and desktop_offline.lower() in ("1", "true", "yes"):
        logger.info("Using offline desktop auth bypass (DESKTOP_OFFLINE enabled)")
        # Create a synthetic local user for desktop mode
        roles = [UserRole.CLINICIAN]
        return User(id="desktop|local", email="local@desktop.local", roles=roles, name="Local Desktop User")

    # Get the auth provider (lazy initialization)
    provider = get_auth_provider()

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
