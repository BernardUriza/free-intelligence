"""
Free Intelligence - Authentication Models
HIPAA Card: G-003 - JWT + RBAC middleware FastAPI
Author: Bernard Uriza Orozco
Created: 2025-11-17

User, role, and token models for JWT authentication and RBAC.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """
    User roles for RBAC (Role-Based Access Control).

    HIPAA Reference: 45 CFR §164.308(a)(4) - Access Management
    """

    MEDICO = "MEDICO"  # Doctor: read/write SOAP notes
    ENFERMERA = "ENFERMERA"  # Nurse: read-only access
    ADMIN = "ADMIN"  # Admin: full access to all resources


class Permission(str, Enum):
    """
    Permissions for RBAC authorization.

    Maps to HTTP methods and resource actions.
    """

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


# RBAC Matrix: role → permissions
# This defines what each role can do
ROLE_PERMISSIONS = {
    UserRole.MEDICO: [Permission.READ, Permission.WRITE],
    UserRole.ENFERMERA: [Permission.READ],
    UserRole.ADMIN: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
}


class User(BaseModel):
    """
    User model for authentication.

    In a real implementation, this would be stored in a database.
    For MVP, we use an in-memory store.
    """

    user_id: str = Field(..., description="Unique user identifier (UUID)")
    username: str = Field(..., description="Username for login")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User's full name")
    role: UserRole = Field(..., description="User role for RBAC")
    hashed_password: str = Field(..., description="Bcrypt hashed password")
    disabled: bool = Field(default=False, description="Account disabled flag")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserInDB(User):
    """User model with hashed password (stored in DB)."""

    pass


class UserPublic(BaseModel):
    """Public user model (no sensitive data)."""

    user_id: str
    username: str
    email: str
    full_name: str
    role: UserRole


class Token(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token (15min expiry)")
    refresh_token: str = Field(..., description="JWT refresh token (7 days expiry)")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(default=900, description="Token expiry in seconds (15min)")


class TokenData(BaseModel):
    """Data extracted from JWT token."""

    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None
    scopes: List[str] = Field(default_factory=list)


class LoginRequest(BaseModel):
    """Login request body."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request body."""

    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")
