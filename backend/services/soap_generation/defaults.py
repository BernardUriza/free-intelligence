"""Default SOAP structures for fallback scenarios.

This module provides default empty/fallback SOAP structures
used when LLM extraction fails or returns invalid data.
"""

from __future__ import annotations

from typing import Any

__all__ = ["get_default_soap_structure"]


def get_default_soap_structure() -> dict[str, Any]:
    """Return default empty SOAP structure.

    Used as fallback when LLM extraction fails or returns invalid JSON.
    Ensures graceful degradation with empty but valid structure.

    Returns:
        Dictionary with SOAP structure (English field names - medical standard)
    """
    return {
        "subjective": {
            "chief_complaint": "",
            "history_present_illness": "",
            "past_medical_history": "",
        },
        "objective": {
            "vital_signs": "",
            "physical_exam": "",
        },
        "assessment": {
            "differential_diagnoses": [],
            "primary_diagnosis": "",
        },
        "plan": {
            "treatment": "",
            "follow_up": "",
            "studies": [],
        },
    }
