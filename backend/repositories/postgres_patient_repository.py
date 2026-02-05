"""PostgreSQL Patient Repository - IPatientRepository implementation.

Uses SQLAlchemy for database operations.
Translates between domain entities and database models.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 3 - Repository Implementation
"""

from __future__ import annotations

# PEP 585: use built-in list instead of typing.List

from backend.domain.patient import IPatientRepository, Patient
from backend.mappers.patient_mapper import PatientMapper
from backend.models.db_models import Patient as DBPatient
from sqlalchemy.orm import Session


class PostgreSQLPatientRepository(IPatientRepository):
    """PostgreSQL implementation of IPatientRepository.

    Uses SQLAlchemy ORM for database operations.
    """

    def __init__(self, db_session: Session):
        """Initialize repository with database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def save(self, patient: Patient) -> str:
        """Persist patient entity.

        Args:
            patient: Patient entity to save

        Returns:
            patient_id of saved entity

        Raises:
            DuplicatePatientError: If CURP already exists
            RepositoryError: If persistence fails
        """
        # Check for duplicate CURP
        if patient.curp:
            existing = self.db.query(DBPatient).filter_by(curp=patient.curp).first()
            if existing:
                raise ValueError(f"Patient with CURP {patient.curp} already exists")

        # Convert domain entity to DB model
        db_patient = PatientMapper.to_db(patient)

        # Persist
        self.db.add(db_patient)
        self.db.flush()

        return db_patient.patient_id

    def find_by_id(self, patient_id: str) -> Patient | None:
        """Find patient by ID.

        Args:
            patient_id: Patient UUID

        Returns:
            Patient entity if found, None otherwise
        """
        db_patient = self.db.query(DBPatient).filter_by(patient_id=patient_id).first()

        if db_patient is None:
            return None

        return PatientMapper.from_db(db_patient)

    def find_by_curp(self, curp: str) -> Patient | None:
        """Find patient by CURP.

        Args:
            curp: 18-character CURP

        Returns:
            Patient entity if found, None otherwise
        """
        db_patient = self.db.query(DBPatient).filter_by(curp=curp).first()

        if db_patient is None:
            return None

        return PatientMapper.from_db(db_patient)

    def find_all(self, limit: int = 100, offset: int = 0) -> list[Patient]:
        """List all patients with pagination.

        Args:
            limit: Maximum patients to return
            offset: Number of patients to skip

        Returns:
            List of Patient entities
        """
        db_patients = (
            self.db.query(DBPatient)
            .order_by(DBPatient.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        return [PatientMapper.from_db(db_p) for db_p in db_patients]

    def update(self, patient: Patient) -> bool:
        """Update existing patient.

        Args:
            patient: Patient entity with updated data

        Returns:
            True if update successful

        Raises:
            PatientNotFoundError: If patient_id doesn't exist
            RepositoryError: If update fails
        """
        db_patient = self.db.query(DBPatient).filter_by(patient_id=patient.patient_id).first()

        if db_patient is None:
            raise ValueError(f"Patient {patient.patient_id} not found")

        # Update DB model from entity
        PatientMapper.to_db(patient, db_patient)
        self.db.flush()

        return True

    def delete(self, patient_id: str) -> bool:
        """Delete patient by ID.

        Args:
            patient_id: Patient UUID

        Returns:
            True if deletion successful
        """
        db_patient = self.db.query(DBPatient).filter_by(patient_id=patient_id).first()

        if db_patient is None:
            return False

        self.db.delete(db_patient)
        self.db.flush()

        return True

    def exists(self, patient_id: str) -> bool:
        """Check if patient exists.

        Args:
            patient_id: Patient UUID

        Returns:
            True if patient exists
        """
        return (
            self.db.query(DBPatient).filter_by(patient_id=patient_id).count() > 0
        )

    def count(self) -> int:
        """Count total number of patients.

        Returns:
            Total patient count
        """
        return self.db.query(DBPatient).count()
