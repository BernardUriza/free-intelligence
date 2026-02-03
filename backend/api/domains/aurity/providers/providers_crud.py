"""Provider CRUD Endpoints.

POST   /providers - Create provider
GET    /providers - List providers
GET    /providers/{id} - Get provider
PUT    /providers/{id} - Update provider
DELETE /providers/{id} - Delete provider

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
Card: FI-DATA-DB-001
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.database import get_db_dependency
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.models.db_models import Provider
from backend.utils.common.logging.logger import get_logger

from .models import ProviderCreate, ProviderResponse, ProviderUpdate

logger = get_logger(__name__)

router = APIRouter(prefix="/providers", tags=["Providers"])


# ============================================================================
# CRUD Endpoints
# ============================================================================


@router.post("/", response_model=ProviderResponse, status_code=201)
def create_provider(
    provider: ProviderCreate,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
    """Create a new provider record.

    Args:
        provider: Provider data
        db: Database session (injected)

    Returns:
        Created provider with assigned ID

    Raises:
        400: Cedula already exists
        500: Database error
    """
    try:
        # Check for duplicate cedula
        if provider.cedula_profesional:
            existing = (
                db.query(Provider)
                .filter(Provider.cedula_profesional == provider.cedula_profesional)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cedula {provider.cedula_profesional} already exists",
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

        audit_service.log_action(
            action="provider_created",
            user_id=current_user.id,
            clinic_id=None,
            resource=str(db_provider.provider_id),
            result="success",
        )
        return db_provider.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="provider_create_failed",
            user_id=current_user.id,
            resource="provider",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to create provider")


@router.get("/", response_model=list[ProviderResponse])
def list_providers(
    search: str | None = Query(None, description="Search by nombre or especialidad"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Skip N results"),
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
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
        audit_service.log_action(
            action="providers_list_failed",
            user_id=current_user.id,
            resource="providers",
            result="failure",
            details={"error": str(e), "search": search},
        )
        raise HTTPException(status_code=500, detail="Failed to list providers")


@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider(
    provider_id: str,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
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
        audit_service.log_action(
            action="provider_get_failed",
            user_id=current_user.id,
            resource=provider_id,
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve provider")


@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(
    provider_id: str,
    updates: ProviderUpdate,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
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
        400: Cedula conflict
    """
    try:
        provider = db.query(Provider).filter(Provider.provider_id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

        # Check cedula conflict
        if updates.cedula_profesional and updates.cedula_profesional != provider.cedula_profesional:
            existing = (
                db.query(Provider)
                .filter(Provider.cedula_profesional == updates.cedula_profesional)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cedula {updates.cedula_profesional} already exists",
                )

        # Apply updates
        update_data = updates.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(provider, key, value)

        db.commit()
        db.refresh(provider)

        audit_service.log_action(
            action="provider_updated",
            user_id=current_user.id,
            clinic_id=None,
            resource=provider_id,
            result="success",
            metadata={"fields_updated": list(update_data.keys())},
        )
        return provider.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="provider_update_failed",
            user_id=current_user.id,
            resource=provider_id,
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to update provider")


@router.delete("/{provider_id}", status_code=204)
def delete_provider(
    provider_id: str,
    db: Session = Depends(get_db_dependency),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
):
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

        audit_service.log_action(
            action="provider_deleted",
            user_id=current_user.id,
            clinic_id=None,
            resource=provider_id,
            result="success",
        )
        return None

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="provider_delete_failed",
            user_id=current_user.id,
            resource=provider_id,
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to delete provider")
