"""
Admin User Management API

RBAC-protected endpoints for user administration.
Requires SUPERADMIN role.

Endpoints:
- GET    /api/internal/admin/users - List users
- GET    /api/internal/admin/users/{id} - Get user details
- POST   /api/internal/admin/users - Create user
- PUT    /api/internal/admin/users/{id}/block - Block/unblock user
- PUT    /api/internal/admin/users/{id}/roles - Update user roles
- DELETE /api/internal/admin/users/{id} - Delete user
"""

from __future__ import annotations

from typing import Annotated

import structlog
from backend.api.admin.dependencies import get_user_service_dep
from backend.database import get_db_dependency
from backend.infrastructure.auth import User, UserRole, require_roles
from backend.infrastructure.auth.domain.entities.db_user import DBUser
from backend.infrastructure.auth.services.user_service import UserService
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

UserServiceDep = Annotated[UserService, Depends(get_user_service_dep)]

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/users", tags=["admin"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class UserListResponse(BaseModel):
    users: list[dict]
    total: int
    page: int
    per_page: int


class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=8)
    role: str = "FI-clinician"


class UpdateRolesRequest(BaseModel):
    role: str


class BlockUserRequest(BaseModel):
    blocked: bool


# ============================================================================
# RBAC DEPENDENCY
# ============================================================================

superadmin_dependency = Depends(require_roles([UserRole.SUPERADMIN]))


async def require_superadmin(
    current_user: User = superadmin_dependency,
) -> dict:
    return {
        "sub": current_user.user_id,
        "email": current_user.email,
        "roles": [role.value for role in current_user.roles],
    }


require_superadmin_dependency = Depends(require_superadmin)


def _user_to_dict(u: DBUser) -> dict:
    return {
        "user_id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "clinic_id": u.clinic_id,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
    }


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = 0,
    per_page: int = 50,
    search: str | None = None,
    admin: dict = require_superadmin_dependency,
    db: Session = Depends(get_db_dependency),
):
    """List all users with pagination and search."""
    query = db.query(DBUser)
    if search:
        query = query.filter(DBUser.email.ilike(f"%{search}%"))
    total = query.count()
    users = query.offset(page * per_page).limit(per_page).all()
    return UserListResponse(
        users=[_user_to_dict(u) for u in users],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    service: UserServiceDep,
    admin: dict = require_superadmin_dependency,
):
    """Get user details by ID."""
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    service: UserServiceDep,
    admin: dict = require_superadmin_dependency,
):
    """Create new user."""
    try:
        user = service.register(request.email, request.password, request.name)
        # Override default role if specified
        role = UserRole.coerce(request.role)
        if role and role.value != user.role:
            service.update_role(user.id, role)
            user.role = role.value
        return _user_to_dict(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{user_id}/block")
async def block_user(
    user_id: str,
    request: BlockUserRequest,
    service: UserServiceDep,
    admin: dict = require_superadmin_dependency,
):
    """Block or unblock a user."""
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not request.blocked
    service.db.commit()
    service.db.refresh(user)
    logger.warning("USER_BLOCK_STATUS_CHANGED", user_id=user_id, blocked=request.blocked)
    return _user_to_dict(user)


@router.put("/{user_id}/roles")
async def update_user_roles(
    user_id: str,
    request: UpdateRolesRequest,
    service: UserServiceDep,
    admin: dict = require_superadmin_dependency,
):
    """Update user's role."""
    role = UserRole.coerce(request.role)
    if not role:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")
    user = service.update_role(user_id, role)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    service: UserServiceDep,
    admin: dict = require_superadmin_dependency,
):
    """Delete user (soft delete - deactivate)."""
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    service.db.commit()
    logger.warning("USER_DELETED_VIA_API", user_id=user_id, admin_email=admin.get("email"))


@router.get("/roles")
async def list_available_roles(
    admin: dict = require_superadmin_dependency,
):
    """List all available roles in the system."""
    return {"roles": [{"name": r.value} for r in UserRole]}
