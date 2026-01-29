"""Order domain entity - pure business logic.

Order represents a medical service order (lab test, imaging, procedure).

This is a PURE domain entity with ZERO framework dependencies.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 2 - Pure Domain Entities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class OrderType(str, Enum):
    """Type of medical order."""

    LAB_TEST = "lab_test"
    IMAGING = "imaging"
    PROCEDURE = "procedure"
    PRESCRIPTION = "prescription"
    REFERRAL = "referral"


class OrderStatus(str, Enum):
    """Order lifecycle status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Order:
    """Order domain entity.

    Represents a medical service order within a clinical session.

    Business rules:
    - order_id is immutable
    - session_id links order to session
    - status can only progress forward
    - cancelled orders cannot be uncancelled
    """

    order_id: str
    session_id: str
    order_type: OrderType
    description: str
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate entity after initialization.

        Raises:
            ValueError: If business rules are violated
        """
        if not self.order_id or not self.order_id.strip():
            raise ValueError("Order ID cannot be empty")

        if not self.session_id or not self.session_id.strip():
            raise ValueError("Session ID cannot be empty")

        if not self.description or not self.description.strip():
            raise ValueError("Order description cannot be empty")

        # Ensure dates are UTC-aware
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=UTC)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=UTC)

    # ========================================================================
    # Domain Behavior (Business Logic)
    # ========================================================================

    def mark_in_progress(self) -> None:
        """Mark order as in progress.

        Raises:
            ValueError: If order is not pending
        """
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot start order with status: {self.status}")

        self.status = OrderStatus.IN_PROGRESS
        self.updated_at = datetime.now(UTC)

    def mark_completed(self, notes: str | None = None) -> None:
        """Mark order as completed.

        Args:
            notes: Optional completion notes

        Raises:
            ValueError: If order is cancelled
        """
        if self.status == OrderStatus.CANCELLED:
            raise ValueError("Cannot complete a cancelled order")

        self.status = OrderStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

        if notes:
            self.notes = notes

    def cancel(self, reason: str | None = None) -> None:
        """Cancel order.

        Args:
            reason: Optional cancellation reason

        Raises:
            ValueError: If order is already completed
        """
        if self.status == OrderStatus.COMPLETED:
            raise ValueError("Cannot cancel a completed order")

        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

        if reason:
            self.notes = f"Cancelled: {reason}"

    def is_active(self) -> bool:
        """Check if order is active (not completed or cancelled).

        Returns:
            True if order is pending or in progress
        """
        return self.status in [OrderStatus.PENDING, OrderStatus.IN_PROGRESS]

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Order(id={self.order_id}, type={self.order_type.value}, "
            f"status={self.status.value})"
        )
