"""Patient domain entities."""

from backend.models.db_models import Patient

# Gender enum
try:
    from backend.models.db_models import Gender
except ImportError:
    from enum import Enum
    class Gender(str, Enum):
        MALE = "male"
        FEMALE = "female"
        OTHER = "other"

# Repository interface from domain layer (no circular dependency)
from backend.domain.interfaces.ipatient_repository import IPatientRepository

__all__ = [
    "Patient",
    "Gender",
    "IPatientRepository",
]
