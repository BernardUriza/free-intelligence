"""Patient domain module - pure business logic.

Exports:
- Patient: Domain entity
- Gender: Value object enum
- IPatientRepository: Repository interface
- PatientMapper: DTO↔Entity conversions

Author: Claude Code
Created: 2026-01-28
"""

from backend.domain.patient.entity import Gender, Patient
from backend.domain.patient.mapper import PatientMapper
from backend.domain.patient.repository import IPatientRepository

__all__ = ["Patient", "Gender", "IPatientRepository", "PatientMapper"]
