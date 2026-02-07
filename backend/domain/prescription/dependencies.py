"""FastAPI Dependency Injection providers for Prescription domain.

Provides singleton ICatalogService and ICatalogRepository dependencies.

Author: Claude Code
Created: 2026-02-02 (Phase 2.3 - DI Refactor - Circular Import Fix)
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.domain.prescription.interfaces.icatalog_repository import ICatalogRepository
    from backend.domain.prescription.interfaces.icatalog_service import ICatalogService


@lru_cache(maxsize=1)
def _get_catalog_repository_singleton() -> "ICatalogRepository":
    """Internal singleton factory for InMemoryCatalogRepository."""
    from backend.domain.prescription.repositories import InMemoryCatalogRepository

    return InMemoryCatalogRepository()


def get_catalog_repository_dep() -> "ICatalogRepository":
    """Get medication catalog repository singleton - SOLID DI factory.

    Phase 2.3 Marte: Provides raw data access for advanced use cases.

    Returns:
        ICatalogRepository singleton instance (InMemoryCatalogRepository)

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_catalog_repository_singleton()


@lru_cache(maxsize=1)
def _get_catalog_service_singleton() -> "ICatalogService":
    """Internal singleton factory for CatalogService."""
    from backend.domain.prescription.services.catalog_service import CatalogService

    return CatalogService(repository=get_catalog_repository_dep())


def get_catalog_service_dep() -> "ICatalogService":
    """Get medication catalog service singleton via DI.

    Returns:
        ICatalogService singleton instance with InMemoryCatalogRepository

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_catalog_service_singleton()


__all__ = ["get_catalog_repository_dep", "get_catalog_service_dep"]
