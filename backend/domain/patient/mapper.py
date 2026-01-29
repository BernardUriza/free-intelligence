"""Patient mapper - DTO to Entity conversions.

Translates between:
- HTTP DTOs (Pydantic models for API)
- Domain entities (pure Python dataclasses)
- Database models (SQLAlchemy ORM)

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 3 - DTO↔Entity Mapping
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from backend.domain.patient.entity import Gender, Patient

if TYPE_CHECKING:
    from backend.models.db_models import Patient as DBPatient
    from backend.api.routers.patient.public.patients import (
        PatientCreate,
        PatientResponse,
        PatientUpdate,
    )


class PatientMapper:
    """Maps between Patient representations.

    Conversions:
    - to_entity: DTO/DB → Domain
    - to_dto: Domain → API response
    - to_db: Domain → SQLAlchemy model
    """

    @staticmethod
    def from_create_dto(dto: PatientCreate, patient_id: str) -> Patient:
        """Convert PatientCreate DTO to domain entity.

        Args:
            dto: API create request
            patient_id: Generated UUID

        Returns:
            Patient domain entity
        """
        return Patient(
            patient_id=patient_id,
            nombre=dto.nombre,
            apellido=dto.apellido,
            fecha_nacimiento=dto.fecha_nacimiento,
            genero=Gender(dto.genero.value) if dto.genero else None,
            curp=dto.curp,
        )

    @staticmethod
    def from_db(db_patient: DBPatient) -> Patient:
        """Convert SQLAlchemy model to domain entity.

        Args:
            db_patient: Database model instance

        Returns:
            Patient domain entity
        """
        return Patient(
            patient_id=db_patient.patient_id,
            nombre=db_patient.nombre,
            apellido=db_patient.apellido,
            fecha_nacimiento=db_patient.fecha_nacimiento,
            genero=Gender(db_patient.genero.value) if db_patient.genero else None,
            curp=db_patient.curp,
            created_at=db_patient.created_at,
            updated_at=db_patient.updated_at,
        )

    @staticmethod
    def to_response_dto(entity: Patient) -> PatientResponse:
        """Convert domain entity to API response DTO.

        Args:
            entity: Patient domain entity

        Returns:
            PatientResponse Pydantic model
        """
        from backend.api.routers.patient.public.patients import PatientResponse

        return PatientResponse(
            patient_id=entity.patient_id,
            nombre=entity.nombre,
            apellido=entity.apellido,
            fecha_nacimiento=entity.fecha_nacimiento.isoformat(),
            genero=entity.genero.value if entity.genero else None,
            curp=entity.curp,
            created_at=entity.created_at.isoformat(),
            updated_at=entity.updated_at.isoformat(),
        )

    @staticmethod
    def to_db(entity: Patient, db_patient: DBPatient | None = None) -> DBPatient:
        """Convert domain entity to SQLAlchemy model.

        Args:
            entity: Patient domain entity
            db_patient: Existing DB model to update (or None for new)

        Returns:
            SQLAlchemy Patient model
        """
        from backend.models.db_models import Patient as DBPatient, GenderEnum

        if db_patient is None:
            db_patient = DBPatient(patient_id=entity.patient_id)

        db_patient.nombre = entity.nombre
        db_patient.apellido = entity.apellido
        db_patient.fecha_nacimiento = entity.fecha_nacimiento
        db_patient.genero = GenderEnum(entity.genero.value) if entity.genero else None
        db_patient.curp = entity.curp
        db_patient.updated_at = entity.updated_at

        return db_patient

    @staticmethod
    def apply_update(entity: Patient, dto: PatientUpdate) -> Patient:
        """Apply PatientUpdate DTO to existing entity.

        Args:
            entity: Existing Patient entity
            dto: Update request DTO

        Returns:
            Updated Patient entity (new instance)
        """
        # Update mutable fields
        if dto.nombre is not None:
            entity.update_demographics(nombre=dto.nombre)
        if dto.apellido is not None:
            entity.update_demographics(apellido=dto.apellido)
        if dto.genero is not None:
            entity.update_demographics(genero=Gender(dto.genero.value))
        if dto.fecha_nacimiento is not None:
            entity.fecha_nacimiento = dto.fecha_nacimiento

        return entity
