"""Prescription domain interfaces for dependency inversion.

Phase 2.3 Marte - SOLID refactor of medication catalog.
"""

from backend.domain.prescription.interfaces.icatalog_repository import ICatalogRepository
from backend.domain.prescription.interfaces.icatalog_service import ICatalogService

__all__ = ["ICatalogRepository", "ICatalogService"]
