"""Patient domain entity - pure business logic.

This is a PURE domain entity with ZERO framework dependencies.
No Pydantic, no SQLAlchemy, no FastAPI - just Python dataclasses.

Domain entities represent business concepts and contain:
- Core data fields
- Business validation rules
- Domain behavior (methods)

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 2 - Pure Domain Entities
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class Gender(str, Enum):
    """Patient gender - domain value object."""

    MASCULINO = "MASCULINO"
    FEMENINO = "FEMENINO"
    OTRO = "OTRO"
    NO_ESPECIFICADO = "NO_ESPECIFICADO"


@dataclass
class Patient:
    """Patient domain entity.

    Represents a patient in the healthcare system with Mexican identifiers.

    Business rules:
    - CURP must be 18 characters (if provided)
    - Nombre and apellido are required
    - Age is derived from fecha_nacimiento
    """

    patient_id: str
    nombre: str
    apellido: str
    fecha_nacimiento: datetime
    genero: Gender | None = None
    curp: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate entity after initialization.

        Raises:
            ValueError: If business rules are violated
        """
        if not self.nombre or not self.nombre.strip():
            raise ValueError("Patient nombre cannot be empty")

        if not self.apellido or not self.apellido.strip():
            raise ValueError("Patient apellido cannot be empty")

        if self.curp and not self.is_valid_curp(self.curp):
            raise ValueError(f"Invalid CURP format: {self.curp}")

    # ========================================================================
    # Domain Behavior (Business Logic)
    # ========================================================================

    def get_full_name(self) -> str:
        """Get patient's full name.

        Returns:
            Full name as "Nombre Apellido"
        """
        return f"{self.nombre} {self.apellido}"

    def get_age(self) -> int:
        """Calculate patient's current age in years.

        Returns:
            Age in years
        """
        today = datetime.now(UTC)
        age = today.year - self.fecha_nacimiento.year

        # Adjust if birthday hasn't occurred this year
        if (today.month, today.day) < (
            self.fecha_nacimiento.month,
            self.fecha_nacimiento.day,
        ):
            age -= 1

        return age

    def is_adult(self) -> bool:
        """Check if patient is 18+ years old.

        Returns:
            True if patient is adult (18+)
        """
        return self.get_age() >= 18

    def is_minor(self) -> bool:
        """Check if patient is under 18.

        Returns:
            True if patient is minor (<18)
        """
        return not self.is_adult()

    @staticmethod
    def is_valid_curp(curp: str) -> bool:
        """Validate CURP format (Mexican national ID).

        CURP format: 18 alphanumeric characters
        Example: OAPB891103HDFRZR01

        Args:
            curp: CURP string to validate

        Returns:
            True if CURP format is valid
        """
        if not curp or len(curp) != 18:
            return False

        # CURP regex: 4 letters + 6 digits + 1 letter + 5 alphanumeric + 2 digits
        curp_pattern = r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$"
        return bool(re.match(curp_pattern, curp.upper()))

    def update_demographics(
        self,
        nombre: str | None = None,
        apellido: str | None = None,
        genero: Gender | None = None,
    ) -> None:
        """Update patient demographics.

        Args:
            nombre: New first name
            apellido: New last name
            genero: New gender

        Raises:
            ValueError: If validation fails
        """
        if nombre is not None:
            if not nombre.strip():
                raise ValueError("Nombre cannot be empty")
            self.nombre = nombre

        if apellido is not None:
            if not apellido.strip():
                raise ValueError("Apellido cannot be empty")
            self.apellido = apellido

        if genero is not None:
            self.genero = genero

        self.updated_at = datetime.now(UTC)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Patient(id={self.patient_id}, name={self.get_full_name()}, age={self.get_age()})"
