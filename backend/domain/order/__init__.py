"""Order domain entities."""

from enum import Enum
from dataclasses import dataclass

# Order types and status
class OrderType(str, Enum):
    PRESCRIPTION = "prescription"
    LAB = "lab"
    IMAGING = "imaging"
    REFERRAL = "referral"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Minimal Order entity
@dataclass
class Order:
    id: str
    session_id: str
    type: OrderType
    status: OrderStatus
    content: dict


# Repository interface from domain layer (no circular dependency)
from backend.domain.interfaces.iorder_repository import IOrderRepository

__all__ = [
    "Order",
    "OrderType",
    "OrderStatus",
    "IOrderRepository",
]
