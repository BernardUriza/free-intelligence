"""Provider management API endpoints.

CRUD operations for healthcare provider records with PostgreSQL persistence.
Public API - accessible to authenticated users.

Author: Bernard Uriza Orozco
Created: 2025-11-17
Card: FI-DATA-DB-001
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db_dependency
from backend.logger import get_logger
from backend.models.db_models import Provider

logger = get_logger(__name__)

router = APIRouter(prefix="/providers", tags=["Providers"])


# ============================================================================
# Pydantic Schemas
# ============================================================================


class ProviderCreate(BaseModel):
    """Schema for creating a new provider."""

    nombre: str = Field(..., min_length=1, max_length=100, description="Full name")
    cedula_profesional: str | None = Field(
        None, min_length=1, max_length=20, description="Professional license number"
    )
    especialidad: str | None = Field(None, max_length=100, description="Medical specialty")


class ProviderUpdate(BaseModel):
    """Schema for updating provider data."""

    nombre: str | None = Field(None, min_length=1, max_length=100)
    cedula_profesional: str | None = Field(None, min_length=1, max_length=20)
    especialidad: str | None = Field(None, max_length=100)


class ProviderResponse(BaseModel):
    """Schema for provider API responses."""

    provider_id: str
    nombre: str
    cedula_profesional: str | None
    especialidad: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ============================================================================
# CRUD Endpoints
# ============================================================================


@router.post("/", response_model=ProviderResponse, status_code=201)
def create_provider(provider: ProviderCreate, db: Session = Depends(get_db_dependency)):
    """Create a new provider record.

    Args:
        provider: Provider data
        db: Database session (injected)

    Returns:
        Created provider with assigned ID

    Raises:
        400: Cédula already exists
        500: Database error
    """
    try:
        # Check for duplicate cédula
        if provider.cedula_profesional:
            existing = (
                db.query(Provider)
                .filter(Provider.cedula_profesional == provider.cedula_profesional)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cédula {provider.cedula_profesional} already exists",
                )

        # Create provider
        db_provider = Provider(
            nombre=provider.nombre,
            cedula_profesional=provider.cedula_profesional,
            especialidad=provider.especialidad,
        )
        db.add(db_provider)
        db.commit()
        db.refresh(db_provider)

        logger.info("PROVIDER_CREATED", provider_id=db_provider.provider_id, nombre=provider.nombre)
        return db_provider.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PROVIDER_CREATE_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create provider")


@router.get("/", response_model=List[ProviderResponse])
def list_providers(
    search: str | None = Query(None, description="Search by nombre or especialidad"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    db: Session = Depends(get_db_dependency),
):
    """List providers with optional search and pagination.

    Args:
        search: Search query (nombre or especialidad)
        limit: Maximum results (1-100)
        offset: Skip N results
        db: Database session (injected)

    Returns:
        List of providers matching criteria
    """
    try:
        query = db.query(Provider)

        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Provider.nombre.ilike(search_pattern))
                | (Provider.especialidad.ilike(search_pattern))
            )

        # Apply pagination
        providers = query.order_by(Provider.nombre).offset(offset).limit(limit).all()

        logger.info("PROVIDERS_LISTED", count=len(providers), search=search)
        return [p.to_dict() for p in providers]

    except Exception as e:
        logger.error("PROVIDERS_LIST_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list providers")


@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: str, db: Session = Depends(get_db_dependency)):
    """Get provider by ID.

    Args:
        provider_id: Provider UUID
        db: Database session (injected)

    Returns:
        Provider record

    Raises:
        404: Provider not found
    """
    try:
        provider = db.query(Provider).filter(Provider.provider_id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

        logger.info("PROVIDER_RETRIEVED", provider_id=provider_id)
        return provider.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PROVIDER_GET_FAILED", error=str(e), provider_id=provider_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve provider")


@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(
    provider_id: str, updates: ProviderUpdate, db: Session = Depends(get_db_dependency)
):
    """Update provider record.

    Args:
        provider_id: Provider UUID
        updates: Fields to update
        db: Database session (injected)

    Returns:
        Updated provider record

    Raises:
        404: Provider not found
        400: Cédula conflict
    """
    try:
        provider = db.query(Provider).filter(Provider.provider_id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

        # Check cédula conflict
        if updates.cedula_profesional and updates.cedula_profesional != provider.cedula_profesional:
            existing = (
                db.query(Provider)
                .filter(Provider.cedula_profesional == updates.cedula_profesional)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cédula {updates.cedula_profesional} already exists",
                )

        # Apply updates
        update_data = updates.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(provider, key, value)

        db.commit()
        db.refresh(provider)

        logger.info("PROVIDER_UPDATED", provider_id=provider_id, fields=list(update_data.keys()))
        return provider.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PROVIDER_UPDATE_FAILED", error=str(e), provider_id=provider_id)
        raise HTTPException(status_code=500, detail="Failed to update provider")


@router.delete("/{provider_id}", status_code=204)
def delete_provider(provider_id: str, db: Session = Depends(get_db_dependency)):
    """Delete provider record.

    Args:
        provider_id: Provider UUID
        db: Database session (injected)

    Raises:
        404: Provider not found
    """
    try:
        provider = db.query(Provider).filter(Provider.provider_id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

        db.delete(provider)
        db.commit()

        logger.info("PROVIDER_DELETED", provider_id=provider_id)
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error("PROVIDER_DELETE_FAILED", error=str(e), provider_id=provider_id)
        raise HTTPException(status_code=500, detail="Failed to delete provider")
