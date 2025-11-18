"""
Free Intelligence - Auth0 API Router
HIPAA Card: G-003 - Auth0 OAuth2/OIDC Integration
Author: Bernard Uriza Orozco
Created: 2025-11-17

FastAPI router for Auth0 authentication endpoints.
NOTE: Auth0 handles login/logout (not the backend).
This router provides user info and configuration endpoints.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.auth0_config import (
    AUTH0_API_IDENTIFIER,
    AUTH0_CLIENT_ID,
    AUTH0_DOMAIN,
    FRONTEND_URL_DEV,
    FRONTEND_URL_PROD,
    validate_config,
)
from backend.auth.auth0_dependencies import get_current_user_auth0
from backend.auth.models import User, UserPublic
from backend.auth.rbac import export_rbac_matrix_csv

# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
)

logger = structlog.get_logger()


# Validate Auth0 config on module load
try:
    validate_config()
except ValueError as e:
    logger.error("auth0_config_invalid", error=str(e))


# ============================================================================
# Auth0 Endpoints
# ============================================================================


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(current_user: User = Depends(get_current_user_auth0)) -> UserPublic:
    """
    Get current user information (requires Auth0 authentication).

    This endpoint demonstrates Auth0 token validation.
    The user's information is extracted from the Auth0 JWT token.

    **Auth Flow:**
    1. Frontend authenticates with Auth0 Universal Login
    2. Auth0 returns access_token
    3. Frontend sends token in Authorization: Bearer header
    4. Backend validates token with Auth0 JWKS

    Args:
        current_user: Current authenticated user (injected by Depends)

    Returns:
        UserPublic: Public user information (no password)

    Example:
        ```bash
        curl -H "Authorization: Bearer $ACCESS_TOKEN" \\
             https://fi-aurity.duckdns.org/api/auth/me
        ```

        Response:
        ```json
        {
            "user_id": "auth0|507f1f77bcf86cd799439011",
            "username": "doctor@hospital.com",
            "email": "doctor@hospital.com",
            "full_name": "Dr. Carlos Mendoza",
            "role": "MEDICO"
        }
        ```
    """
    logger.info(
        "user_info_requested",
        user_id=current_user.user_id,
        role=current_user.role.value,
    )

    return UserPublic(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
    )


@router.get("/config")
async def get_auth0_config() -> dict:
    """
    Get Auth0 configuration for frontend (public information only).

    This endpoint provides the frontend with the necessary Auth0 configuration
    to initiate the authentication flow.

    **Security Note:** Only public configuration is exposed.
    Client Secret is never returned.

    Returns:
        dict: Auth0 public configuration

    Example:
        ```bash
        curl https://fi-aurity.duckdns.org/api/auth/config
        ```

        Response:
        ```json
        {
            "domain": "dev-1r4daup7ofj7q6gn.auth0.com",
            "clientId": "rYOowVCxSqeSNFVOFsZuVIiYsjw4wkKp",
            "audience": "https://api.fi-aurity.duckdns.org",
            "redirectUri": "https://fi-aurity.duckdns.org/callback",
            "scope": "openid profile email"
        }
        ```
    """
    return {
        "domain": AUTH0_DOMAIN,
        "clientId": AUTH0_CLIENT_ID,
        "audience": AUTH0_API_IDENTIFIER,
        "redirectUri": f"{FRONTEND_URL_PROD}/callback",
        "redirectUriDev": f"{FRONTEND_URL_DEV}/callback",
        "scope": "openid profile email",
        "responseType": "code",  # Authorization Code Flow (most secure)
    }


@router.get("/rbac-matrix")
async def get_rbac_matrix() -> dict:
    """
    Export RBAC matrix as CSV for HIPAA compliance evidence.

    This endpoint generates the RBAC permission matrix showing
    which roles can perform which actions on which resources.

    **HIPAA Reference:** 45 CFR §164.308(a)(4) - Access Management

    Returns:
        dict: {"csv": "role,resource,action\\n..."}

    Example:
        ```bash
        curl https://fi-aurity.duckdns.org/api/auth/rbac-matrix
        ```

        Response:
        ```json
        {
            "csv": "role,resource,action\\nMEDICO,SOAP,read\\n..."
        }
        ```
    """
    csv_content = export_rbac_matrix_csv()
    return {"csv": csv_content}


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint for Auth0 integration.

    Verifies that Auth0 configuration is valid and JWKS is accessible.

    Returns:
        dict: Health status

    Example:
        ```bash
        curl https://fi-aurity.duckdns.org/api/auth/health
        ```

        Response:
        ```json
        {
            "status": "healthy",
            "auth0_domain": "dev-1r4daup7ofj7q6gn.auth0.com",
            "jwks_url": "https://dev-1r4daup7ofj7q6gn.auth0.com/.well-known/jwks.json"
        }
        ```
    """
    from backend.auth.auth0_config import JWKS_URL

    # Test JWKS fetch
    try:
        from backend.auth.auth0_validator import get_jwks

        jwks = get_jwks()
        keys_count = len(jwks.get("keys", []))

        return {
            "status": "healthy",
            "auth0_domain": AUTH0_DOMAIN,
            "jwks_url": JWKS_URL,
            "jwks_keys_count": keys_count,
        }
    except Exception as e:
        logger.error("auth0_health_check_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Auth0 integration unhealthy: {e!s}",
        )
