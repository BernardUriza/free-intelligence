"""
Free Intelligence - Auth0 FastAPI Dependencies
HIPAA Card: G-003 - Auth0 OAuth2/OIDC Integration
Author: Bernard Uriza Orozco
Created: 2025-11-17

FastAPI dependency injection for Auth0 authentication.
Use Depends(get_current_user_auth0) to protect endpoints.
"""
from __future__ import annotations

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth.auth0_validator import (
    extract_user_email,
    extract_user_id,
    extract_user_roles,
    verify_auth0_token,
)
from backend.auth.models import User, UserRole

# ============================================================================
# FastAPI Security Scheme
# ============================================================================

# HTTP Bearer token scheme (Authorization: Bearer <token>)
security = HTTPBearer()

logger = structlog.get_logger()


# ============================================================================
# Auth0 Authentication Dependencies
# ============================================================================


async def get_current_user_auth0(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    FastAPI dependency: Validate Auth0 token and return current user.

    This validates the JWT token issued by Auth0, verifies the signature
    using Auth0's public keys (JWKS), and extracts user information.

    Usage:
        @app.get("/api/sessions/{id}/soap")
        async def get_soap(
            session_id: str,
            user: User = Depends(get_current_user_auth0)
        ):
            # user is now authenticated via Auth0
            logger.info("authenticated_request", user_id=user.user_id)
            ...

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User object with Auth0 user information

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate Auth0 credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract token from credentials
        token = credentials.credentials

        # Verify token with Auth0 (validates signature, expiration, issuer, audience)
        claims = verify_auth0_token(token)

        # Extract user information from token claims
        user_id = extract_user_id(claims)
        email = extract_user_email(claims)
        roles = extract_user_roles(claims)

        if not user_id:
            raise credentials_exception

        # Get primary role (first in list, or ENFERMERA as default)
        primary_role = roles[0] if roles else UserRole.ENFERMERA

        # Construct User object from Auth0 claims
        user = User(
            user_id=user_id,
            username=email or user_id,  # Use email as username, fallback to user_id
            email=email or "",
            full_name=claims.get("name", email or "Unknown"),
            role=primary_role,
            hashed_password="",  # Not used with Auth0 (Auth0 handles passwords)
            disabled=False,
        )

        logger.info(
            "auth0_authenticated",
            user_id=user.user_id,
            email=user.email,
            role=user.role.value,
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "auth0_validation_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise credentials_exception


async def get_current_active_user_auth0(
    current_user: User = Depends(get_current_user_auth0)
) -> User:
    """
    FastAPI dependency: Get current user and ensure account is active.

    Args:
        current_user: Current user from get_current_user_auth0 dependency

    Returns:
        User object if active

    Raises:
        HTTPException: 403 Forbidden if user is disabled
    """
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
    return current_user


# ============================================================================
# Role-Based Dependencies (Auth0 Version)
# ============================================================================


class RoleCheckerAuth0:
    """
    FastAPI dependency class: Check if Auth0 user has required role(s).

    Usage:
        @app.get("/api/admin/users")
        async def get_users(
            user: User = Depends(RoleCheckerAuth0([UserRole.ADMIN]))
        ):
            # user has ADMIN role (from Auth0 custom claims)
            ...
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user_auth0)) -> User:
        if user.role not in self.allowed_roles:
            allowed_roles_str = ", ".join([r.value for r in self.allowed_roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {allowed_roles_str}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


# ============================================================================
# Convenience Role Dependencies (Auth0 Version)
# ============================================================================


def require_medico_auth0(user: User = Depends(get_current_user_auth0)) -> User:
    """
    FastAPI dependency: Require user to be a MEDICO (via Auth0 custom claims).
    """
    if user.role != UserRole.MEDICO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires MEDICO role",
        )
    return user


def require_admin_auth0(user: User = Depends(get_current_user_auth0)) -> User:
    """
    FastAPI dependency: Require user to be an ADMIN (via Auth0 custom claims).
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires ADMIN role",
        )
    return user


def allow_medico_or_admin_auth0(user: User = Depends(get_current_user_auth0)) -> User:
    """
    FastAPI dependency: Allow MEDICO or ADMIN roles (via Auth0).
    """
    if user.role not in [UserRole.MEDICO, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires MEDICO or ADMIN role",
        )
    return user
