"""User service for registration, authentication, and user management.

Handles user CRUD and password-based login.
First registered user automatically becomes FI-superadmin.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from ..domain.entities.db_user import DBUser
from ..domain.entities.user import UserRole
from .password_service import hash_password, verify_password

logger = structlog.get_logger(__name__)


class UserService:
    """Business logic for user management."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, email: str, password: str, name: str) -> DBUser:
        """Register a new user.

        First user gets FI-superadmin role. Subsequent users get FI-clinician.

        Raises:
            ValueError: If email already exists or password too short.
        """
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        existing = self.db.query(DBUser).filter(DBUser.email == email).first()
        if existing:
            raise ValueError("Email already registered")

        # First user = superadmin
        user_count = self.db.query(DBUser).count()
        role = UserRole.SUPERADMIN.value if user_count == 0 else UserRole.CLINICIAN.value

        user = DBUser(
            email=email.lower().strip(),
            password_hash=hash_password(password),
            name=name.strip(),
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        logger.info(
            "user_registered",
            user_id=user.id,
            email=user.email,
            role=role,
            is_first_user=(user_count == 0),
        )
        return user

    def authenticate(self, email: str, password: str) -> DBUser | None:
        """Authenticate a user by email and password.

        Returns the user if credentials are valid, None otherwise.
        """
        user = self.db.query(DBUser).filter(DBUser.email == email.lower().strip()).first()
        if not user:
            return None

        if not user.is_active:
            logger.warning("login_inactive_user", email=email)
            return None

        if not verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()

        logger.info("user_authenticated", user_id=user.id, email=user.email)
        return user

    def get_by_id(self, user_id: str) -> DBUser | None:
        """Get user by ID."""
        return self.db.query(DBUser).filter(DBUser.id == user_id).first()

    def get_by_email(self, email: str) -> DBUser | None:
        """Get user by email."""
        return self.db.query(DBUser).filter(DBUser.email == email.lower().strip()).first()

    def update_role(self, user_id: str, role: UserRole) -> DBUser | None:
        """Update a user's role."""
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.role = role.value
        self.db.commit()
        self.db.refresh(user)
        logger.info("user_role_updated", user_id=user_id, new_role=role.value)
        return user

    def assign_clinic(self, user_id: str, clinic_id: str) -> DBUser | None:
        """Assign a user to a clinic."""
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.clinic_id = clinic_id
        self.db.commit()
        self.db.refresh(user)
        logger.info("user_clinic_assigned", user_id=user_id, clinic_id=clinic_id)
        return user
