"""Drug Interaction Checker Service.

Checks medications for drug-drug interactions and generates
clinical alerts based on severity levels.

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-008
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_prescription.data.interactions_catalog import DRUG_INTERACTIONS_CATALOG
from backend.src.fi_prescription.models.interaction import (
    DrugInteraction,
    InteractionAlert,
    InteractionCheckResult,
    InteractionSeverity,
)

if TYPE_CHECKING:
    from backend.src.fi_prescription.models.medication import Medication

logger = get_logger(__name__)


class InteractionChecker:
    """Service to check medications for drug-drug interactions.

    Checks all pairs of medications against the interaction database
    and returns alerts with severity levels and recommendations.

    Uses fuzzy matching to handle variations in medication names
    (generic vs commercial, spelling variations, etc.).

    Example:
        >>> checker = InteractionChecker()
        >>> result = checker.check_medications(["Warfarina", "Ketorolaco"])
        >>> result.has_major_interactions
        True
        >>> result.can_proceed
        False  # Contraindicated combination
    """

    def __init__(self) -> None:
        """Initialize the interaction checker with the catalog."""
        self._interactions = DRUG_INTERACTIONS_CATALOG
        self._build_index()
        logger.info(
            "INTERACTION_CHECKER_INITIALIZED",
            interaction_count=len(self._interactions),
        )

    def _build_index(self) -> None:
        """Build lookup index for faster searches.

        Creates a dictionary mapping drug names (lowercase) to
        their interactions for O(1) lookup.
        """
        self._drug_index: dict[str, list[DrugInteraction]] = {}

        for interaction in self._interactions:
            if not interaction.is_active:
                continue

            # Index by drug_a
            key_a = interaction.drug_a.lower()
            if key_a not in self._drug_index:
                self._drug_index[key_a] = []
            self._drug_index[key_a].append(interaction)

            # Index by drug_b
            key_b = interaction.drug_b.lower()
            if key_b not in self._drug_index:
                self._drug_index[key_b] = []
            self._drug_index[key_b].append(interaction)

    def check_medications(
        self,
        medication_names: list[str],
    ) -> InteractionCheckResult:
        """Check a list of medications for interactions.

        Checks all possible pairs of medications against the
        interaction database and returns alerts.

        Args:
            medication_names: List of medication names to check

        Returns:
            InteractionCheckResult with alerts and summary
        """
        if len(medication_names) < 2:
            return InteractionCheckResult(
                medications_checked=medication_names,
                alerts=[],
                has_major_interactions=False,
                can_proceed=True,
                summary="Se necesitan al menos 2 medicamentos para verificar interacciones.",
            )

        alerts: list[InteractionAlert] = []
        checked_pairs: set[tuple[str, str]] = set()

        # Check all pairs
        for i, med1 in enumerate(medication_names):
            for med2 in medication_names[i + 1 :]:
                # Normalize names
                med1_lower = med1.lower().strip()
                med2_lower = med2.lower().strip()

                # Skip if already checked (order doesn't matter)
                pair_key = tuple(sorted([med1_lower, med2_lower]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                # Find interaction
                interaction = self._find_interaction(med1_lower, med2_lower)
                if interaction:
                    alert = InteractionAlert.from_interaction(
                        interaction=interaction,
                        drug_1_name=med1,
                        drug_2_name=med2,
                    )
                    alerts.append(alert)

                    logger.info(
                        "INTERACTION_FOUND",
                        drug_1=med1,
                        drug_2=med2,
                        severity=interaction.severity.value,
                    )

        # Determine result status
        has_major = any(
            a.interaction.severity
            in (InteractionSeverity.MAJOR, InteractionSeverity.CONTRAINDICATED)
            for a in alerts
        )

        has_contraindicated = any(
            a.interaction.severity == InteractionSeverity.CONTRAINDICATED for a in alerts
        )

        # Sort alerts by severity (most severe first)
        severity_order = {
            InteractionSeverity.CONTRAINDICATED: 0,
            InteractionSeverity.MAJOR: 1,
            InteractionSeverity.MODERATE: 2,
            InteractionSeverity.MINOR: 3,
        }
        alerts.sort(key=lambda a: severity_order[a.interaction.severity])

        # Generate summary
        summary = self._generate_summary(alerts, has_contraindicated)

        result = InteractionCheckResult(
            medications_checked=medication_names,
            alerts=alerts,
            has_major_interactions=has_major,
            can_proceed=not has_contraindicated,
            summary=summary,
        )

        logger.info(
            "INTERACTION_CHECK_COMPLETE",
            medications=medication_names,
            alert_count=len(alerts),
            has_major=has_major,
            can_proceed=result.can_proceed,
        )

        return result

    def check_medication_objects(
        self,
        medications: list["Medication"],
    ) -> InteractionCheckResult:
        """Check Medication objects for interactions.

        Convenience method that extracts names from Medication objects.

        Args:
            medications: List of Medication objects

        Returns:
            InteractionCheckResult with alerts and summary
        """
        # Use both name and active_ingredient if available
        names: list[str] = []
        for med in medications:
            names.append(med.name)
            if med.active_ingredient and med.active_ingredient.lower() != med.name.lower():
                # Also check by active ingredient
                names.append(med.active_ingredient)

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_names: list[str] = []
        for name in names:
            name_lower = name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                unique_names.append(name)

        return self.check_medications(unique_names)

    def _find_interaction(
        self,
        drug1: str,
        drug2: str,
    ) -> DrugInteraction | None:
        """Find interaction between two drugs.

        Uses fuzzy matching to handle name variations.

        Args:
            drug1: First drug name (lowercase)
            drug2: Second drug name (lowercase)

        Returns:
            DrugInteraction if found, None otherwise
        """
        # First, try direct lookup using index
        interactions_for_drug1 = self._drug_index.get(drug1, [])

        for interaction in interactions_for_drug1:
            if interaction.involves_drug(drug2):
                return interaction

        # Also check reverse
        interactions_for_drug2 = self._drug_index.get(drug2, [])

        for interaction in interactions_for_drug2:
            if interaction.involves_drug(drug1):
                return interaction

        # Fuzzy match: check if drug name is contained
        for interaction in self._interactions:
            if not interaction.is_active:
                continue

            # Check if both drugs are involved
            drug1_match = interaction.involves_drug(drug1)
            drug2_match = interaction.involves_drug(drug2)

            if drug1_match and drug2_match:
                return interaction

        return None

    def get_interactions_for_drug(
        self,
        drug_name: str,
    ) -> list[DrugInteraction]:
        """Get all known interactions for a specific drug.

        Useful for displaying warnings when selecting a medication.

        Args:
            drug_name: Drug name to look up

        Returns:
            List of interactions involving this drug
        """
        drug_lower = drug_name.lower().strip()
        interactions: list[DrugInteraction] = []

        for interaction in self._interactions:
            if not interaction.is_active:
                continue

            if interaction.involves_drug(drug_lower):
                interactions.append(interaction)

        # Sort by severity
        severity_order = {
            InteractionSeverity.CONTRAINDICATED: 0,
            InteractionSeverity.MAJOR: 1,
            InteractionSeverity.MODERATE: 2,
            InteractionSeverity.MINOR: 3,
        }
        interactions.sort(key=lambda i: severity_order[i.severity])

        return interactions

    def _generate_summary(
        self,
        alerts: list[InteractionAlert],
        has_contraindicated: bool,
    ) -> str:
        """Generate a human-readable summary of interactions.

        Args:
            alerts: List of interaction alerts
            has_contraindicated: Whether contraindicated interactions exist

        Returns:
            Summary message in Spanish
        """
        if not alerts:
            return "✅ No se detectaron interacciones medicamentosas conocidas."

        contraindicated = sum(
            1 for a in alerts if a.interaction.severity == InteractionSeverity.CONTRAINDICATED
        )
        major = sum(1 for a in alerts if a.interaction.severity == InteractionSeverity.MAJOR)
        moderate = sum(1 for a in alerts if a.interaction.severity == InteractionSeverity.MODERATE)
        minor = sum(1 for a in alerts if a.interaction.severity == InteractionSeverity.MINOR)

        parts: list[str] = []

        if contraindicated:
            parts.append(f"🚫 {contraindicated} CONTRAINDICADA(S)")
        if major:
            parts.append(f"⚠️ {major} mayor(es)")
        if moderate:
            parts.append(f"⚡ {moderate} moderada(s)")
        if minor:
            parts.append(f"ℹ️ {minor} menor(es)")

        summary = f"Interacciones detectadas: {', '.join(parts)}."

        if has_contraindicated:
            summary += "\n⛔ NO PROCEDER - Revisar combinaciones contraindicadas."
        elif major:
            summary += "\n⚠️ PRECAUCIÓN - Evaluar riesgo/beneficio antes de prescribir."

        return summary

    def get_stats(self) -> dict:
        """Get statistics about the interaction database.

        Returns:
            Dict with interaction statistics
        """
        active = [i for i in self._interactions if i.is_active]
        return {
            "total_interactions": len(self._interactions),
            "active_interactions": len(active),
            "contraindicated": sum(
                1 for i in active if i.severity == InteractionSeverity.CONTRAINDICATED
            ),
            "major": sum(1 for i in active if i.severity == InteractionSeverity.MAJOR),
            "moderate": sum(1 for i in active if i.severity == InteractionSeverity.MODERATE),
            "minor": sum(1 for i in active if i.severity == InteractionSeverity.MINOR),
            "indexed_drugs": len(self._drug_index),
        }


# Singleton instance
_checker: InteractionChecker | None = None


def get_interaction_checker() -> InteractionChecker:
    """Get the singleton InteractionChecker instance.

    Returns:
        InteractionChecker instance
    """
    global _checker
    if _checker is None:
        _checker = InteractionChecker()
    return _checker
