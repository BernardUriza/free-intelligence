"""Medical Orders Models - Pydantic schemas.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================


class OrderCreateRequest(BaseModel):
    """Request body for order creation."""

    type: str = Field(
        ...,
        description="Order type: medication, lab, imaging, followup",
    )
    description: str = Field(..., min_length=1, description="Order description")
    details: str = Field(default="", description="Additional details")


class OrderUpdateRequest(BaseModel):
    """Request body for order update."""

    type: str = Field(..., description="Order type")
    description: str = Field(..., min_length=1, description="Order description")
    details: str = Field(default="", description="Additional details")
