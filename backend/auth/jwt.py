"""
Free Intelligence - JWT Token Management
HIPAA Card: G-003 - JWT + RBAC middleware FastAPI
Author: Bernard Uriza Orozco
Created: 2025-11-17

JWT token encoding, decoding, and validation.
HIPAA Reference: 45 CFR §164.312(d) - Person or Entity Authentication
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.auth.models import TokenData, User, UserRole

# ============================================================================
# Configuration
# ============================================================================

# Secret key for JWT signing (MUST be set in environment variables)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "INSECURE_DEV_KEY_CHANGE_IN_PRODUCTION")
if SECRET_KEY == "INSECURE_DEV_KEY_CHANGE_IN_PRODUCTION":
    print("⚠️  WARNING: Using default JWT_SECRET_KEY. Set JWT_SECRET_KEY env var for production!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15 minutes (HIPAA best practice)
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days


# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# Password Hashing
# ============================================================================


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password from user
        hashed_password: Bcrypt hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)


# ============================================================================
# JWT Token Creation
# ============================================================================


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode (should include sub, role, etc.)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token({"sub": "user123", "role": "MEDICO"})
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    to_encode.update({"iat": datetime.now(UTC)})  # Issued at
    to_encode.update({"type": "access"})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token (long-lived, 7 days).

    Args:
        data: Payload data to encode

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire})
    to_encode.update({"iat": datetime.now(UTC)})
    to_encode.update({"type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ============================================================================
# JWT Token Validation
# ============================================================================


def decode_token(token: str) -> TokenData | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData if valid, None if invalid

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("sub")
        username = payload.get("username")
        role_str = payload.get("role")
        scopes: list = payload.get("scopes", [])

        if user_id is None or username is None:
            return None

        # Type assertions after None check
        user_id = str(user_id)
        username = str(username)
        role_str = str(role_str) if role_str else None

        # Parse role enum
        try:
            role = UserRole(role_str) if role_str else None
        except ValueError:
            role = None

        return TokenData(
            user_id=user_id,
            username=username,
            role=role,
            scopes=scopes,
        )

    except JWTError:
        return None


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verify that a token is of the expected type (access or refresh).

    Args:
        token: JWT token string
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        True if token type matches, False otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        return token_type == expected_type
    except JWTError:
        return False


# ============================================================================
# User Authentication
# ============================================================================


def authenticate_user(fake_db: dict, username: str, password: str) -> User | None:
    """
    Authenticate a user with username and password.

    Args:
        fake_db: In-memory user database (dict[username] = User)
        username: Username
        password: Plain text password

    Returns:
        User object if authentication succeeds, None otherwise

    Note:
        In production, replace fake_db with real database queries.
    """
    user = fake_db.get(username)
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if user.disabled:
        return None

    return user
