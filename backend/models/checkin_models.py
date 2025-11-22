"""SQLAlchemy models for FI Receptionist Check-in System.

Database models for patient self-service check-in, appointments,
pending actions, and waiting room management.

Author: Bernard Uriza Orozco
Created: 2025-11-21
Card: FI-CHECKIN-001
"""

from __future__ import annotations

import enum
import secrets
from datetime import datetime, timedelta
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from typing import List  # noqa: F401 - referenced in string annotations
from uuid import uuid4

from backend.models.db_models import Base

# =============================================================================
# ENUMS
# =============================================================================


class AppointmentStatus(str, enum.Enum):
    """Appointment lifecycle status."""

    SCHEDULED = "scheduled"  # Cita programada
    CONFIRMED = "confirmed"  # Paciente confirmó
    CHECKED_IN = "checked_in"  # Paciente hizo check-in
    IN_PROGRESS = "in_progress"  # En consulta
    COMPLETED = "completed"  # Consulta terminada
    NO_SHOW = "no_show"  # No se presentó
    CANCELLED = "cancelled"  # Cancelada


class AppointmentType(str, enum.Enum):
    """Type of medical appointment."""

    FIRST_VISIT = "first_visit"  # Primera consulta
    FOLLOW_UP = "follow_up"  # Seguimiento
    PROCEDURE = "procedure"  # Procedimiento
    EMERGENCY = "emergency"  # Urgencia
    TELEMEDICINE = "telemedicine"  # Consulta virtual


class PendingActionType(str, enum.Enum):
    """Types of actions patient must complete at check-in."""

    UPDATE_CONTACT = "update_contact"  # Actualizar teléfono/email
    UPDATE_INSURANCE = "update_insurance"  # Actualizar seguro
    SIGN_CONSENT = "sign_consent"  # Firmar consentimiento
    SIGN_PRIVACY = "sign_privacy"  # Firmar aviso privacidad
    PAY_COPAY = "pay_copay"  # Pagar copago
    PAY_BALANCE = "pay_balance"  # Pagar saldo
    UPLOAD_LABS = "upload_labs"  # Subir laboratorios
    UPLOAD_IMAGING = "upload_imaging"  # Subir estudios imagen
    FILL_QUESTIONNAIRE = "fill_questionnaire"  # Llenar cuestionario
    VERIFY_IDENTITY = "verify_identity"  # Verificar identidad


