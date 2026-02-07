"""Prescription Template Endpoints.

GET /templates - List available templates
GET /templates/{id} - Get template details

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from backend.domain.prescription.models.template import PrescriptionTemplate
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, HTTPException, Query, status

from .dependencies import get_template_engine_cached
from .models import TemplateListResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions - Templates"])


@router.get(
    "/templates",
    response_model=TemplateListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_templates(
    owner_id: str | None = Query(default=None, description="Filter by owner"),
    include_system: bool = Query(default=True, description="Include system templates"),
) -> TemplateListResponse:
    """List available prescription templates."""
    engine = get_template_engine_cached()
    templates = engine.list_templates(owner_id=owner_id, include_system=include_system)

    logger.info("TEMPLATES_LISTED", count=len(templates), owner_id=owner_id)

    return TemplateListResponse(templates=templates, count=len(templates))


@router.get(
    "/templates/{template_id}",
    response_model=PrescriptionTemplate,
    status_code=status.HTTP_200_OK,
)
async def get_template(template_id: str) -> PrescriptionTemplate:
    """Get a specific template by ID."""
    engine = get_template_engine_cached()
    template = engine.get_template(template_id)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )

    return template
