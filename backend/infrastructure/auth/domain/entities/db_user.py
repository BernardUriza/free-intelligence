"""SQLAlchemy model for the users table.

Stores application users with password hashes for local authentication.
Local JWT identity provider.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from backend.models.db_models import Base


def _generate_uuid() -> str:
    return str(uuid4())


class DBUser(Base):
    """Local user account for self-hosted authentication."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="FI-clinician")
    clinic_id = Column(UUID(as_uuid=False), ForeignKey("clinics.clinic_id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<DBUser {self.email} role={self.role}>"
