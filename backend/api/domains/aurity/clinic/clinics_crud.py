"""Clinic CRUD Endpoints.

GET    /clinics - List clinics
GET    /clinics/{id} - Get clinic
POST   /clinics - Create clinic
PATCH  /clinics/{id} - Update clinic
DELETE /clinics/{id} - Delete clinic

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.api.audit.dependencies import get_audit_service
from backend.database import get_db_dependency
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User, UserRole
from backend.infrastructure.auth.utils import validate_clinic_access
from backend.models.checkin_models import Clinic
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .helpers import model_to_response
from .models import ClinicCreate, ClinicListResponse, ClinicResponse, ClinicUpdate

logger = get_logger(__name__)

router = APIRouter(tags=["Clinics - CRUD"])


@router.get("", response_model=ClinicListResponse)
def list_clinics(
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> ClinicListResponse:
    """List clinics (SUPERADMIN sees all, regular users see only their clinic)."""
    # SUPERADMIN: See all clinics
    if UserRole.SUPERADMIN in current_user.roles:
        query = db.query(Clinic)
        if active_only:
            query = query.filter(Clinic.is_active.is_(True))

        total = query.count()
        clinics = query.offset(skip).limit(limit).all()

        return ClinicListResponse(
            clinics=[model_to_response(c, ClinicResponse) for c in clinics],
            total=total,
        )

    # Regular user: Only their clinic
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=403,
            detail="User has no clinic assigned. Create a clinic first.",
        )

    clinic = db.query(Clinic).filter(Clinic.clinic_id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Return as list (consistent API)
    return ClinicListResponse(
        clinics=[model_to_response(clinic, ClinicResponse)],
        total=1,
    )


@router.get("/{clinic_id}", response_model=ClinicResponse)
def get_clinic(
    clinic_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> ClinicResponse:
    """Get a clinic by ID."""
    validate_clinic_access(clinic_id, current_user)

    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return model_to_response(clinic, ClinicResponse)


@router.post("", response_model=ClinicResponse, status_code=201)
async def create_clinic(
    request: ClinicCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> ClinicResponse:
    """Create a new clinic (self-service - any authenticated user can create)."""
    # Optional: Validate user doesn't already have a clinic (remove if multi-clinic allowed)
    if current_user.clinic_id:
        raise HTTPException(
            status_code=400,
            detail=f"User already assigned to clinic '{current_user.clinic_id}'. Cannot create multiple clinics.",
        )

    # Create clinic
    clinic = Clinic(**request.model_dump())
    db.add(clinic)
    db.commit()
    db.refresh(clinic)

    # Auto-assign clinic to the creating user in our local users table
    from backend.infrastructure.auth.services.user_service import UserService

    user_svc = UserService(db)
    user_svc.assign_clinic(current_user.id, str(clinic.clinic_id))

    logger.info(
        "CLINIC_CREATED",
        clinic_id=str(clinic.clinic_id),
        name=clinic.name,
        creator_user_id=current_user.id,
    )
    return model_to_response(clinic, ClinicResponse)


@router.patch("/{clinic_id}", response_model=ClinicResponse)
def update_clinic(
    clinic_id: str,
    request: ClinicUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
    audit_service=Depends(get_audit_service),
) -> ClinicResponse:
    """Update a clinic."""
    validate_clinic_access(clinic_id, current_user, action="update clinic")

    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clinic, field, value)

    clinic.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(clinic)

    audit_service.log_action(
        action="clinic_updated",
        user_id=current_user.id,
        clinic_id=current_user.clinic_id or clinic_id,
        resource=clinic_id,
        result="success",
    )
    return model_to_response(clinic, ClinicResponse)


@router.delete("/{clinic_id}", status_code=204)
def delete_clinic(
    clinic_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
    audit_service=Depends(get_audit_service),
) -> None:
    """Soft delete a clinic (set is_active=False)."""
    validate_clinic_access(clinic_id, current_user, action="delete clinic")

    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    clinic.is_active = False
    clinic.updated_at = datetime.now(UTC)
    db.commit()

    audit_service.log_action(
        action="clinic_deleted",
        user_id=current_user.id,
        clinic_id=current_user.clinic_id or clinic_id,
        resource=clinic_id,
        result="success",
    )
