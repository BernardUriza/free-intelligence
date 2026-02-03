"""User-Clinic Membership Endpoints.

Allows authenticated users to link themselves to clinics
and manage their clinic membership.

Endpoints:
- GET    /users/me/clinic-membership - Get current user's membership
- POST   /users/me/link-to-clinic - Link user to a clinic
- DELETE /users/me/unlink-from-clinic - Unlink from clinic
- POST   /users/me/admin/assign-to-clinic - Admin: assign user to clinic
- DELETE /users/me/admin/unassign-user/{id} - Admin: unassign user
- GET    /users/me/admin/user-clinic-info/{id} - Admin: get user info

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db_dependency
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.infrastructure.auth.utils import require_superadmin, validate_clinic_access
from backend.models.checkin_models import Clinic, ClinicRole, Doctor
from backend.utils.common.logging.logger import get_logger

from .user_clinic_models import (
    AdminLinkUserRequest,
    AdminUserClinicInfo,
    ClinicMembershipResponse,
    LinkToClinicRequest,
    LinkToClinicResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/users/me", tags=["User Clinic"])


# =============================================================================
# USER ENDPOINTS
# =============================================================================


@router.get("/clinic-membership", response_model=None)
async def get_clinic_membership(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> ClinicMembershipResponse | dict:
    """Get current user's clinic membership.

    Args:
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Clinic membership info or empty dict if not linked
    """
    auth0_user_id = current_user.id

    logger.info("GET_CLINIC_MEMBERSHIP", auth0_user_id=auth0_user_id)

    doctor = db.query(Doctor).filter(Doctor.auth0_user_id == auth0_user_id).first()

    if not doctor:
        return {"linked": False, "message": "User is not linked to any clinic"}

    clinic = db.query(Clinic).filter(Clinic.clinic_id == doctor.clinic_id).first()

    if not clinic:
        logger.warning(
            "CLINIC_NOT_FOUND_FOR_DOCTOR",
            doctor_id=str(doctor.doctor_id),
            clinic_id=str(doctor.clinic_id),
        )
        return {"linked": False, "message": "Clinic not found"}

    return ClinicMembershipResponse(
        doctor_id=str(doctor.doctor_id),
        clinic_id=str(doctor.clinic_id),
        clinic_name=clinic.name,
        clinic_role=doctor.clinic_role.value if doctor.clinic_role else "DOCTOR",
        nombre=doctor.nombre,
        apellido=doctor.apellido,
        display_name=doctor.full_display_name,
        especialidad=doctor.especialidad,
        email=doctor.email,
        is_active=doctor.is_active or True,
    )


@router.post("/link-to-clinic")
async def link_to_clinic(
    request: LinkToClinicRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> LinkToClinicResponse:
    """Link authenticated user to a clinic.

    Creates a new Doctor record linked to the user's Auth0 ID.
    User can only be linked to one clinic at a time.

    Args:
        request: Clinic and profile info
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Success status and membership info
    """
    auth0_user_id = current_user.id
    email = current_user.email

    # SECURITY: Validate user can join requested clinic
    validate_clinic_access(request.clinic_id, current_user)

    logger.info(
        "LINK_TO_CLINIC_START",
        auth0_user_id=auth0_user_id,
        clinic_id=request.clinic_id,
        role=request.role,
    )

    # Check if user is already linked to a clinic
    existing = db.query(Doctor).filter(Doctor.auth0_user_id == auth0_user_id).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User is already linked to clinic {existing.clinic_id}. "
            "Unlink first to join a different clinic.",
        )

    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == request.clinic_id).first()

    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinic {request.clinic_id} not found",
        )

    # Create doctor record linked to Auth0 user
    doctor = Doctor(
        clinic_id=request.clinic_id,
        auth0_user_id=auth0_user_id,
        email=email,
        clinic_role=ClinicRole(request.role) if isinstance(request.role, str) else request.role,
        nombre=request.nombre,
        apellido=request.apellido,
        especialidad=request.especialidad,
        cedula_profesional=request.cedula_profesional,
        display_name=f"Dr. {request.apellido}",
        is_active=True,
    )

    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    logger.info(
        "LINK_TO_CLINIC_SUCCESS",
        auth0_user_id=auth0_user_id,
        doctor_id=str(doctor.doctor_id),
        clinic_id=request.clinic_id,
        role=request.role,
    )

    return LinkToClinicResponse(
        success=True,
        message=f"Successfully linked to {clinic.name}",
        membership=ClinicMembershipResponse(
            doctor_id=str(doctor.doctor_id),
            clinic_id=str(doctor.clinic_id),
            clinic_name=clinic.name,
            clinic_role=doctor.clinic_role.value if doctor.clinic_role else "DOCTOR",
            nombre=doctor.nombre,
            apellido=doctor.apellido,
            display_name=doctor.full_display_name,
            especialidad=doctor.especialidad,
            email=doctor.email,
            is_active=doctor.is_active or True,
        ),
    )


@router.delete("/unlink-from-clinic", response_model=None)
async def unlink_from_clinic(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> dict:
    """Unlink user from their clinic.

    This removes the Doctor record, unlinking the user.
    Does NOT delete appointments or other related data.

    Args:
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Success message
    """
    auth0_user_id = current_user.id

    logger.info("UNLINK_FROM_CLINIC_START", auth0_user_id=auth0_user_id)

    doctor = db.query(Doctor).filter(Doctor.auth0_user_id == auth0_user_id).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not linked to any clinic",
        )

    clinic_id = str(doctor.clinic_id)

    # Soft delete: just unlink, don't remove record
    doctor.auth0_user_id = None
    doctor.is_active = False
    db.commit()

    logger.info(
        "UNLINK_FROM_CLINIC_SUCCESS",
        auth0_user_id=auth0_user_id,
        clinic_id=clinic_id,
    )

    return {
        "success": True,
        "message": "Successfully unlinked from clinic",
        "clinic_id": clinic_id,
    }


# =============================================================================
# ADMIN ENDPOINTS - For superadmin to manage user-clinic assignments
# =============================================================================


@router.post("/admin/assign-to-clinic")
async def admin_assign_user_to_clinic(
    request: AdminLinkUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> LinkToClinicResponse:
    """Admin endpoint to assign any user to a clinic.

    This allows superadmin to create clinic memberships for users.
    If user is already linked, updates their assignment.

    Args:
        request: User and clinic info
        current_user: Authenticated user (must be SUPERADMIN)
        db: Database session

    Returns:
        Success status and membership info
    """
    require_superadmin(current_user)

    logger.info(
        "ADMIN_ASSIGN_USER_START",
        admin_user_id=current_user.id,
        target_auth0_user_id=request.auth0_user_id,
        clinic_id=request.clinic_id,
        role=request.role,
    )

    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == request.clinic_id).first()

    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinic {request.clinic_id} not found",
        )

    # Check if user is already linked to a clinic
    existing = db.query(Doctor).filter(Doctor.auth0_user_id == request.auth0_user_id).first()

    if existing:
        # Update existing assignment
        existing.clinic_id = request.clinic_id
        existing.email = request.email
        existing.clinic_role = (
            ClinicRole(request.role) if isinstance(request.role, str) else request.role
        )
        existing.nombre = request.nombre
        existing.apellido = request.apellido
        existing.especialidad = request.especialidad
        existing.display_name = (
            f"Dr. {request.apellido}"
            if request.role in [ClinicRole.DOCTOR, "DOCTOR"]
            else request.nombre
        )
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        doctor = existing

        logger.info(
            "ADMIN_ASSIGN_USER_UPDATED",
            admin_user_id=current_user.id,
            target_auth0_user_id=request.auth0_user_id,
            doctor_id=str(doctor.doctor_id),
            clinic_id=request.clinic_id,
            role=request.role,
        )
    else:
        # Create new doctor record
        doctor = Doctor(
            clinic_id=request.clinic_id,
            auth0_user_id=request.auth0_user_id,
            email=request.email,
            clinic_role=ClinicRole(request.role) if isinstance(request.role, str) else request.role,
            nombre=request.nombre,
            apellido=request.apellido,
            especialidad=request.especialidad,
            display_name=f"Dr. {request.apellido}"
            if request.role in [ClinicRole.DOCTOR, "DOCTOR"]
            else request.nombre,
            is_active=True,
        )

        db.add(doctor)
        db.commit()
        db.refresh(doctor)

        logger.info(
            "ADMIN_ASSIGN_USER_CREATED",
            admin_user_id=current_user.id,
            target_auth0_user_id=request.auth0_user_id,
            doctor_id=str(doctor.doctor_id),
            clinic_id=request.clinic_id,
            role=request.role,
        )

    return LinkToClinicResponse(
        success=True,
        message=f"User assigned to {clinic.name}",
        membership=ClinicMembershipResponse(
            doctor_id=str(doctor.doctor_id),
            clinic_id=str(doctor.clinic_id),
            clinic_name=clinic.name,
            clinic_role=doctor.clinic_role.value if doctor.clinic_role else "STAFF",
            nombre=doctor.nombre,
            apellido=doctor.apellido,
            display_name=doctor.full_display_name,
            especialidad=doctor.especialidad,
            email=doctor.email,
            is_active=doctor.is_active or True,
        ),
    )


@router.delete("/admin/unassign-user/{auth0_user_id}", response_model=None)
async def admin_unassign_user_from_clinic(
    auth0_user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> dict:
    """Admin endpoint to remove user from their clinic.

    Args:
        auth0_user_id: Auth0 user ID to unassign
        current_user: Authenticated user (must be SUPERADMIN)
        db: Database session

    Returns:
        Success message
    """
    require_superadmin(current_user)

    logger.info(
        "ADMIN_UNASSIGN_USER_START",
        admin_user_id=current_user.id,
        target_auth0_user_id=auth0_user_id,
    )

    doctor = db.query(Doctor).filter(Doctor.auth0_user_id == auth0_user_id).first()

    if not doctor:
        return {
            "success": True,
            "message": "User was not linked to any clinic",
        }

    clinic_id = str(doctor.clinic_id)

    # Soft delete: unlink and deactivate
    doctor.auth0_user_id = None
    doctor.is_active = False
    db.commit()

    logger.info(
        "ADMIN_UNASSIGN_USER_SUCCESS",
        admin_user_id=current_user.id,
        target_auth0_user_id=auth0_user_id,
        clinic_id=clinic_id,
    )

    return {
        "success": True,
        "message": "User unassigned from clinic",
        "clinic_id": clinic_id,
    }


@router.get("/admin/user-clinic-info/{auth0_user_id}")
async def admin_get_user_clinic_info(
    auth0_user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
) -> AdminUserClinicInfo:
    """Get clinic assignment info for a specific user.

    Args:
        auth0_user_id: Auth0 user ID to query
        current_user: Authenticated user (must be SUPERADMIN)
        db: Database session

    Returns:
        User's clinic assignment info
    """
    require_superadmin(current_user)

    logger.info(
        "ADMIN_GET_USER_CLINIC_INFO",
        admin_user_id=current_user.id,
        target_auth0_user_id=auth0_user_id,
    )

    doctor = db.query(Doctor).filter(Doctor.auth0_user_id == auth0_user_id).first()

    if not doctor:
        return AdminUserClinicInfo(
            auth0_user_id=auth0_user_id,
            email="",
            doctor_id=None,
            clinic_id=None,
            clinic_name=None,
            clinic_role=None,
            nombre=None,
            apellido=None,
            is_linked=False,
        )

    clinic = db.query(Clinic).filter(Clinic.clinic_id == doctor.clinic_id).first()

    return AdminUserClinicInfo(
        auth0_user_id=auth0_user_id,
        email=doctor.email or "",
        doctor_id=str(doctor.doctor_id),
        clinic_id=str(doctor.clinic_id),
        clinic_name=clinic.name if clinic else None,
        clinic_role=doctor.clinic_role.value if doctor.clinic_role else None,
        nombre=doctor.nombre,
        apellido=doctor.apellido,
        is_linked=True,
    )
