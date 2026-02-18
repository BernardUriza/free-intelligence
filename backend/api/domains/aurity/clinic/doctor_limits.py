"""Doctor Limits Endpoints.

GET    /clinics/{id}/doctor-limits - Get doctor limits
PATCH  /clinics/{id}/doctor-override - Update doctor override

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.database import get_db_dependency
from backend.domain.clinic.services.doctor_limits import get_doctor_limit_info
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.infrastructure.auth.utils import require_superadmin, validate_clinic_access
from backend.models.checkin_models import Clinic
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from .helpers import model_to_response
from .models import ClinicResponse, DoctorLimitInfoResponse, DoctorOverrideUpdate

logger = get_logger(__name__)

router = APIRouter(tags=["Clinics - Doctor Limits"])


@router.get("/{clinic_id}/doctor-limits", response_model=DoctorLimitInfoResponse)
def get_doctor_limits(
    clinic_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> DoctorLimitInfoResponse:
    """Get doctor limit information for a clinic.

    Returns current count, maximum allowed, and whether more doctors can be added.
    """
    validate_clinic_access(clinic_id, current_user)

    clinic = (
        db.query(Clinic)
        .options(joinedload(Clinic.subscription))
        .filter(Clinic.clinic_id == clinic_id)
        .first()
    )
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    info = get_doctor_limit_info(db, clinic)
    return DoctorLimitInfoResponse(**info)


@router.patch("/{clinic_id}/doctor-override", response_model=ClinicResponse)
def update_doctor_override(
    clinic_id: str,
    request: DoctorOverrideUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> ClinicResponse:
    """Update max_doctors_override for a clinic.

    Requires FI-superadmin role.
    Set to NULL to remove override and use plan limit.
    """
    require_superadmin(current_user)

    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    old_override = clinic.max_doctors_override
    clinic.max_doctors_override = request.max_doctors_override
    clinic.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(clinic)

    logger.info(
        "DOCTOR_OVERRIDE_UPDATED",
        clinic_id=clinic_id,
        old_override=old_override,
        new_override=request.max_doctors_override,
        user_id=current_user.id,
    )

    return model_to_response(clinic, ClinicResponse)
