"""Doctor Limits Service.

Validates and enforces doctor limits per clinic subscription plan.
Supports superadmin override via max_doctors_override field.

Author: Bernard Uriza Orozco
Created: 2025-12-31
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.models.checkin_models import Clinic, Doctor
from backend.src.fi_common.logging.logger import get_logger
from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)


def get_doctor_limit(clinic: Clinic) -> int | None:
    """Get the effective doctor limit for a clinic.

    Priority:
    1. max_doctors_override (superadmin bypass)
    2. subscription.max_doctors (plan limit)
    3. None (unlimited)

    Args:
        clinic: The clinic to check

    Returns:
        Maximum doctors allowed, or None if unlimited
    """
    # Superadmin override takes priority
    if clinic.max_doctors_override is not None:
        return clinic.max_doctors_override

    # Plan limit
    if clinic.subscription and clinic.subscription.max_doctors is not None:
        return clinic.subscription.max_doctors

    # Default: unlimited (for legacy clinics without plan)
    return None


def get_current_doctor_count(db: Session, clinic_id: str) -> int:
    """Count active doctors in a clinic.

    Args:
        db: Database session
        clinic_id: Clinic UUID

    Returns:
        Number of active doctors
    """
    return (
        db.query(Doctor)
        .filter(
            Doctor.clinic_id == clinic_id,
            Doctor.is_active.is_(True),
        )
        .count()
    )


def validate_can_add_doctor(db: Session, clinic: Clinic) -> None:
    """Validate if a new doctor can be added to the clinic.

    Raises HTTPException 403 if the clinic has reached its doctor limit.

    Args:
        db: Database session
        clinic: The clinic to validate

    Raises:
        HTTPException: 403 if limit exceeded
    """
    limit = get_doctor_limit(clinic)

    # No limit = unlimited
    if limit is None:
        logger.debug(
            "doctor_limit_check",
            clinic_id=str(clinic.clinic_id),
            result="unlimited",
        )
        return

    current_count = get_current_doctor_count(db, str(clinic.clinic_id))

    if current_count >= limit:
        plan_name = clinic.subscription.display_name if clinic.subscription else "Sin plan"

        logger.warning(
            "doctor_limit_exceeded",
            clinic_id=str(clinic.clinic_id),
            current_count=current_count,
            max_allowed=limit,
            plan_name=plan_name,
        )

        raise HTTPException(
            status_code=403,
            detail={
                "error": "DOCTOR_LIMIT_EXCEEDED",
                "message": f"La clínica ha alcanzado el límite de {limit} doctores para {plan_name}.",
                "current_count": current_count,
                "max_allowed": limit,
                "plan_name": clinic.subscription.name if clinic.subscription else "free",
            },
        )

    logger.debug(
        "doctor_limit_check",
        clinic_id=str(clinic.clinic_id),
        current_count=current_count,
        max_allowed=limit,
        result="allowed",
    )


def get_doctor_limit_info(db: Session, clinic: Clinic) -> dict:
    """Get complete doctor limit information for a clinic.

    Args:
        db: Database session
        clinic: The clinic to check

    Returns:
        Dictionary with limit information
    """
    limit = get_doctor_limit(clinic)
    current_count = get_current_doctor_count(db, str(clinic.clinic_id))

    return {
        "current_count": current_count,
        "max_allowed": limit,
        "can_add": limit is None or current_count < limit,
        "plan_name": clinic.subscription.name if clinic.subscription else "free",
        "plan_display_name": clinic.subscription.display_name
        if clinic.subscription
        else "Sin plan",
        "has_override": clinic.max_doctors_override is not None,
    }
