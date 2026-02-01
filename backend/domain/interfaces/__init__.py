"""Domain repository interfaces.

These interfaces define the contracts for repositories without depending on
concrete implementations, breaking circular dependencies.
"""

from backend.domain.interfaces.iorder_repository import IOrderRepository
from backend.domain.interfaces.ipatient_repository import IPatientRepository
from backend.domain.interfaces.isession_repository import ISessionRepository
from backend.domain.interfaces.isoap_repository import ISOAPRepository

__all__ = [
    "IOrderRepository",
    "IPatientRepository",
    "ISessionRepository",
    "ISOAPRepository",
]