class PendingActionStatus(str, enum.Enum):
    """Status of a pending action."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class CheckinStep(str, enum.Enum):
    """Steps in the check-in flow."""

    SCAN_QR = "scan_qr"
    IDENTIFY = "identify"
    CONFIRM_IDENTITY = "confirm_identity"
    PENDING_ACTIONS = "pending_actions"
    SUCCESS = "success"
    ERROR = "error"


class DeviceType(str, enum.Enum):
    """Device type for check-in session."""

    MOBILE = "mobile"
    KIOSK = "kiosk"
    TABLET = "tablet"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def generate_uuid() -> str:
    """Generate UUID4 as string."""
    return str(uuid4())


def generate_checkin_code() -> str:
    """Generate 6-digit check-in code."""
    return "".join([str(secrets.randbelow(10)) for _ in range(6)])


def get_checkin_code_expiry() -> datetime:
    """Get expiry time for check-in code (end of today)."""
    now = datetime.utcnow()
    return now.replace(hour=23, minute=59, second=59, microsecond=999999)


def get_session_expiry() -> datetime:
    """Get expiry time for check-in session (15 minutes)."""
    return datetime.utcnow() + timedelta(minutes=15)


def get_qr_expiry() -> datetime:
    """Get expiry time for QR code (5 minutes)."""
    return datetime.utcnow() + timedelta(minutes=5)


# =============================================================================
# MODELS
# =============================================================================


class Clinic(Base):
    """Clinic/medical practice entity.

    Multi-tenant support - each clinic has isolated data.
    """

    __tablename__ = "clinics"

    clinic_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    specialty = Column(String(100), nullable=True)  # dental, general, etc.
    timezone = Column(String(50), default="America/Mexico_City")

    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#6366f1")  # Hex color
    welcome_message = Column(Text, nullable=True)

    # Feature flags
    checkin_qr_enabled = Column(Boolean, default=True)
    chat_enabled = Column(Boolean, default=False)
    payments_enabled = Column(Boolean, default=False)
    whatsapp_enabled = Column(Boolean, default=False)

    # Subscription
    subscription_plan = Column(String(50), default="starter")
    subscription_valid_until = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships (no type hints for SQLAlchemy 2.0 compatibility)
    doctors = relationship("Doctor", back_populates="clinic")
    appointments = relationship("Appointment", back_populates="clinic")

    def __repr__(self) -> str:
        return f"<Clinic {self.name} ({self.clinic_id})>"

    def to_dict(self) -> dict:
        return {
            "clinic_id": str(self.clinic_id),
            "name": self.name,
            "specialty": self.specialty,
            "timezone": self.timezone,
            "branding": {
                "logo_url": self.logo_url,
                "primary_color": self.primary_color,
                "welcome_message": self.welcome_message,
            },
            "features": {
                "checkin_qr": self.checkin_qr_enabled,
                "chat_enabled": self.chat_enabled,
                "payments_enabled": self.payments_enabled,
                "whatsapp_enabled": self.whatsapp_enabled,
            },
            "subscription": {
                "plan": self.subscription_plan,
                "valid_until": self.subscription_valid_until.isoformat()
                if self.subscription_valid_until
                else None,
            },
        }


class Doctor(Base):
    """Doctor/healthcare provider for appointments."""

    __tablename__ = "doctors"

    doctor_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    clinic_id = Column(UUID(as_uuid=False), ForeignKey("clinics.clinic_id"), nullable=False)

    # Identity
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    cedula_profesional = Column(String(20), unique=True, nullable=True)
    especialidad = Column(String(100), nullable=True)

    # Display
    display_name = Column(String(150), nullable=True)  # "Dr. López"
    photo_url = Column(String(500), nullable=True)

    # Availability
    avg_consultation_minutes = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    clinic = relationship("Clinic", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")

    def __repr__(self) -> str:
        return f"<Doctor {self.nombre} {self.apellido} ({self.doctor_id})>"

    @property
    def full_display_name(self) -> str:
        """Get display name or generate from name."""
        if self.display_name:
            return self.display_name
        return f"Dr. {self.apellido}"

    def to_dict(self) -> dict:
        return {
            "doctor_id": str(self.doctor_id),
            "clinic_id": str(self.clinic_id),
            "nombre": self.nombre,
            "apellido": self.apellido,
            "display_name": self.full_display_name,
            "especialidad": self.especialidad,
            "cedula_profesional": self.cedula_profesional,
            "photo_url": self.photo_url,
            "avg_consultation_minutes": self.avg_consultation_minutes,
        }


class Appointment(Base):
    """Patient appointment with check-in tracking."""

    __tablename__ = "appointments"

    appointment_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    clinic_id = Column(UUID(as_uuid=False), ForeignKey("clinics.clinic_id"), nullable=False)
    patient_id = Column(UUID(as_uuid=False), ForeignKey("patients.patient_id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=False), ForeignKey("doctors.doctor_id"), nullable=False)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    estimated_duration = Column(Integer, default=30)  # minutes
    appointment_type = Column(
        Enum(AppointmentType), nullable=False, default=AppointmentType.FOLLOW_UP
    )

    # Status tracking
    status = Column(
        Enum(AppointmentStatus), nullable=False, default=AppointmentStatus.SCHEDULED, index=True
    )
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    called_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Check-in code (6 digits, expires same day)
    checkin_code = Column(String(6), nullable=False, default=generate_checkin_code, index=True)
    checkin_code_expires_at = Column(
        DateTime(timezone=True), nullable=False, default=get_checkin_code_expiry
    )

    # Context
    reason = Column(Text, nullable=True)  # Motivo de consulta
    notes = Column(Text, nullable=True)  # Notas internas

    # Queue position (set on check-in)
    queue_position = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    clinic = relationship("Clinic", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    pending_actions = relationship(
        "PendingAction", back_populates="appointment", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_appointments_clinic_date", "clinic_id", "scheduled_at"),
        Index("ix_appointments_clinic_status", "clinic_id", "status"),
        Index(
            "ix_appointments_checkin_lookup", "clinic_id", "checkin_code", "checkin_code_expires_at"
        ),
    )

    def __repr__(self) -> str:
        return f"<Appointment {self.appointment_id} - {self.status.value}>"

    def to_dict(self) -> dict:
        return {
            "appointment_id": str(self.appointment_id),
            "clinic_id": str(self.clinic_id),
            "patient_id": str(self.patient_id),
            "doctor_id": str(self.doctor_id),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "estimated_duration": self.estimated_duration,
            "appointment_type": self.appointment_type.value,
            "status": self.status.value,
            "checked_in_at": self.checked_in_at.isoformat() if self.checked_in_at else None,
            "called_at": self.called_at.isoformat() if self.called_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "checkin_code": self.checkin_code,
            "checkin_code_expires_at": self.checkin_code_expires_at.isoformat()
            if self.checkin_code_expires_at
            else None,
            "reason": self.reason,
            "notes": self.notes,
            "queue_position": self.queue_position,
            "pending_actions": [a.to_dict() for a in self.pending_actions]
            if self.pending_actions
            else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PendingAction(Base):
    """Action patient must complete during check-in."""

    __tablename__ = "pending_actions"

    action_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    appointment_id = Column(
        UUID(as_uuid=False), ForeignKey("appointments.appointment_id"), nullable=False
    )

    # Type and status
    action_type = Column(Enum(PendingActionType), nullable=False)
    status = Column(Enum(PendingActionStatus), nullable=False, default=PendingActionStatus.PENDING)

    # Display
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(10), nullable=True)  # Emoji

    # Requirements
    is_required = Column(Boolean, default=False)
    is_blocking = Column(Boolean, default=False)  # Must complete before check-in

    # For payments
    amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="MXN")
    payment_intent_id = Column(String(100), nullable=True)  # Stripe

    # For documents
    document_type = Column(String(50), nullable=True)
    document_url = Column(String(500), nullable=True)
    signature_data = Column(Text, nullable=True)  # Base64 signature
    signed_at = Column(DateTime(timezone=True), nullable=True)

    # For uploads
    uploaded_file_id = Column(UUID(as_uuid=False), nullable=True)
    uploaded_file_url = Column(String(500), nullable=True)

    # Completion
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(String(50), nullable=True)  # patient, staff, system

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    appointment = relationship("Appointment", back_populates="pending_actions")

    def __repr__(self) -> str:
        return f"<PendingAction {self.action_type.value} - {self.status.value}>"

    def to_dict(self) -> dict:
        return {
            "action_id": str(self.action_id),
            "action_type": self.action_type.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "is_required": self.is_required,
            "is_blocking": self.is_blocking,
            "amount": float(self.amount) if self.amount else None,
            "currency": self.currency,
            "document_type": self.document_type,
            "document_url": self.document_url,
            "signed_at": self.signed_at.isoformat() if self.signed_at else None,
            "uploaded_file_id": str(self.uploaded_file_id) if self.uploaded_file_id else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class CheckinSession(Base):
    """Temporary session for check-in flow (expires in 15 min)."""

    __tablename__ = "checkin_sessions"

    session_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    clinic_id = Column(UUID(as_uuid=False), ForeignKey("clinics.clinic_id"), nullable=False)

    # Progress
    current_step = Column(Enum(CheckinStep), nullable=False, default=CheckinStep.IDENTIFY)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Identification
    identification_method = Column(String(20), nullable=True)  # code, curp, name_dob

    # Linked data (once identified)
    appointment_id = Column(UUID(as_uuid=False), nullable=True)
    patient_id = Column(UUID(as_uuid=False), nullable=True)

    # Device info
    device_type = Column(Enum(DeviceType), nullable=False, default=DeviceType.MOBILE)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Expiry
    expires_at = Column(DateTime(timezone=True), nullable=False, default=get_session_expiry)

    # Rate limiting
    identification_attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)

    # Index for lookup
    __table_args__ = (Index("ix_checkin_sessions_expires", "expires_at"),)

    def __repr__(self) -> str:
        return f"<CheckinSession {self.session_id} - {self.current_step.value}>"

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "session_id": str(self.session_id),
            "clinic_id": str(self.clinic_id),
            "current_step": self.current_step.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "identification_method": self.identification_method,
            "appointment_id": str(self.appointment_id) if self.appointment_id else None,
            "patient_id": str(self.patient_id) if self.patient_id else None,
            "device_type": self.device_type.value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class WaitingRoomEvent(Base):
    """Audit log for waiting room events (for WebSocket broadcasts)."""

    __tablename__ = "waiting_room_events"

    event_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    clinic_id = Column(UUID(as_uuid=False), ForeignKey("clinics.clinic_id"), nullable=False)

    # Event type
    event_type = Column(String(50), nullable=False)  # patient_checkin, patient_called, etc.
    event_data = Column(Text, nullable=True)  # JSON payload

    # Reference
    appointment_id = Column(UUID(as_uuid=False), nullable=True)
    patient_id = Column(UUID(as_uuid=False), nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Index for recent events
    __table_args__ = (Index("ix_waiting_room_events_clinic_time", "clinic_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<WaitingRoomEvent {self.event_type} @ {self.created_at}>"
