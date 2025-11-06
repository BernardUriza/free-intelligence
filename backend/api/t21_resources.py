"""T21 Resources API endpoints.

Provides resources and support information for Down Syndrome (T21).

Handles:
- GET /api/t21/resources - List all T21 resources
- GET /api/t21/resources/{id} - Get resource details
- GET /api/t21/resources/category/{category} - Filter by category
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/t21", tags=["t21-resources"])


# ============================================================================
# MODELS
# ============================================================================


class ResourceCategory(str, Enum):
    """Resource categories."""

    GUIDE = "guide"
    VIDEO = "video"
    ARTICLE = "article"
    TOOL = "tool"


class T21Resource(BaseModel):
    """T21 resource model."""

    id: str
    title: str
    description: str
    category: ResourceCategory
    icon: str
    url: Optional[str] = None
    tags: list[str] = []


class T21ResourcesResponse(BaseModel):
    """Response for resources list."""

    resources: list[T21Resource]
    total: int
    category: Optional[str] = None


# ============================================================================
# DEFAULT RESOURCES
# ============================================================================


DEFAULT_RESOURCES: list[T21Resource] = [
    T21Resource(
        id="t21-001",
        title="Guía de Inclusión Deportiva",
        description="Cómo incluir atletas con Síndrome de Down en deportes regulares",
        category=ResourceCategory.GUIDE,
        icon="📖",
        tags=["inclusión", "deporte", "guía"],
    ),
    T21Resource(
        id="t21-002",
        title="Vídeo: Ejercicios Seguros",
        description="Los 5 ejercicios más seguros para personas con T21",
        category=ResourceCategory.VIDEO,
        icon="🎬",
        tags=["ejercicios", "seguridad", "vídeo"],
    ),
    T21Resource(
        id="t21-003",
        title="Artículo: Nutrición y T21",
        description="Información sobre necesidades nutricionales especiales",
        category=ResourceCategory.ARTICLE,
        icon="📄",
        tags=["nutrición", "salud", "artículo"],
    ),
    T21Resource(
        id="t21-004",
        title="Herramienta: Calculadora de Calorias",
        description="Calcula necesidades calóricas personalizadas",
        category=ResourceCategory.TOOL,
        icon="🛠️",
        url="/tools/calorie-calc",
        tags=["nutrición", "herramienta", "cálculos"],
    ),
    T21Resource(
        id="t21-005",
        title="Guía: Comunicación Efectiva",
        description="Tips para comunicarse mejor con personas con T21",
        category=ResourceCategory.GUIDE,
        icon="📖",
        tags=["comunicación", "inclusión", "guía"],
    ),
    T21Resource(
        id="t21-006",
        title="Vídeo: Inclusión en Educación",
        description="Estrategias educativas inclusivas para el síndrome de Down",
        category=ResourceCategory.VIDEO,
        icon="🎬",
        tags=["educación", "inclusión", "vídeo"],
    ),
]


# ============================================================================
# ROUTES
# ============================================================================


@router.get("/resources", response_model=T21ResourcesResponse)
async def list_resources(
    category: Optional[ResourceCategory] = Query(None),
) -> T21ResourcesResponse:
    """
    List all T21 resources, optionally filtered by category.

    Args:
        category: Filter by resource category (optional)

    Returns:
        List of T21 resources
    """
    try:
        # Filter if category specified
        if category:
            filtered = [r for r in DEFAULT_RESOURCES if r.category == category]
            logger.info("T21_RESOURCES_LISTED", category=category, total=len(filtered))
            return T21ResourcesResponse(
                resources=filtered,
                total=len(filtered),
                category=category.value,
            )

        # Return all resources
        logger.info("T21_RESOURCES_LISTED", total=len(DEFAULT_RESOURCES))
        return T21ResourcesResponse(
            resources=DEFAULT_RESOURCES,
            total=len(DEFAULT_RESOURCES),
        )

    except Exception as e:
        logger.error("T21_RESOURCES_ERROR", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to load resources") from e


@router.get("/resources/{resource_id}", response_model=T21Resource)
async def get_resource(resource_id: str) -> T21Resource:
    """
    Get a specific T21 resource.

    Args:
        resource_id: Resource ID

    Returns:
        Resource details
    """
    try:
        resource = next((r for r in DEFAULT_RESOURCES if r.id == resource_id), None)

        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        logger.info("T21_RESOURCE_RETRIEVED", resource_id=resource_id)
        return resource

    except HTTPException:
        raise
    except Exception as e:
        logger.error("T21_RESOURCE_GET_ERROR", resource_id=resource_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve resource") from e


@router.get("/resources/search", response_model=T21ResourcesResponse)
async def search_resources(
    q: str = Query(..., min_length=1),
) -> T21ResourcesResponse:
    """
    Search T21 resources by title, description, or tags.

    Args:
        q: Search query

    Returns:
        Matching resources
    """
    try:
        query_lower = q.lower()

        # Search in title, description, and tags
        filtered = [
            r
            for r in DEFAULT_RESOURCES
            if (
                query_lower in r.title.lower()
                or query_lower in r.description.lower()
                or any(query_lower in tag.lower() for tag in r.tags)
            )
        ]

        logger.info("T21_RESOURCES_SEARCHED", query=q, total_found=len(filtered))
        return T21ResourcesResponse(
            resources=filtered,
            total=len(filtered),
        )

    except Exception as e:
        logger.error("T21_RESOURCES_SEARCH_ERROR", query=q, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed") from e


@router.get("/support")
async def get_support_contacts() -> dict[str, dict[str, str]]:
    """Get T21 support contacts and resources."""
    return {
        "hotline": {
            "name": "Línea de Apoyo T21",
            "phone": "1-800-T21-HELP",
            "hours": "24/7",
        },
        "email": {
            "address": "apoyo@fi-stride.com",
            "response_time": "24 horas",
        },
        "chat": {
            "available": "Lunes a Viernes 9am-6pm",
            "language": "Español",
        },
    }
