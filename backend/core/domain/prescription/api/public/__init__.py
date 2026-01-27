# fi_prescription.api.public
"""Public API endpoints for prescription management."""

from backend.core.domain.prescription.api.public.prescriptions import router

__all__ = ["router"]
