"""User-Clinic Membership Models - Pydantic schemas.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.models.checkin_models import ClinicRole


# ============================================================================
# Request Schemas
# ============================================================================


class LinkToClinicRequest(BaseModel):
    """Request to link user to a clinic."""

    clinic_id: str = Field(..., description="Clinic ID to join")
    role: ClinicRole = Field(default=ClinicRole.DOCTOR, description="Role in clinic")
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    especialidad: str | None = Field(default=None, max_length=100)
    cedula_profesional: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(use_enum_values=True)


class AdminLinkUserRequest(BaseModel):
    """Admin request to link any user to a clinic."""

    user_id: str = Field(..., description="JWT user ID to link")
    email: str = Field(..., description="User's email")
    clinic_id: str = Field(..., description="Clinic ID to assign")
    role: ClinicRole = Field(default=ClinicRole.STAFF, description="Role in clinic")
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    especialidad: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(use_enum_values=True)


# ============================================================================
# Response Schemas
# ============================================================================


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


class AdminUserClinicInfo(BaseModel):
    """User's clinic assignment info for admin view."""

    user_id: str
    email: str
    doctor_id: str | None
    clinic_id: str | None
    clinic_name: str | None
    clinic_role: str | None
    nombre: str | None
    apellido: str | None
    is_linked: bool

    model_config = ConfigDict(from_attributes=True)
