"""SQLAlchemy models for Subscription Plans.

Defines subscription tiers with doctor limits and feature flags.
Used for multi-tenant clinic licensing.

Author: Bernard Uriza Orozco
Created: 2025-12-31
"""

from __future__ import annotations

from uuid import uuid4

from backend.models.db_models import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid4())


class SubscriptionPlan(Base):
    """Subscription plan defining doctor limits and features.

    Plans are immutable once created - to change limits,
    create a new plan and migrate clinics.

    Attributes:
        plan_id: Unique identifier
        name: Internal name (free, pro, enterprise)
        display_name: User-facing name (Plan Gratuito, Plan Profesional)
        max_doctors: Maximum doctors allowed (NULL = unlimited)
        features: JSON array of enabled features
        price_usd: Monthly price in USD
        is_active: Whether plan is available for new subscriptions
    """

    __tablename__ = "subscription_plans"

    plan_id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
    )
    name = Column(String(50), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)
    max_doctors = Column(Integer, nullable=True)  # NULL = unlimited
    features = Column(JSONB, nullable=True, default=list)
    price_usd = Column(Numeric(10, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    # clinics = relationship("Clinic", back_populates="subscription")  # COMMENTED: Clinic.plan_id FK doesn't exist yet

    def __repr__(self) -> str:
        limit = self.max_doctors if self.max_doctors is not None else "∞"
        return f"<SubscriptionPlan {self.name} (max_doctors={limit})>"

    @property
    def is_unlimited(self) -> bool:
        """Check if plan has unlimited doctors."""
        return self.max_doctors is None
