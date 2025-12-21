"""User-Clinic membership API endpoints.

Allows authenticated users to link themselves to clinics
and manage their clinic membership.

Author: Bernard Uriza Orozco
Created: 2025-12-11
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.database import get_db_dependency
from backend.src.fi_common.logging.logger import get_logger
from backend.models.checkin_models import Clinic, ClinicRole, Doctor

logger = get_logger(__name__)

router = APIRouter(prefix="/users/me", tags=["User Clinic"])


# =============================================================================
# SCHEMAS
# =============================================================================


class LinkToClinicRequest(BaseModel):
    """Request to link user to a clinic."""

    clinic_id: str = Field(..., description="Clinic ID to join")
    role: ClinicRole = Field(default=ClinicRole.DOCTOR, description="Role in clinic")
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    especialidad: str | None = Field(default=None, max_length=100)
    cedula_profesional: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(use_enum_values=True)


class ClinicMembershipResponse(BaseModel):
    """User's clinic membership info."""

    doctor_id: str
    clinic_id: str
    clinic_name: str
    clinic_role: str
    nombre: str
    apellido: str
    display_name: str
    especialidad: str | None
    email: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LinkToClinicResponse(BaseModel):
    """Response after linking user to clinic."""

    success: bool
    message: str
    membership: ClinicMembershipResponse | None = None


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/clinic-membership")
async def get_clinic_membership(
    auth0_user_id: str,
    email: str | None = None,
    db: Session = Depends(get_db_dependency),
) -> ClinicMembershipResponse | dict:
    """Get current user's clinic membership.

    Args:
        auth0_user_id: Auth0 user ID (from frontend)
        email: User's email (optional, for display)
        db: Database session

    Returns:
        Clinic membership info or empty dict if not linked
    """
    logger.info(
        "GET_CLINIC_MEMBERSHIP",
        auth0_user_id=auth0_user_id,
    )

    # Find doctor record linked to this Auth0 user
    doctor = db.query(Doctor).filter(Doctor.auth0_user_id == auth0_user_id).first()

    if not doctor:
        return {"linked": False, "message": "User is not linked to any clinic"}

    # Get clinic info
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
    auth0_user_id: str,
    email: str | None = None,
    db: Session = Depends(get_db_dependency),
) -> LinkToClinicResponse:
    """Link authenticated user to a clinic.

    Creates a new Doctor record linked to the user's Auth0 ID.
    User can only be linked to one clinic at a time.

    Args:
        request: Clinic and profile info
        auth0_user_id: Auth0 user ID (from frontend)
        email: User's email (from frontend)
        db: Database session

    Returns:
        Success status and membership info
    """
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


@router.delete("/unlink-from-clinic")
async def unlink_from_clinic(
    auth0_user_id: str,
    db: Session = Depends(get_db_dependency),
) -> dict:
    """Unlink user from their clinic.

    This removes the Doctor record, unlinking the user.
    Does NOT delete appointments or other related data.

    Args:
        auth0_user_id: Auth0 user ID
        db: Database session

    Returns:
        Success message
    """
    logger.info(
        "UNLINK_FROM_CLINIC_START",
        auth0_user_id=auth0_user_id,
    )

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


class AdminLinkUserRequest(BaseModel):
    """Admin request to link any user to a clinic."""

    auth0_user_id: str = Field(..., description="Auth0 user ID to link")
    email: str = Field(..., description="User's email")
    clinic_id: str = Field(..., description="Clinic ID to assign")
    role: ClinicRole = Field(default=ClinicRole.STAFF, description="Role in clinic")
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    especialidad: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(use_enum_values=True)


class AdminUserClinicInfo(BaseModel):
    """User's clinic assignment info for admin view."""

    auth0_user_id: str
    email: str
    doctor_id: str | None
    clinic_id: str | None
    clinic_name: str | None
    clinic_role: str | None
    nombre: str | None
    apellido: str | None
    is_linked: bool

    model_config = ConfigDict(from_attributes=True)


@router.post("/admin/assign-to-clinic")
async def admin_assign_user_to_clinic(
    request: AdminLinkUserRequest,
    db: Session = Depends(get_db_dependency),
) -> LinkToClinicResponse:
    """Admin endpoint to assign any user to a clinic.

    This allows superadmin to create clinic memberships for users.
    If user is already linked, updates their assignment.

    Args:
        request: User and clinic info
        db: Database session

    Returns:
        Success status and membership info

    Note: Authorization check should be done at API gateway/middleware level
    """
    logger.info(
        "ADMIN_ASSIGN_USER_START",
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


@router.delete("/admin/unassign-user/{auth0_user_id}")
async def admin_unassign_user_from_clinic(
    auth0_user_id: str,
    db: Session = Depends(get_db_dependency),
) -> dict:
    """Admin endpoint to remove user from their clinic.

    Args:
        auth0_user_id: Auth0 user ID to unassign
        db: Database session

    Returns:
        Success message
    """
    logger.info(
        "ADMIN_UNASSIGN_USER_START",
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
    db: Session = Depends(get_db_dependency),
) -> AdminUserClinicInfo:
    """Get clinic assignment info for a specific user.

    Args:
        auth0_user_id: Auth0 user ID
        db: Database session

    Returns:
        User's clinic assignment info
    """
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
