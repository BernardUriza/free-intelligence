"""SQLAlchemy model for the refresh_tokens table.

DB-backed refresh tokens with revocation support.
Each token is hashed (SHA-256) before storage for security.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from backend.models.db_models import Base


def _generate_uuid() -> str:
    return str(uuid4())


class DBRefreshToken(Base):
    """Refresh token stored in the database for revocation and audit."""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_generate_uuid)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    device_info = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<DBRefreshToken user={self.user_id} revoked={self.revoked}>"
