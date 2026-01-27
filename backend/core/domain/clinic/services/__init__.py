"""FI Clinic Services.

Business logic for clinic management.
"""

from backend.core.domain.clinic.services.doctor_limits import (
    get_current_doctor_count,
    get_doctor_limit,
    validate_can_add_doctor,
)

__all__ = [
    "get_doctor_limit",
    "get_current_doctor_count",
    "validate_can_add_doctor",
]
