"""SQLAlchemy database models for PostgreSQL.

Patient and Provider models for medical record management.
UserPersonaConfig for per-user AI persona customization.
Uses SQLAlchemy ORM for PostgreSQL persistence.

Author: Bernard Uriza Orozco
Created: 2025-11-17
Updated: 2025-11-20 (Added UserPersonaConfig)
Card: FI-DATA-DB-001, FI-UI-DESIGN-003
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import (
    CHAR,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def generate_uuid() -> str:
    """Generate UUID4 as string."""
    return str(uuid4())


class Patient(Base):
    """Patient model - demographic and identity information.

    Stores patient demographic data with Mexican healthcare identifiers.
    Links to Session records via patient_id foreign key.

    Attributes:
        patient_id: UUID primary key
        nombre: First name(s)
        apellido: Last name(s) - paterno + materno
        fecha_nacimiento: Date of birth
        curp: CURP (Clave Única de Registro de Población) - Mexican ID
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "patients"

    patient_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    nombre = Column(String(100), nullable=False, index=True)
    apellido = Column(String(100), nullable=False, index=True)
    fecha_nacimiento = Column(DateTime(timezone=False), nullable=False)
    curp = Column(CHAR(18), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Patient {self.nombre} {self.apellido} ({self.patient_id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "patient_id": str(self.patient_id),
            "nombre": self.nombre,
            "apellido": self.apellido,
            "fecha_nacimiento": self.fecha_nacimiento.isoformat()
            if self.fecha_nacimiento is not None
            else None,
            "curp": self.curp,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
        }


class Provider(Base):
    """Healthcare provider model - physician/clinician information.

    Stores provider credentials and specialty information.
    Links to Session records via provider_id foreign key.

    Attributes:
        provider_id: UUID primary key
        nombre: Full name
        cedula_profesional: Professional license number (México)
        especialidad: Medical specialty (e.g., "Medicina Interna")
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "providers"

    provider_id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    nombre = Column(String(100), nullable=False, index=True)
    cedula_profesional = Column(CHAR(20), unique=True, nullable=True, index=True)
    especialidad = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Provider {self.nombre} - {self.especialidad} ({self.provider_id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "provider_id": str(self.provider_id),
            "nombre": self.nombre,
            "cedula_profesional": self.cedula_profesional,
            "especialidad": self.especialidad,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
        }


class UserPersonaConfig(Base):
    """User-specific AI persona configuration overrides.

    Stores per-user customizations of AI personas (templates in /backend/config/personas/).
    Uses NULL to indicate "use template default" - only stores actual overrides.

    Architecture: Template + Override Pattern
    - Templates: YAML files in /backend/config/personas/ (immutable base)
    - Overrides: This table (per-user customizations)
    - Merge logic: User override takes precedence, NULL = use template

    Attributes:
        user_id: UUID of user (provider_id FK)
        persona_id: Persona identifier (soap_editor, clinical_advisor, etc.)
        custom_prompt: Full system prompt override (NULL = use template)
        temperature: LLM temperature override (NULL = use template)
        max_tokens: Max tokens override (NULL = use template)
        is_active: Whether this persona is active for user
        created_at: When user first cloned/customized this persona
        updated_at: Last modification timestamp
    """

    __tablename__ = "user_persona_configs"

    user_id = Column(UUID(as_uuid=False), primary_key=True)
    persona_id = Column(String(50), primary_key=True)
    custom_prompt = Column(Text, nullable=True)  # NULL = use template
    temperature = Column(Float, nullable=True)  # NULL = use template
    max_tokens = Column(Integer, nullable=True)  # NULL = use template
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<UserPersonaConfig {self.user_id}/{self.persona_id} (active={self.is_active})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "user_id": str(self.user_id),
            "persona_id": self.persona_id,
            "custom_prompt": self.custom_prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
        }
