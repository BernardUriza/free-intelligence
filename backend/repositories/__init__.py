"""Repository pattern for data access layer.

Provides abstraction over HDF5 storage operations to improve testability,
maintainability, and reduce code duplication.

Clean Code Principles Applied:
- Single Responsibility: Each repository handles one entity/aggregate
- Dependency Inversion: Depend on abstractions, not concrete implementations
- DRY: Centralize HDF5 I/O logic to eliminate duplication
- Open/Closed: Easy to extend with new repository types without modifying existing code
"""

from .audit_repository import AuditRepository
from .base_repository import BaseRepository
from .corpus_repository import CorpusRepository
from .session_repository import SessionRepository

__all__ = [
    "AuditRepository",
    "BaseRepository",
    "CorpusRepository",
    "SessionRepository",
]
