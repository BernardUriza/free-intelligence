"""Prescription API Dependencies.

Shared dependencies for prescription endpoints.
Provides catalog and checker service instances.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from functools import lru_cache

from backend.domain.prescription.interfaces.icatalog_service import ICatalogService
from backend.domain.prescription.models.catalog import DrugCategory
from backend.domain.prescription.services.allergy_checker import (
    AllergyChecker,
    get_allergy_checker,
)
from backend.domain.prescription.services.catalog_service import (
    CatalogSearchRequest,
    CatalogService,
)
from backend.domain.prescription.dependencies import get_catalog_service_dep
from backend.domain.prescription.services.interaction_checker import (
    InteractionChecker,
    get_interaction_checker,
)
from backend.domain.prescription.services.template_engine import (
    TemplateEngine,
    get_template_engine,
)
from fastapi import HTTPException, status


@lru_cache(maxsize=1)
def get_catalog_service_cached() -> ICatalogService:
    """Get cached catalog service instance.

    Returns:
        ICatalogService instance via DI
    """
    return get_catalog_service_dep()


def get_interaction_checker_cached() -> InteractionChecker:
    """Get interaction checker instance.

    Returns:
        InteractionChecker instance
    """
    return get_interaction_checker()


def get_allergy_checker_cached() -> AllergyChecker:
    """Get allergy checker instance.

    Returns:
        AllergyChecker instance
    """
    return get_allergy_checker()


def get_template_engine_cached() -> TemplateEngine:
    """Get template engine instance.

    Returns:
        TemplateEngine instance
    """
    return get_template_engine()


def parse_category(category: str | None) -> DrugCategory | None:
    """Parse category string to DrugCategory enum.

    Args:
        category: Category string or None

    Returns:
        DrugCategory enum or None

    Raises:
        HTTPException: If category is invalid
    """
    if category is None:
        return None

    try:
        return DrugCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {category}",
        )


# Re-export commonly used items
__all__ = [
    "CatalogSearchRequest",
    "CatalogService",
    "DrugCategory",
    "get_allergy_checker_cached",
    "get_catalog_service_cached",
    "get_interaction_checker_cached",
    "get_template_engine_cached",
    "parse_category",
]
