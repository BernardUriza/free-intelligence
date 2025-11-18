"""
Free Intelligence - Authentication API Router
HIPAA Card: G-003 - JWT + RBAC middleware FastAPI
Author: Bernard Uriza Orozco
Created: 2025-11-17

FastAPI router for authentication endpoints (login, refresh, logout).
"""
from __future__ import annotations

from datetime import timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.dependencies import get_current_user
from backend.auth.jwt import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)
from backend.auth.models import (
    LoginRequest,
    RefreshTokenRequest,
    Token,
    User,
    UserPublic,
)
from backend.auth.rbac import export_rbac_matrix_csv
from backend.auth.user_store import get_user_by_id, get_users_db, init_demo_users

# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
)

logger = structlog.get_logger()


# ============================================================================
# Initialize Demo Users (Lazy)
# ============================================================================

_demo_users_initialized = False


def ensure_demo_users():
    """Lazy initialization of demo users (avoids bcrypt issues on module import)."""
    global _demo_users_initialized
    if not _demo_users_initialized:
        init_demo_users()
        _demo_users_initialized = True


# ============================================================================
# Authentication Endpoints
# ============================================================================


@router.post("/login", response_model=Token)
async def login(login_req: LoginRequest) -> Token:
    """
    Login endpoint: Authenticate user and return JWT tokens.

    **HIPAA Reference:** 45 CFR §164.312(d) - Person or Entity Authentication

    Args:
        login_req: Login credentials (username, password)

    Returns:
        Token: Access token (15min) + Refresh token (7 days)

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid

    Example:
        POST /api/auth/login
        {
            "username": "dr.mendoza",
            "password": "medico123"
        }

        Response:
        {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "token_type": "bearer",
            "expires_in": 900
        }
    """
    # Ensure demo users are initialized (lazy initialization)
    ensure_demo_users()

    # Authenticate user
    users_db = get_users_db()
    user = authenticate_user(users_db, login_req.username, login_req.password)

    if not user:
        logger.warning(
            "login_failed",
            username=login_req.username,
            reason="invalid_credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.user_id,
            "username": user.username,
            "role": user.role.value,
        },
        expires_delta=access_token_expires,
    )

    # Create refresh token
    refresh_token = create_refresh_token(
        data={
            "sub": user.user_id,
            "username": user.username,
            "role": user.role.value,
        }
    )

    logger.info(
        "login_success",
        user_id=user.user_id,
        username=user.username,
        role=user.role.value,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_req: RefreshTokenRequest) -> Token:
    """
    Refresh token endpoint: Exchange refresh token for new access token.

    This allows clients to get a new access token without re-authenticating
    when the 15-minute access token expires.

    Args:
        refresh_req: Refresh token request

    Returns:
        Token: New access token (15min) + same refresh token

    Raises:
        HTTPException: 401 Unauthorized if refresh token is invalid

    Example:
        POST /api/auth/refresh
        {
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
    """
    # Verify token type
    if not verify_token_type(refresh_req.refresh_token, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type (expected refresh token)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode refresh token
    token_data = decode_token(refresh_req.refresh_token)
    if token_data is None or token_data.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    user = get_user_by_id(token_data.user_id)
    if user is None or user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.user_id,
            "username": user.username,
            "role": user.role.value,
        },
        expires_delta=access_token_expires,
    )

    logger.info(
        "token_refreshed",
        user_id=user.user_id,
        username=user.username,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_req.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> UserPublic:
    """
    Get current user information (requires authentication).

    This endpoint demonstrates how to use the authentication dependency.

    Args:
        current_user: Current authenticated user (injected by Depends)

    Returns:
        UserPublic: Public user information (no password)

    Example:
        GET /api/auth/me
        Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

        Response:
        {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "username": "dr.mendoza",
            "email": "mendoza@hospital.mx",
            "full_name": "Dr. Carlos Mendoza",
            "role": "MEDICO"
        }
    """
    return UserPublic(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
    )


# ============================================================================
# RBAC Evidence Export (for HIPAA compliance)
# ============================================================================


@router.get("/rbac-matrix")
async def get_rbac_matrix() -> dict:
    """
    Export RBAC matrix as CSV for HIPAA compliance evidence.

    This endpoint generates the RBAC permission matrix showing
    which roles can perform which actions on which resources.

    Returns:
        dict: {"csv": "role,resource,action\\n..."}

    Example:
        GET /api/auth/rbac-matrix

        Response:
        {
            "csv": "role,resource,action\\nMEDICO,SOAP,read\\n..."
        }
    """
    csv_content = export_rbac_matrix_csv()
    return {"csv": csv_content}
