"""Library API endpoints for consultation browsing and search.

Handles:
- GET /api/consultations - List user consultations
- GET /api/consultations/{id} - Get consultation details
- GET /api/consultations/search - Search consultations
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.fi_event_store import EventStore
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/consultations", tags=["library"])


# ============================================================================
# MODELS
# ============================================================================


class ConsultationMetadata(BaseModel):
    """Consultation metadata for library listing."""

    consultation_id: str
    event_count: int
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        populate_by_name = True  # Allow both snake_case and camelCase


class ConsultationsResponse(BaseModel):
    """Response for consultations list."""

    consultations: list[ConsultationMetadata]
    total: int
    limit: int
    offset: int


# ============================================================================
# ROUTES
# ============================================================================


@router.get("", response_model=ConsultationsResponse)
async def list_consultations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ConsultationsResponse:
    """
    List all consultations with pagination.

    Args:
        limit: Max results per page (default: 20)
        offset: Offset for pagination (default: 0)

    Returns:
        List of consultations with metadata
    """
    try:
        # Initialize event store
        from backend.config_loader import load_config

        config = load_config()
        corpus_path = config.get("storage", {}).get("corpus_path", "storage/corpus.h5")
        store = EventStore(corpus_path)

        # Get all consultations
        all_consultations = store.list_consultations()

        # Apply pagination
        total = len(all_consultations)
        paginated = all_consultations[offset : offset + limit]

        # Convert to response model
        consultations = [
            ConsultationMetadata(
                id=c.get("consultation_id", ""),
                consultationId=c.get("consultation_id", ""),
                eventCount=c.get("event_count", 0),
                createdAt=c.get("created_at", ""),
                updatedAt=c.get("updated_at"),
            )
            for c in paginated
        ]

        logger.info(
            "CONSULTATIONS_LISTED",
            total=total,
            returned=len(consultations),
            offset=offset,
            limit=limit,
        )

        return ConsultationsResponse(
            consultations=consultations,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error("CONSULTATIONS_LIST_ERROR", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list consultations") from e


@router.get("/{consultation_id}", response_model=dict[str, Any])
async def get_consultation(consultation_id: str) -> dict[str, Any]:
    """
    Get detailed consultation data.

    Args:
        consultation_id: Consultation UUID

    Returns:
        Consultation metadata and summary
    """
    try:
        from backend.config_loader import load_config

        config = load_config()
        corpus_path = config.get("storage", {}).get("corpus_path", "storage/corpus.h5")
        store = EventStore(corpus_path)

        # Check if consultation exists
        if not store.consultation_exists(consultation_id):
            raise HTTPException(status_code=404, detail="Consultation not found")

        # Get metadata
        metadata = store.get_consultation_metadata(consultation_id)

        # Get event count
        event_count = store.get_event_count(consultation_id)

        logger.info("CONSULTATION_RETRIEVED", consultation_id=consultation_id)

        return {
            "id": consultation_id,
            "metadata": metadata,
            "eventCount": event_count,
            "status": "complete",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("CONSULTATION_GET_ERROR", consultation_id=consultation_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve consultation") from e


@router.get("/search", response_model=ConsultationsResponse)
async def search_consultations(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ConsultationsResponse:
    """
    Search consultations by ID or metadata.

    Args:
        q: Search query
        limit: Max results
        offset: Pagination offset

    Returns:
        Matching consultations
    """
    try:
        from backend.config_loader import load_config

        config = load_config()
        corpus_path = config.get("storage", {}).get("corpus_path", "storage/corpus.h5")
        store = EventStore(corpus_path)

        # Get all and filter
        all_consultations = store.list_consultations()
        query_lower = q.lower()

        filtered = [
            c for c in all_consultations if query_lower in c.get("consultation_id", "").lower()
        ]

        # Apply pagination
        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        # Convert to response
        consultations = [
            ConsultationMetadata(
                id=c.get("consultation_id", ""),
                consultationId=c.get("consultation_id", ""),
                eventCount=c.get("event_count", 0),
                createdAt=c.get("created_at", ""),
                updatedAt=c.get("updated_at"),
            )
            for c in paginated
        ]

        logger.info(
            "CONSULTATIONS_SEARCHED",
            query=q,
            total_found=total,
            returned=len(consultations),
        )

        return ConsultationsResponse(
            consultations=consultations,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error("CONSULTATIONS_SEARCH_ERROR", query=q, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed") from e
