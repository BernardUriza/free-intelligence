"""Mappers module - DB ↔ Domain bidirectional mapping.

Mappers extract mapping logic from repositories, ensuring:
- Single Responsibility: Repositories handle persistence, mappers handle transformation
- Type Safety: Explicit dataclasses for persistence structures
- Reusability: Same mapper can be used by multiple repositories
- Testability: Mappers are pure functions, easy to unit test

Pattern (P1-5 Repository Mappers):
    Repository: Handles I/O, transactions, error handling
    Mapper: Handles data transformation (domain ↔ persistence)

Created: 2026-02-02 (P1-5 Triásico - Repository Mappers)
"""

from backend.mappers.order_mapper import OrderHDF5Metadata, OrderMapper
from backend.mappers.patient_mapper import PatientMapper
from backend.mappers.session_mapper import SessionHDF5Metadata, SessionMapper
from backend.mappers.soap_mapper import (
    SOAPHDF5Content,
    SOAPHDF5Metadata,
    SOAPMapper,
)

__all__ = [
    "SOAPMapper",
    "SOAPHDF5Metadata",
    "SOAPHDF5Content",
    "PatientMapper",
    "SessionMapper",
    "SessionHDF5Metadata",
    "OrderMapper",
    "OrderHDF5Metadata",
]
