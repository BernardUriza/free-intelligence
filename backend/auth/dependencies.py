"""
Free Intelligence - FastAPI Authentication Dependencies
HIPAA Card: G-003 - JWT + RBAC middleware FastAPI
Author: Bernard Uriza Orozco
Created: 2025-11-17

FastAPI dependency injection for JWT authentication and RBAC.
Use Depends(get_current_user) to protect endpoints.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth.jwt import decode_token
from backend.auth.models import TokenData, User, UserRole
from backend.auth.user_store import get_user_by_id

# ============================================================================
# FastAPI Security Scheme
# ============================================================================

# HTTP Bearer token scheme (Authorization: Bearer <token>)
security = HTTPBearer()


# ============================================================================
# Authentication Dependencies
# ============================================================================


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    FastAPI dependency: Extract and validate JWT token, return current user.

    This is the main authentication dependency. Use it to protect endpoints:

    @app.get("/api/sessions/{id}/soap")
    async def get_soap(session_id: str, user: User = Depends(get_current_user)):
        # user is now authenticated
        ...

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User object if authentication succeeds

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Extract token from credentials
    token = credentials.credentials

    # Decode and validate token
    token_data: TokenData | None = decode_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    # Get user from database (or in-memory store for MVP)
    user = get_user_by_id(token_data.user_id)
    if user is None:
        raise credentials_exception

    # Check if user is disabled
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency: Get current user and ensure account is active.

    This is a stricter version of get_current_user that explicitly checks
    the disabled flag (though get_current_user already does this).

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        User object if active

    Raises:
        HTTPException: 403 Forbidden if user is disabled
    """
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


# ============================================================================
# Role-Based Dependencies
# ============================================================================


class RoleChecker:
    """
    FastAPI dependency class: Check if user has required role(s).

    Usage:
        @app.get("/api/admin/users")
        async def get_users(user: User = Depends(RoleChecker([UserRole.ADMIN]))):
            # user has ADMIN role
            ...
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            allowed_roles_str = ", ".join([r.value for r in self.allowed_roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {allowed_roles_str}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


# ============================================================================
# Convenience Role Dependencies
# ============================================================================


def require_medico(user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency: Require user to be a MEDICO.

    Usage:
        @app.post("/api/sessions/{id}/soap")
        async def create_soap(user: User = Depends(require_medico)):
            # user is MEDICO
            ...
    """
    if user.role != UserRole.MEDICO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires MEDICO role",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency: Require user to be an ADMIN.

    Usage:
        @app.delete("/api/sessions/{id}")
        async def delete_session(user: User = Depends(require_admin)):
            # user is ADMIN
            ...
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires ADMIN role",
        )
    return user


def allow_medico_or_admin(user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency: Allow MEDICO or ADMIN roles.

    Usage:
        @app.put("/api/sessions/{id}/soap")
        async def update_soap(user: User = Depends(allow_medico_or_admin)):
            # user is MEDICO or ADMIN
            ...
    """
    if user.role not in [UserRole.MEDICO, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires MEDICO or ADMIN role",
        )
    return user
