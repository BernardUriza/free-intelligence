"""Patient Mapper - DB ↔ Domain mapping for Patient entities.

Special case: Patient domain entity IS the SQLAlchemy DB model.
This is an identity mapper - no transformation needed.

However, we maintain the mapper pattern for:
- Consistency with other repositories (SOAPMapper, SessionMapper, etc.)
- Future flexibility if domain/persistence separation is needed
- Clear API contract for repository operations

Pattern:
    Repository calls: PatientMapper.to_db(patient) → DBPatient (new instance)
    Repository calls: PatientMapper.to_db(patient, db_patient) → None (update in-place)
    Repository calls: PatientMapper.from_db(db_patient) → Patient (identity)

Author: Claude Code (P1-5 Repository Mappers)
Created: 2026-02-02
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.db_models import Patient as DBPatient


class PatientMapper:
    """Maps Patient domain entity ↔ DB model.

    Identity mapper - domain Patient IS the SQLAlchemy model.
    Maintains mapper pattern for consistency and future flexibility.
    """

    @staticmethod
    def to_db(patient: DBPatient, db_patient: DBPatient | None = None) -> DBPatient:
        """Convert Patient entity to DB model.

        Args:
            patient: Patient entity (which is also the DB model)
            db_patient: Optional existing DB model to update in-place

        Returns:
            DBPatient model (new instance if db_patient is None, else updates in-place)

        Example:
            >>> # Create new
            >>> db_patient = PatientMapper.to_db(patient)
            >>> db.add(db_patient)
            >>>
            >>> # Update existing
            >>> db_patient = db.query(DBPatient).get(patient_id)
            >>> PatientMapper.to_db(patient, db_patient)  # Updates in-place
            >>> db.flush()
        """
        if db_patient is None:
            # Creating new instance - return the patient itself (identity)
            return patient

        # Updating existing instance - copy fields
        db_patient.nombre = patient.nombre
        db_patient.apellido = patient.apellido
        db_patient.fecha_nacimiento = patient.fecha_nacimiento
        db_patient.genero = patient.genero
        db_patient.curp = patient.curp
        # Note: patient_id, created_at, updated_at are managed by DB

        return db_patient

    @staticmethod
    def from_db(db_patient: DBPatient) -> DBPatient:
        """Convert DB model to Patient entity.

        Args:
            db_patient: SQLAlchemy Patient model

        Returns:
            Patient entity (identity - same as input)

        Example:
            >>> db_patient = db.query(DBPatient).get(patient_id)
            >>> patient = PatientMapper.from_db(db_patient)
            >>> # patient is db_patient (same object)
        """
        # Identity mapping - Patient domain entity IS the DB model
        return db_patient
