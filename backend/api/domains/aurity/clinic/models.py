"""Clinic API Request/Response Models.

Pydantic models for clinic, doctor, and appointment endpoints.
Extracted from monolithic clinics.py for modularity.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.models.checkin_models import AppointmentStatus, AppointmentType


# =============================================================================
# CLINIC SCHEMAS
# =============================================================================


class ClinicCreate(BaseModel):
    """Schema for creating a new clinic."""

    name: str = Field(..., min_length=1, max_length=200)
    specialty: str = Field(default="general", max_length=100)
    timezone: str = Field(default="America/Mexico_City", max_length=50)
    welcome_message: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default="#6366f1", max_length=20)
    logo_url: str | None = None
    checkin_qr_enabled: bool = True
    chat_enabled: bool = True
    payments_enabled: bool = False
    subscription_plan: str = Field(default="free", max_length=50)


class ClinicUpdate(BaseModel):
    """Schema for updating a clinic."""

    name: str | None = Field(default=None, max_length=200)
    specialty: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=50)
    welcome_message: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default=None, max_length=20)
    logo_url: str | None = None
    checkin_qr_enabled: bool | None = None
    chat_enabled: bool | None = None
    payments_enabled: bool | None = None
    subscription_plan: str | None = Field(default=None, max_length=50)


class ClinicResponse(BaseModel):
    """Clinic response schema."""

    clinic_id: str
    name: str
    specialty: str
    timezone: str
    welcome_message: str | None = None
    primary_color: str | None = None
    logo_url: str | None = None
    checkin_qr_enabled: bool
    chat_enabled: bool
    payments_enabled: bool
    subscription_plan: str
    is_active: bool
    created_at: str
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ClinicListResponse(BaseModel):
    """Response for clinic list."""

    clinics: list[ClinicResponse]
    total: int


# =============================================================================
# DOCTOR SCHEMAS
# =============================================================================


class DoctorCreate(BaseModel):
    """Schema for creating a doctor."""

    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    especialidad: str | None = Field(default=None, max_length=100)
    cedula_profesional: str | None = Field(default=None, max_length=20)
    avg_consultation_minutes: int = Field(default=20, ge=5, le=180)


class DoctorUpdate(BaseModel):
    """Schema for updating a doctor."""

    nombre: str | None = Field(default=None, max_length=100)
    apellido: str | None = Field(default=None, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    especialidad: str | None = Field(default=None, max_length=100)
    cedula_profesional: str | None = Field(default=None, max_length=20)
    avg_consultation_minutes: int | None = Field(default=None, ge=5, le=180)
    work_start_time: str | None = Field(
        default=None, pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
    )
    work_end_time: str | None = Field(
        default=None, pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
    )
    working_hours: dict | None = Field(
        default=None, description="Full availability config as JSONB"
    )
    is_active: bool | None = None


class DoctorResponse(BaseModel):
    """Doctor response schema."""

    doctor_id: str
    clinic_id: str
    nombre: str
    apellido: str
    display_name: str | None = None
    especialidad: str | None = None
    cedula_profesional: str | None = None
    avg_consultation_minutes: int
    work_start_time: str | None = None
    work_end_time: str | None = None
    working_hours: dict | None = None
    is_active: bool
    created_at: str
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DoctorListResponse(BaseModel):
    """Response for doctor list."""

    doctors: list[DoctorResponse]
    total: int


class DoctorLimitInfoResponse(BaseModel):
    """Response schema for doctor limit information."""

    current_count: int
    max_allowed: int | None  # None = unlimited
    can_add: bool
    plan_name: str
    plan_display_name: str
    has_override: bool


class DoctorOverrideUpdate(BaseModel):
    """Schema for updating doctor override."""

    max_doctors_override: int | None = Field(
        default=None,
        ge=1,
        le=1000,
        description="Custom doctor limit. NULL removes the override and uses plan limit.",
    )


# =============================================================================
# APPOINTMENT SCHEMAS
# =============================================================================


class AppointmentCreate(BaseModel):
    """Schema for creating an appointment with auto-generated check-in code."""

    patient_id: str = Field(..., min_length=1)
    doctor_id: str = Field(..., min_length=1)
    scheduled_at: str = Field(..., description="ISO datetime")
    appointment_type: AppointmentType = AppointmentType.FOLLOW_UP
    estimated_duration: int = Field(default=20, ge=5, le=180)
    reason: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment."""

    scheduled_at: str | None = Field(default=None, description="ISO datetime")
    estimated_duration: int | None = Field(default=None, ge=5, le=180)
    doctor_id: str | None = Field(default=None, min_length=1)
    appointment_type: AppointmentType | None = None
    status: AppointmentStatus | None = None
    reason: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)


class AppointmentResponse(BaseModel):
    """Appointment response with check-in code."""

    appointment_id: str
    clinic_id: str
    patient_id: str
    doctor_id: str
    scheduled_at: str
    estimated_duration: int
    appointment_type: str
    status: str
    checkin_code: str
    checkin_code_expires_at: str
    reason: str | None = None
    notes: str | None = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AppointmentListResponse(BaseModel):
    """Response for appointment list."""

    appointments: list[AppointmentResponse]
    total: int
