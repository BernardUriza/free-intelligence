"""FI Clinic Services.

Business logic for clinic management.
"""

from backend.domain.clinic.services.doctor_limits import (
    DoctorLimitInfo,
    get_current_doctor_count,
    get_doctor_limit,
    get_doctor_limit_info,
    validate_can_add_doctor,
)

__all__ = [
    "DoctorLimitInfo",
    "get_current_doctor_count",
    "get_doctor_limit",
    "get_doctor_limit_info",
    "validate_can_add_doctor",
]
