"""Alert Transformers for Prescription API.

DRY helpers to transform domain objects to API responses.
Eliminates duplicated alert formatting code across endpoints.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.domain.prescription.services.allergy_checker import (
        AllergyAlert,
        AllergyCheckResult,
    )
    from backend.domain.prescription.services.interaction_checker import (
        InteractionAlert,
        InteractionCheckResult,
    )


def format_interaction_alert(alert: "InteractionAlert") -> dict[str, Any]:
    """Format an interaction alert for API response.

    Args:
        alert: InteractionAlert from interaction_checker

    Returns:
        Dictionary formatted for API response
    """
    return {
        "drug_1": alert.drug_1_name,
        "drug_2": alert.drug_2_name,
        "severity": alert.interaction.severity.value,
        "effect": alert.interaction.effect_es,
        "recommendation": alert.interaction.recommendation_es,
        "can_override": alert.can_override,
        "alert_message": alert.alert_message,
    }


def format_interaction_alert_brief(alert: "InteractionAlert") -> dict[str, Any]:
    """Format an interaction alert for brief API response (no can_override/alert_message).

    Args:
        alert: InteractionAlert from interaction_checker

    Returns:
        Dictionary formatted for brief API response
    """
    return {
        "drug_1": alert.drug_1_name,
        "drug_2": alert.drug_2_name,
        "severity": alert.interaction.severity.value,
        "effect": alert.interaction.effect_es,
        "recommendation": alert.interaction.recommendation_es,
    }


def format_interaction_result(result: "InteractionCheckResult") -> dict[str, Any]:
    """Format full interaction check result for API response.

    Args:
        result: InteractionCheckResult from interaction_checker

    Returns:
        Dictionary formatted for API response
    """
    return {
        "medications_checked": result.medications_checked,
        "alert_count": len(result.alerts),
        "has_major_interactions": result.has_major_interactions,
        "can_proceed": result.can_proceed,
        "summary": result.summary,
        "alerts": [format_interaction_alert(alert) for alert in result.alerts],
    }


def format_allergy_alert(alert: "AllergyAlert") -> dict[str, Any]:
    """Format an allergy alert for API response.

    Args:
        alert: AllergyAlert from allergy_checker

    Returns:
        Dictionary formatted for API response
    """
    return {
        "medication": alert.medication_name,
        "patient_allergy": alert.patient_allergy,
        "severity": alert.severity.value,
        "allergen_type": alert.allergen.allergen_type.value,
        "notes": alert.allergen.notes_es,
        "can_override": alert.can_override,
        "alert_message": alert.alert_message,
    }


def format_allergy_alert_brief(alert: "AllergyAlert") -> dict[str, Any]:
    """Format an allergy alert for brief API response (no can_override/alert_message).

    Args:
        alert: AllergyAlert from allergy_checker

    Returns:
        Dictionary formatted for brief API response
    """
    return {
        "medication": alert.medication_name,
        "patient_allergy": alert.patient_allergy,
        "severity": alert.severity.value,
        "notes": alert.allergen.notes_es,
    }


def format_allergy_result(result: "AllergyCheckResult") -> dict[str, Any]:
    """Format full allergy check result for API response.

    Args:
        result: AllergyCheckResult from allergy_checker

    Returns:
        Dictionary formatted for API response
    """
    return {
        "medications_checked": result.medications_checked,
        "patient_allergies": result.patient_allergies,
        "alert_count": len(result.alerts),
        "has_severe_allergies": result.has_severe_allergies,
        "can_proceed": result.can_proceed,
        "summary": result.summary,
        "alerts": [format_allergy_alert(alert) for alert in result.alerts],
    }
