"""Pure domain layer - framework-agnostic business logic.

This module contains:
- Domain entities (Patient, Session, Order, SOAPNote)
- Repository interfaces (IPatientRepository, ISessionRepository, etc.)
- Value objects and domain enums

ZERO dependencies on:
- FastAPI
- Pydantic (except for validation if needed)
- SQLAlchemy
- Any infrastructure framework

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 2 - Pure Domain Entities
"""

# Patient domain
# from backend.domain.patient import Gender, IPatientRepository, Patient

# Session domain
# from backend.domain.session import ISessionRepository, Session, SessionStatus

# Order domain
# from backend.domain.order import IOrderRepository, Order, OrderStatus, OrderType

# SOAP domain
# from backend.domain.soap import ISOAPRepository, SOAPNote, SOAPStatus

# TODO: Re-enable these imports after defining the entities properly

__all__ = [
    # Patient
    "Patient",
    "Gender",
    "IPatientRepository",
    # Session
    "Session",
    "SessionStatus",
    "ISessionRepository",
    # Order
    "Order",
    "OrderType",
    "OrderStatus",
    "IOrderRepository",
    # SOAP
    "SOAPNote",
    "SOAPStatus",
    "ISOAPRepository",
]
