"""Pydantic schemas for FI Receptionist Check-in API.

Request/Response schemas matching frontend TypeScript types exactly.

Author: Bernard Uriza Orozco
Created: 2025-11-21
Card: FI-CHECKIN-001
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# ENUMS (match TypeScript exactly)
# =============================================================================


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class AppointmentType(str, Enum):
    FIRST_VISIT = "first_visit"
    FOLLOW_UP = "follow_up"
    PROCEDURE = "procedure"
    EMERGENCY = "emergency"
    TELEMEDICINE = "telemedicine"


class PendingActionType(str, Enum):
    UPDATE_CONTACT = "update_contact"
    UPDATE_INSURANCE = "update_insurance"
    SIGN_CONSENT = "sign_consent"
    SIGN_PRIVACY = "sign_privacy"
    PAY_COPAY = "pay_copay"
    PAY_BALANCE = "pay_balance"
    UPLOAD_LABS = "upload_labs"
    UPLOAD_IMAGING = "upload_imaging"
    FILL_QUESTIONNAIRE = "fill_questionnaire"
    VERIFY_IDENTITY = "verify_identity"


class PendingActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class CheckinStep(str, Enum):
    SCAN_QR = "scan_qr"
    IDENTIFY = "identify"
    CONFIRM_IDENTITY = "confirm_identity"
    PENDING_ACTIONS = "pending_actions"
    SUCCESS = "success"
    ERROR = "error"


class DeviceType(str, Enum):
    MOBILE = "mobile"
    KIOSK = "kiosk"
    TABLET = "tablet"


# =============================================================================
# PENDING ACTION SCHEMAS
# =============================================================================


class PendingActionResponse(BaseModel):
    """Pending action response matching TypeScript PendingAction."""

    action_id: str
    action_type: PendingActionType
    status: PendingActionStatus

    title: str
    description: str | None = None
    icon: str | None = None

    is_required: bool
    is_blocking: bool

    # For payments
    amount: float | None = None
    currency: str | None = "MXN"

    # For documents
    document_type: str | None = None
    document_url: str | None = None
    signed_at: str | None = None

    # For uploads
    uploaded_file_id: str | None = None

    completed_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CompleteActionRequest(BaseModel):
    """Request to complete a pending action."""

    # For signatures
    signature_data: str | None = None  # Base64

    # For payments
    payment_intent_id: str | None = None

    # For uploads
    file_id: str | None = None


# =============================================================================
# APPOINTMENT SCHEMAS
# =============================================================================


class AppointmentBrief(BaseModel):
    """Brief appointment info for identification response."""

    appointment_id: str
    scheduled_at: str
    doctor_name: str
    appointment_type: AppointmentType


class AppointmentResponse(BaseModel):
    """Full appointment response."""

    appointment_id: str
    clinic_id: str
    patient_id: str
    doctor_id: str

    scheduled_at: str
    estimated_duration: int
    appointment_type: AppointmentType

    status: AppointmentStatus
    checked_in_at: str | None = None
    called_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    checkin_code: str
    checkin_code_expires_at: str

    reason: str | None = None
    notes: str | None = None

    pending_actions: List[PendingActionResponse] = []

    created_at: str
    updated_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# QR CODE SCHEMAS
# =============================================================================


class GenerateQRRequest(BaseModel):
    """Request to generate QR code for TV display."""

    clinic_id: str = Field(..., min_length=1)


class GenerateQRResponse(BaseModel):
    """QR code response matching TypeScript GenerateQRResponse."""

    qr_data: str  # Base64 encoded PNG
    qr_url: str  # URL encoded in QR
    expires_at: str  # ISO datetime


# =============================================================================
# SESSION SCHEMAS
# =============================================================================


class StartSessionRequest(BaseModel):
    """Request to start check-in session."""

    clinic_id: str = Field(..., min_length=1)
    device_type: DeviceType = Field(default=DeviceType.MOBILE)


class CheckinSessionResponse(BaseModel):
    """Check-in session response matching TypeScript CheckinSession."""

    session_id: str
    clinic_id: str

    current_step: CheckinStep
    started_at: str
    completed_at: str | None = None

    identification_method: str | None = None

    appointment_id: str | None = None
    patient_id: str | None = None

    device_type: DeviceType

    expires_at: str

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# IDENTIFICATION SCHEMAS
# =============================================================================


class IdentifyByCodeRequest(BaseModel):
    """Identify patient by 6-digit check-in code."""

    clinic_id: str = Field(..., min_length=1)
    checkin_code: str = Field(..., min_length=6, max_length=6)

    @field_validator("checkin_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Check-in code must be 6 digits")
        return v


class IdentifyByCurpRequest(BaseModel):
    """Identify patient by CURP."""

    clinic_id: str = Field(..., min_length=1)
    curp: str = Field(..., min_length=18, max_length=18)

    @field_validator("curp")
    @classmethod
    def validate_curp(cls, v: str) -> str:
        v = v.upper()
        curp_regex = r"^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$"
        if not re.match(curp_regex, v):
            raise ValueError("Invalid CURP format")
        return v


class IdentifyByNameRequest(BaseModel):
    """Identify patient by name and date of birth."""

    clinic_id: str = Field(..., min_length=1)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: str = Field(..., description="YYYY-MM-DD format")

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v


class PatientBrief(BaseModel):
    """Brief patient info for identification response."""

    patient_id: str
    full_name: str
    masked_curp: str | None = None


class IdentifyPatientResponse(BaseModel):
    """Response for patient identification matching TypeScript."""

    success: bool
    patient: PatientBrief | None = None
    appointment: AppointmentBrief | None = None
    pending_actions: List[PendingActionResponse] | None = None
    error: str | None = None


# =============================================================================
# COMPLETE CHECK-IN SCHEMAS
# =============================================================================


class CompleteCheckinRequest(BaseModel):
    """Request to complete check-in."""

    session_id: str
    appointment_id: str
    completed_actions: List[str] = []  # action_ids
    skipped_actions: List[str] = []  # action_ids (non-required only)


class CompleteCheckinResponse(BaseModel):
    """Response for completed check-in matching TypeScript."""

    success: bool
    checkin_time: str
    position_in_queue: int
    estimated_wait_minutes: int
    message: str
    error: str | None = None


# =============================================================================
# WAITING ROOM SCHEMAS
# =============================================================================


class WaitingRoomPatient(BaseModel):
    """Patient in waiting room matching TypeScript."""

    patient_id: str
    patient_name: str
    appointment_id: str

    checked_in_at: str
    position_in_queue: int
    estimated_wait_minutes: int

    doctor_id: str
    doctor_name: str

    display_name: str  # Privacy-aware: "María G."
    is_next: bool


class WaitingRoomState(BaseModel):
    """Waiting room state matching TypeScript."""

    clinic_id: str

    patients_waiting: List[WaitingRoomPatient]
    total_waiting: int

    avg_wait_time_minutes: int
    patients_seen_today: int

    next_available_slot: str | None = None

    updated_at: str


class GetWaitingRoomResponse(BaseModel):
    """Wrapper for waiting room state."""

    state: WaitingRoomState


# =============================================================================
# ACTIONS LIST RESPONSE
# =============================================================================


class GetActionsResponse(BaseModel):
    """Response for pending actions list."""

    actions: List[PendingActionResponse]
