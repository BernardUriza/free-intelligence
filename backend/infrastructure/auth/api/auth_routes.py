"""Auth API routes for self-hosted authentication.

POST /auth/login     - Login with email/password
POST /auth/register  - Register new account
POST /auth/refresh   - Refresh access token
POST /auth/logout    - Revoke refresh token
GET  /auth/me        - Current user info
GET  /auth/rbac-matrix - Role-permission matrix
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.database import get_db_dependency

from ..domain import User, UserRole
from ..domain.constants import DEFAULT_ROLE_PERMISSIONS
from ..domain.entities.db_user import DBUser
from ..domain.entities.refresh_token_model import DBRefreshToken
from ..infrastructure.middleware import get_current_user
from ..services.local_token_service import LocalTokenService
from ..services.user_service import UserService

logger = structlog.get_logger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["authentication"])


def _get_token_service() -> LocalTokenService:
    """Get the singleton LocalTokenService."""
    from ..infrastructure.middleware.auth_middleware import get_auth_provider

    provider = get_auth_provider()
    return provider.token_service


# ── Request / Response Schemas ──────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ── Helpers ─────────────────────────────────────────────────────────────────


def _issue_tokens(
    user: DBUser,
    token_service: LocalTokenService,
    db: Session,
    device_info: str | None = None,
) -> TokenResponse:
    """Create access + refresh tokens for a user and persist the refresh token."""
    role = UserRole.coerce(user.role) or UserRole.CLINICIAN
    access = token_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=[role],
        clinic_id=user.clinic_id,
        name=user.name,
    )

    raw_refresh, token_hash, expires_at = token_service.create_refresh_token()

    db_token = DBRefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=device_info,
    )
    db.add(db_token)
    db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=token_service.access_ttl,
    )


# ── Endpoints ───────────────────────────────────────────────────────────────


@auth_router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db_dependency)) -> TokenResponse:
    svc = UserService(db)
    user = svc.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    ts = _get_token_service()
    return _issue_tokens(user, ts, db)


@auth_router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: Session = Depends(get_db_dependency)) -> TokenResponse:
    svc = UserService(db)
    try:
        user = svc.register(body.email, body.password, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    ts = _get_token_service()
    return _issue_tokens(user, ts, db)


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: Session = Depends(get_db_dependency)) -> TokenResponse:
    ts = _get_token_service()
    token_hash = ts.hash_token(body.refresh_token)

    db_token = (
        db.query(DBRefreshToken)
        .filter(
            DBRefreshToken.token_hash == token_hash,
            DBRefreshToken.revoked == False,  # noqa: E712
            DBRefreshToken.expires_at > datetime.now(UTC),
        )
        .first()
    )
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revoke old token (rotation)
    db_token.revoked = True
    db.commit()

    user = db.query(DBUser).filter(DBUser.id == db_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return _issue_tokens(user, ts, db, device_info=db_token.device_info)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshRequest,
    db: Session = Depends(get_db_dependency),
) -> None:
    ts = _get_token_service()
    token_hash = ts.hash_token(body.refresh_token)
    db_token = db.query(DBRefreshToken).filter(DBRefreshToken.token_hash == token_hash).first()
    if db_token:
        db_token.revoked = True
        db.commit()


@auth_router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "roles": [role.value for role in current_user.roles],
        "tenant_id": current_user.tenant_id,
        "name": current_user.name,
        "clinic_id": current_user.clinic_id,
    }


@auth_router.get("/rbac-matrix")
async def rbac_matrix(current_user: User = Depends(get_current_user)) -> dict:
    """Get RBAC permission matrix. Requires authentication."""
    matrix = {role.value: sorted(perms) for role, perms in DEFAULT_ROLE_PERMISSIONS.items()}
    return {"roles": matrix}
