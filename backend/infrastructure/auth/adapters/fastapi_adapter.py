from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from ..domain import User, UserRole
from ..infrastructure import load_auth0_config
from ..infrastructure.auth0.auth0_provider import DEFAULT_ROLE_PERMISSIONS
from ..infrastructure.middleware import (
    get_current_user,
    get_optional_current_user,
    require_permission,
    require_roles,
)

auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "roles": [role.value for role in current_user.roles],
        "tenant_id": current_user.tenant_id,
        "name": current_user.name,
    }


@auth_router.get("/config")
async def get_auth_config() -> dict:
    config = load_auth0_config()
    return {
        "domain": config.domain,
        "audience": config.audience,
        "issuer": config.issuer,
        "jwks_url": config.jwks_url,
        "roles_claim": config.roles_claim_key,
    }


@auth_router.get("/rbac-matrix")
async def rbac_matrix() -> dict:
    matrix = {role.value: sorted(perms) for role, perms in DEFAULT_ROLE_PERMISSIONS.items()}
    return {"roles": matrix}


@auth_router.get("/health")
async def auth_health() -> dict:
    config = load_auth0_config()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(config.jwks_url, timeout=5.0)
            response.raise_for_status()
            payload = response.json()
            keys_count = len(payload.get("keys", []))

        return {
            "status": "healthy",
            "jwks_url": config.jwks_url,
            "keys": keys_count,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Auth provider unhealthy: {exc}",
        ) from exc


__all__ = [
    "User",
    "UserRole",
    "auth_router",
    "get_current_user",
    "get_optional_current_user",
    "require_permission",
    "require_roles",
]
