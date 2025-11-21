"""
Free Intelligence - In-Memory User Store (MVP)
HIPAA Card: G-003 - JWT + RBAC middleware FastAPI
Author: Bernard Uriza Orozco
Created: 2025-11-17

In-memory user database for MVP demonstration.
In production, replace with PostgreSQL/MySQL/etc.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Dict
from uuid import uuid4

from backend.auth.jwt import get_password_hash
from backend.auth.models import User, UserRole

# ============================================================================
# In-Memory User Database (MVP)
# ============================================================================

# Fake database: dict[user_id] = User
USERS_DB: Dict[str, User] = {}

# Username index: dict[username] = user_id
USERNAME_INDEX: Dict[str, str] = {}


def create_user(
    username: str,
    password: str,
    email: str,
    full_name: str,
    role: UserRole,
) -> User:
    """
    Create a new user in the in-memory database.

    Args:
        username: Unique username
        password: Plain text password (will be hashed)
        email: User email
        full_name: User's full name
        role: User role for RBAC

    Returns:
        Created User object

    Raises:
        ValueError: If username already exists
    """
    if username in USERNAME_INDEX:
        raise ValueError(f"Username '{username}' already exists")

    user_id = str(uuid4())
    hashed_password = get_password_hash(password)

    user = User(
        user_id=user_id,
        username=username,
        email=email,
        full_name=full_name,
        role=role,
        hashed_password=hashed_password,
        disabled=False,
        created_at=datetime.now(UTC),
    )

    USERS_DB[user_id] = user
    USERNAME_INDEX[username] = user_id

    return user


def get_user_by_id(user_id: str) -> User | None:
    """
    Get user by user_id.

    Args:
        user_id: User ID (UUID)

    Returns:
        User object if found, None otherwise
    """
    return USERS_DB.get(user_id)


def get_user_by_username(username: str) -> User | None:
    """
    Get user by username.

    Args:
        username: Username

    Returns:
        User object if found, None otherwise
    """
    user_id = USERNAME_INDEX.get(username)
    if user_id is None:
        return None
    return USERS_DB.get(user_id)


def get_users_db() -> Dict[str, User]:
    """
    Get the entire user database (for authentication).

    Returns:
        Dict mapping username to User object
    """
    return {user.username: user for user in USERS_DB.values()}


# ============================================================================
# Initialize Demo Users (for MVP testing)
# ============================================================================


def init_demo_users() -> None:
    """
    Initialize demo users for MVP testing.

    Creates:
    - dr.mendoza (MEDICO) - password: medico123
    - enf.garcia (ENFERMERA) - password: enfermera123
    - admin (ADMIN) - password: admin123

    SECURITY WARNING: These are demo credentials only!
    In production, users should be created via admin panel with secure passwords.
    """
    # Clear existing users
    USERS_DB.clear()
    USERNAME_INDEX.clear()

    # Create demo users
    users = [
        {
            "username": "dr.mendoza",
            "password": "medico123",
            "email": "mendoza@hospital.mx",
            "full_name": "Dr. Carlos Mendoza",
            "role": UserRole.MEDICO,
        },
        {
            "username": "enf.garcia",
            "password": "enfermera123",
            "email": "garcia@hospital.mx",
            "full_name": "María García",
            "role": UserRole.ENFERMERA,
        },
        {
            "username": "admin",
            "password": "admin123",
            "email": "admin@hospital.mx",
            "full_name": "System Administrator",
            "role": UserRole.ADMIN,
        },
    ]

    for user_data in users:
        create_user(**user_data)

    print(f"✅ Initialized {len(users)} demo users:")
    for user in USERS_DB.values():
        print(f"   • {user.username} ({user.role.value}) - {user.email}")


# Don't auto-initialize on import (causes bcrypt issues with Python 3.14)
# Call init_demo_users() manually when needed or on first login attempt
