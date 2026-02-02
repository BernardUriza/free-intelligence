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

Import from submodules directly:
    from backend.domain.patient import Patient, IPatientRepository
    from backend.domain.session import Session, SessionStatus
    from backend.domain.order import Order, OrderType
    from backend.domain.soap import SOAPNote, SOAPStatus

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 2 - Pure Domain Entities
"""
