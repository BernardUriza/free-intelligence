"""Allergy Checker Service.

Checks medications against patient allergies and generates
clinical alerts based on severity levels.

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-009
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.utils.common.logging.logger import get_logger
from backend.core.domain.prescription.data.allergen_catalog import ALLERGEN_CATALOG
from backend.core.domain.prescription.models.allergy import (
    AllergenEntry,
    AllergyAlert,
    AllergyCheckResult,
    AllergySeverity,
)

if TYPE_CHECKING:
    from backend.core.domain.prescription.models.medication import Medication

logger = get_logger(__name__)


class AllergyChecker:
    """Service to check medications against patient allergies.

    Checks each medication against the allergen database and
    patient's recorded allergies to generate safety alerts.

    Example:
        >>> checker = AllergyChecker()
        >>> result = checker.check_medications(
        ...     medications=["Amoxicilina", "Paracetamol"],
        ...     patient_allergies=["Penicilina"]
        ... )
        >>> result.has_severe_allergies
        True
        >>> result.can_proceed
        False
    """

    def __init__(self) -> None:
        """Initialize the allergy checker with the catalog."""
        self._allergens = ALLERGEN_CATALOG
        self._build_index()
        logger.info(
            "ALLERGY_CHECKER_INITIALIZED",
            allergen_count=len(self._allergens),
        )

    def _build_index(self) -> None:
        """Build lookup indices for efficient matching.

        Creates:
        - Name index: Maps allergen names to entries
        - Medication index: Maps medication names to allergen entries
        """
        self._name_index: dict[str, AllergenEntry] = {}
        self._medication_index: dict[str, list[AllergenEntry]] = {}

        for allergen in self._allergens:
            if not allergen.is_active:
                continue

            # Index by allergen names
            self._name_index[allergen.name.lower()] = allergen
            self._name_index[allergen.name_es.lower()] = allergen
            self._name_index[allergen.id.lower()] = allergen

            # Index by related medications
            for medication in allergen.related_medications:
                med_lower = medication.lower()
                if med_lower not in self._medication_index:
                    self._medication_index[med_lower] = []
                self._medication_index[med_lower].append(allergen)

    def check_medications(
        self,
        medications: list[str],
        patient_allergies: list[str],
    ) -> AllergyCheckResult:
        """Check medications against patient allergies.

        Args:
            medications: List of medication names to check
            patient_allergies: Patient's recorded allergies

        Returns:
            AllergyCheckResult with alerts and summary
        """
        if not medications:
            return AllergyCheckResult(
                medications_checked=[],
                patient_allergies=patient_allergies,
                alerts=[],
                has_severe_allergies=False,
                can_proceed=True,
                summary="No se verificaron medicamentos.",
            )

        if not patient_allergies:
            return AllergyCheckResult(
                medications_checked=medications,
                patient_allergies=[],
                alerts=[],
                has_severe_allergies=False,
                can_proceed=True,
                summary="✅ Paciente sin alergias registradas.",
            )

        alerts: list[AllergyAlert] = []
        checked_pairs: set[tuple[str, str]] = set()

        # For each patient allergy, find matching allergen entry
        for patient_allergy in patient_allergies:
            allergen = self._find_allergen(patient_allergy)
            if not allergen:
                continue

            # Check each medication against this allergen
            for medication in medications:
                pair_key = (patient_allergy.lower(), medication.lower())
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                if self._medication_matches_allergen(medication, allergen):
                    alert = AllergyAlert.from_allergen(
                        allergen=allergen,
                        medication_name=medication,
                        patient_allergy=patient_allergy,
                    )
                    alerts.append(alert)

                    logger.info(
                        "ALLERGY_MATCH_FOUND",
                        medication=medication,
                        allergen=allergen.name_es,
                        patient_allergy=patient_allergy,
                        severity=allergen.severity.value,
                    )

        # Check cross-reactivity
        for patient_allergy in patient_allergies:
            allergen = self._find_allergen(patient_allergy)
            if not allergen or not allergen.cross_reactive:
                continue

            for cross_reactive_name in allergen.cross_reactive:
                cross_allergen = self._find_allergen(cross_reactive_name)
                if not cross_allergen:
                    continue

                for medication in medications:
                    pair_key = (
                        f"{patient_allergy}+{cross_reactive_name}".lower(),
                        medication.lower(),
                    )
                    if pair_key in checked_pairs:
                        continue
                    checked_pairs.add(pair_key)

                    if self._medication_matches_allergen(medication, cross_allergen):
                        # Reduce severity for cross-reactivity
                        cross_severity = (
                            AllergySeverity.MODERATE
                            if cross_allergen.severity == AllergySeverity.SEVERE
                            else cross_allergen.severity
                        )

                        alert = AllergyAlert(
                            allergen=cross_allergen,
                            medication_name=medication,
                            patient_allergy=f"{patient_allergy} (reactividad cruzada)",
                            severity=cross_severity,
                            alert_message=(
                                f"⚠️ REACTIVIDAD CRUZADA: {medication}\n"
                                f"Paciente alérgico a: {patient_allergy}\n"
                                f"Posible reacción cruzada con: {cross_allergen.name_es}\n"
                                f"{cross_allergen.notes_es or ''}"
                            ),
                            can_override=True,  # Cross-reactivity can usually be overridden
                        )
                        alerts.append(alert)

                        logger.info(
                            "CROSS_REACTIVITY_FOUND",
                            medication=medication,
                            original_allergy=patient_allergy,
                            cross_reactive=cross_allergen.name_es,
                        )

        # Determine result status
        has_severe = any(a.severity == AllergySeverity.SEVERE for a in alerts)

        # Sort by severity (most severe first)
        severity_order = {
            AllergySeverity.SEVERE: 0,
            AllergySeverity.MODERATE: 1,
            AllergySeverity.MILD: 2,
        }
        alerts.sort(key=lambda a: severity_order[a.severity])

        # Generate summary
        summary = self._generate_summary(alerts, has_severe)

        result = AllergyCheckResult(
            medications_checked=medications,
            patient_allergies=patient_allergies,
            alerts=alerts,
            has_severe_allergies=has_severe,
            can_proceed=not has_severe,
            summary=summary,
        )

        logger.info(
            "ALLERGY_CHECK_COMPLETE",
            medication_count=len(medications),
            allergy_count=len(patient_allergies),
            alert_count=len(alerts),
            has_severe=has_severe,
        )

        return result

    def check_medication_objects(
        self,
        medications: list["Medication"],
        patient_allergies: list[str],
    ) -> AllergyCheckResult:
        """Check Medication objects against patient allergies.

        Convenience method that extracts names from Medication objects.

        Args:
            medications: List of Medication objects
            patient_allergies: Patient's recorded allergies

        Returns:
            AllergyCheckResult with alerts and summary
        """
        names = [med.name for med in medications]
        # Also check active ingredients
        for med in medications:
            if med.active_ingredient and med.active_ingredient != med.name:
                names.append(med.active_ingredient)

        return self.check_medications(names, patient_allergies)

    def _find_allergen(self, query: str) -> AllergenEntry | None:
        """Find an allergen entry by name or ID.

        Args:
            query: Allergen name, Spanish name, or ID

        Returns:
            AllergenEntry if found, None otherwise
        """
        query_lower = query.lower().strip()

        # Direct lookup
        if query_lower in self._name_index:
            return self._name_index[query_lower]

        # Fuzzy matching
        for allergen in self._allergens:
            if not allergen.is_active:
                continue

            # Check if query contains allergen name or vice versa
            if (
                allergen.name.lower() in query_lower
                or allergen.name_es.lower() in query_lower
                or query_lower in allergen.name.lower()
                or query_lower in allergen.name_es.lower()
            ):
                return allergen

        return None

    def _medication_matches_allergen(
        self,
        medication: str,
        allergen: AllergenEntry,
    ) -> bool:
        """Check if a medication matches an allergen.

        Args:
            medication: Medication name to check
            allergen: Allergen entry to match against

        Returns:
            True if medication is related to the allergen
        """
        med_lower = medication.lower().strip()

        # Check direct index lookup
        if med_lower in self._medication_index:
            return allergen in self._medication_index[med_lower]

        # Check using allergen's method
        return allergen.matches_medication(medication)

    def get_allergens_for_medication(
        self,
        medication_name: str,
    ) -> list[AllergenEntry]:
        """Get all allergens that a medication is related to.

        Useful for displaying warnings when selecting a medication.

        Args:
            medication_name: Medication name to look up

        Returns:
            List of allergen entries this medication belongs to
        """
        med_lower = medication_name.lower().strip()
        allergens: list[AllergenEntry] = []

        # Check direct index
        if med_lower in self._medication_index:
            allergens.extend(self._medication_index[med_lower])

        # Also check by partial match
        for allergen in self._allergens:
            if not allergen.is_active:
                continue
            if allergen in allergens:
                continue
            if allergen.matches_medication(medication_name):
                allergens.append(allergen)

        return allergens

    def _generate_summary(
        self,
        alerts: list[AllergyAlert],
        has_severe: bool,
    ) -> str:
        """Generate a human-readable summary.

        Args:
            alerts: List of allergy alerts
            has_severe: Whether severe matches exist

        Returns:
            Summary message in Spanish
        """
        if not alerts:
            return "✅ No se detectaron alergias que afecten la prescripción."

        severe = sum(1 for a in alerts if a.severity == AllergySeverity.SEVERE)
        moderate = sum(1 for a in alerts if a.severity == AllergySeverity.MODERATE)
        mild = sum(1 for a in alerts if a.severity == AllergySeverity.MILD)

        parts: list[str] = []

        if severe:
            parts.append(f"🚫 {severe} GRAVE(S)")
        if moderate:
            parts.append(f"⚠️ {moderate} moderada(s)")
        if mild:
            parts.append(f"ℹ️ {mild} leve(s)")

        summary = f"Alertas de alergia: {', '.join(parts)}."

        if has_severe:
            summary += "\n⛔ NO PROCEDER - Revisar alergias graves."

        return summary

    def get_stats(self) -> dict:
        """Get statistics about the allergen database.

        Returns:
            Dict with database statistics
        """
        active = [a for a in self._allergens if a.is_active]
        return {
            "total_allergens": len(self._allergens),
            "active_allergens": len(active),
            "drug_class_allergens": sum(1 for a in active if a.allergen_type.value == "drug_class"),
            "specific_drug_allergens": sum(
                1 for a in active if a.allergen_type.value == "specific_drug"
            ),
            "excipient_allergens": sum(1 for a in active if a.allergen_type.value == "excipient"),
            "food_allergens": sum(1 for a in active if a.allergen_type.value == "food"),
            "indexed_medications": len(self._medication_index),
        }


# Singleton instance
_checker: AllergyChecker | None = None


def get_allergy_checker() -> AllergyChecker:
    """Get the singleton AllergyChecker instance.

    Returns:
        AllergyChecker instance
    """
    global _checker
    if _checker is None:
        _checker = AllergyChecker()
    return _checker
