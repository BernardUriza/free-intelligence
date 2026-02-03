"""Clinic API Helpers.

Utility functions for clinic endpoints.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import TypeVar

T = TypeVar("T")


def generate_checkin_code() -> str:
    """Generate a 6-digit check-in code.

    Returns:
        6-digit string of random digits
    """
    return "".join([str(secrets.randbelow(10)) for _ in range(6)])


def model_to_response(model: object, response_class: type[T]) -> T:
    """Convert SQLAlchemy model to Pydantic response.

    Args:
        model: SQLAlchemy model instance
        response_class: Pydantic model class to convert to

    Returns:
        Pydantic model instance
    """
    data = {}
    for field in response_class.model_fields:  # type: ignore[attr-defined]
        value = getattr(model, field, None)
        if isinstance(value, datetime):
            value = value.isoformat()
        data[field] = value
    return response_class(**data)  # type: ignore[return-value]
