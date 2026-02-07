"""Medication Catalog Endpoints.

GET /catalog/search - Search medications
GET /catalog/autocomplete - Autocomplete suggestions
GET /catalog/{id} - Get medication details
GET /catalog/categories/list - List categories
GET /catalog/stats - Get catalog stats
GET /catalog/essential - Essential medications (cuadro básico)
GET /catalog/otc - Over-the-counter medications

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from typing import Any

from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, HTTPException, Query, status

from .dependencies import (
    CatalogSearchRequest,
    get_catalog_service_cached,
    parse_category,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions - Catalog"])


@router.get(
    "/catalog/search",
    status_code=status.HTTP_200_OK,
)
async def search_catalog(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    category: str | None = Query(default=None, description="Filter by category"),
    essential_only: bool = Query(default=False, description="Only essential medications"),
    otc_only: bool = Query(default=False, description="Only OTC medications"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
) -> dict[str, Any]:
    """Search medication catalog."""
    catalog = get_catalog_service_cached()
    category_enum = parse_category(category)

    request = CatalogSearchRequest(
        query=q,
        category=category_enum,
        essential_only=essential_only,
        otc_only=otc_only,
        limit=limit,
    )

    response = catalog.search(request)

    logger.info(
        "CATALOG_SEARCH",
        query=q,
        results=response.total_matches,
    )

    return {
        "query": response.query,
        "total_matches": response.total_matches,
        "results": [
            {
                "medication": r.medication.model_dump(mode="json"),
                "score": r.score,
                "match_type": r.match_type,
            }
            for r in response.results
        ],
    }


@router.get(
    "/catalog/autocomplete",
    status_code=status.HTTP_200_OK,
)
async def autocomplete_medication(
    prefix: str = Query(..., min_length=2, max_length=50, description="Text prefix"),
    limit: int = Query(default=5, ge=1, le=20, description="Max suggestions"),
    category: str | None = Query(default=None, description="Filter by category"),
) -> dict[str, Any]:
    """Get autocomplete suggestions for medication names."""
    catalog = get_catalog_service_cached()
    category_enum = parse_category(category)

    suggestions = catalog.autocomplete(
        prefix=prefix,
        limit=limit,
        category=category_enum,
    )

    return {
        "prefix": prefix,
        "suggestions": suggestions,
    }


@router.get(
    "/catalog/{medication_id}",
    status_code=status.HTTP_200_OK,
)
async def get_catalog_medication(medication_id: str) -> dict[str, Any]:
    """Get medication details by ID."""
    catalog = get_catalog_service_cached()
    medication = catalog.get_by_id(medication_id)

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication not found: {medication_id}",
        )

    return {"medication": medication.model_dump(mode="json")}


@router.get(
    "/catalog/categories/list",
    status_code=status.HTTP_200_OK,
)
async def list_categories() -> dict[str, Any]:
    """Get all available drug categories."""
    catalog = get_catalog_service_cached()
    categories = catalog.get_categories()
    return {"categories": categories}


@router.get(
    "/catalog/stats",
    status_code=status.HTTP_200_OK,
)
async def get_catalog_stats() -> dict[str, Any]:
    """Get medication catalog statistics."""
    catalog = get_catalog_service_cached()
    stats = catalog.get_catalog_stats()
    return {"stats": stats}


@router.get(
    "/catalog/essential",
    status_code=status.HTTP_200_OK,
)
async def list_essential_medications(
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Get essential medications (cuadro básico)."""
    catalog = get_catalog_service_cached()
    medications = catalog.get_essential_medications(limit=limit)
    return {
        "count": len(medications),
        "medications": [m.model_dump(mode="json") for m in medications],
    }


@router.get(
    "/catalog/otc",
    status_code=status.HTTP_200_OK,
)
async def list_otc_medications(
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Get over-the-counter medications."""
    catalog = get_catalog_service_cached()
    medications = catalog.get_otc_medications(limit=limit)
    return {
        "count": len(medications),
        "medications": [m.model_dump(mode="json") for m in medications],
    }
