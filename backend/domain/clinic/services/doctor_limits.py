"""Doctor Limits Service.

Validates and enforces doctor limits per clinic subscription plan.
Supports superadmin override via ``max_doctors_override`` field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog
from fastapi import HTTPException

from backend.models.checkin_models import Clinic, Doctor

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DoctorLimitInfo:
    """Immutable snapshot of a clinic's doctor-limit state."""

    current_count: int
    max_allowed: int | None
    can_add: bool
    plan_name: str
    plan_display_name: str
    has_override: bool


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def get_doctor_limit(clinic: Clinic) -> int | None:
    """Return the effective doctor limit for *clinic*.

    Resolution order:
        1. ``max_doctors_override`` (superadmin bypass)
        2. ``subscription.max_doctors`` (plan limit)
        3. ``None`` (unlimited — legacy clinics without a plan)
    """
    if clinic.max_doctors_override is not None:
        return clinic.max_doctors_override

    if clinic.subscription and clinic.subscription.max_doctors is not None:
        return clinic.subscription.max_doctors

    return None


def get_current_doctor_count(db: Session, clinic_id: str) -> int:
    """Count active doctors belonging to *clinic_id*."""
    return (
        db.query(Doctor)
        .filter(
            Doctor.clinic_id == clinic_id,
            Doctor.is_active.is_(True),
        )
        .count()
    )


def _resolve_plan_fields(clinic: Clinic) -> tuple[str, str]:
    """Extract ``(plan_name, plan_display_name)`` from *clinic*."""
    if clinic.subscription:
        return clinic.subscription.name, clinic.subscription.display_name
    return "free", "Sin plan"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_can_add_doctor(db: Session, clinic: Clinic) -> None:
    """Raise ``HTTPException 403`` if *clinic* has reached its doctor limit."""
    clinic_id = str(clinic.clinic_id)
    limit = get_doctor_limit(clinic)

    if limit is None:
        logger.debug("doctor_limit_check_passed", clinic_id=clinic_id, result="unlimited")
        return

    current_count = get_current_doctor_count(db, clinic_id)

    if current_count >= limit:
        plan_name, plan_display_name = _resolve_plan_fields(clinic)

        logger.warning(
            "doctor_limit_exceeded",
            clinic_id=clinic_id,
            current_count=current_count,
            max_allowed=limit,
        )

        raise HTTPException(
            status_code=403,
            detail={
                "error": "DOCTOR_LIMIT_EXCEEDED",
                "message": (
                    f"La clínica ha alcanzado el límite de {limit} "
                    f"doctores para {plan_display_name}."
                ),
                "current_count": current_count,
                "max_allowed": limit,
                "plan_name": plan_name,
            },
        )

    logger.debug(
        "doctor_limit_check_passed",
        clinic_id=clinic_id,
        current_count=current_count,
        max_allowed=limit,
    )


# ---------------------------------------------------------------------------
# Info aggregation
# ---------------------------------------------------------------------------


def get_doctor_limit_info(db: Session, clinic: Clinic) -> DoctorLimitInfo:
    """Build a complete doctor-limit snapshot for *clinic*."""
    limit = get_doctor_limit(clinic)
    current_count = get_current_doctor_count(db, str(clinic.clinic_id))
    plan_name, plan_display_name = _resolve_plan_fields(clinic)

    return DoctorLimitInfo(
        current_count=current_count,
        max_allowed=limit,
        can_add=limit is None or current_count < limit,
        plan_name=plan_name,
        plan_display_name=plan_display_name,
        has_override=clinic.max_doctors_override is not None,
    )
