"""AI-powered Medication Extraction Service.

Uses LLM (Ollama/Claude) to extract structured medication data from
free-text treatment plans in SOAP notes.

Maps extracted medications to the Mexico medication catalog for
enrichment with standard dosing, warnings, and contraindications.

Author: Bernard Uriza Orozco
Created: 2025-12-28
Updated: 2026-02-01 (Phase 2.3 Marte - DI migration for ICatalogService)
Card: FI-RX-003
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.domain.prescription.interfaces.icatalog_service import ICatalogService

from backend.providers.llm import llm_generate
from backend.utils.common.logging.logger import get_logger
from backend.domain.prescription.models.medication import (
    Medication,
    MedicationFrequency,
    MedicationRoute,
)
from backend.utils.prompts.yaml_provider import YAMLPromptProvider

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_medication_prompt() -> str:
    """Load medication extraction prompt from fi_prompts (cached)."""
    provider = YAMLPromptProvider(yaml_dir="backend/src/fi_prompts/yaml_presets")
    prompt = provider.get_yaml_system_prompt("medication_extractor")
    if not prompt:
        raise ValueError("medication_extractor prompt not found")
    return prompt


# Map Spanish frequency text to enum values
FREQUENCY_MAP: dict[str, MedicationFrequency] = {
    "cada 4 horas": "every_4_hours",
    "cada 6 horas": "every_6_hours",
    "cada 8 horas": "every_8_hours",
    "cada 12 horas": "every_12_hours",
    "cada 24 horas": "every_24_hours",
    "una vez al día": "once_daily",
    "dos veces al día": "twice_daily",
    "tres veces al día": "three_times_daily",
    "cuatro veces al día": "four_times_daily",
    "antes de comer": "before_meals",
    "después de comer": "after_meals",
    "al acostarse": "at_bedtime",
    "según sea necesario": "as_needed",
    "por razón necesaria": "as_needed",
    "prn": "as_needed",
    "semanalmente": "weekly",
    "una vez por semana": "weekly",
}

# Map Spanish route text to enum values
ROUTE_MAP: dict[str, MedicationRoute] = {
    "oral": "oral",
    "vo": "oral",
    "vía oral": "oral",
    "sublingual": "sublingual",
    "sl": "sublingual",
    "intramuscular": "intramuscular",
    "im": "intramuscular",
    "intravenosa": "intravenous",
    "iv": "intravenous",
    "subcutánea": "subcutaneous",
    "sc": "subcutaneous",
    "tópica": "topical",
    "oftálmica": "ophthalmic",
    "ótica": "otic",
    "nasal": "nasal",
    "inhalada": "inhalation",
    "rectal": "rectal",
    "vaginal": "vaginal",
    "transdérmica": "transdermal",
}


class MedicationExtractionError(Exception):
    """Error during medication extraction."""

    pass


class MedicationExtractor:
    """AI-powered medication extractor.

    Uses LLM to parse free-text treatment plans and extract
    structured medication data, then enriches with catalog info.

    Phase 2.3 Critical Fix: Uses constructor injection for ICatalogService.
    """

    def __init__(
        self,
        catalog_service: "ICatalogService",
        provider: str = "ollama",
    ):
        """Initialize extractor with REQUIRED catalog service.

        Args:
            catalog_service: ICatalogService instance (REQUIRED)
            provider: LLM provider ("ollama", "claude", "openai")

        Raises:
            ValueError: If catalog_service is None (DI misconfiguration)

        Note:
            Phase 2.3 Critical Fix: catalog_service is REQUIRED.
            Use get_medication_extractor() factory for proper DI.
        """
        if catalog_service is None:
            raise ValueError(
                "MedicationExtractor requires an ICatalogService. "
                "Use get_medication_extractor() with get_catalog_service_dep()"
            )
        self._catalog_service = catalog_service
        self.provider = provider
        logger.info("MedicationExtractor initialized", provider=provider)

    def extract_medications(
        self,
        treatment_text: str,
        enrich_from_catalog: bool = True,
    ) -> list[Medication]:
        """Extract medications from treatment text using AI.

        Args:
            treatment_text: Free-text treatment plan (e.g., from SOAP plan)
            enrich_from_catalog: Whether to add info from medication catalog

        Returns:
            List of structured Medication objects

        Raises:
            MedicationExtractionError: If extraction fails
        """
        if not treatment_text or not treatment_text.strip():
            return []

        try:
            # Load prompt from fi_prompts and add treatment text
            system_prompt = _load_medication_prompt()
            prompt = f"{system_prompt}\n\nTexto de tratamiento a analizar:\n{treatment_text.strip()}\n\nResponde SOLO con el JSON array:"

            logger.info(
                "MEDICATION_EXTRACTION_START",
                provider=self.provider,
                text_length=len(treatment_text),
            )

            # Call LLM
            response = llm_generate(
                prompt,
                provider=self.provider,
                max_tokens=2000,
                temperature=0.1,  # Low temperature for structured output
            )

            response_text = response.content.strip()

            logger.debug(
                "LLM_RESPONSE_RECEIVED",
                response_preview=response_text[:300],
            )

            # Parse JSON response
            medications_data = self._parse_llm_response(response_text)

            # Convert to Medication objects
            medications = []
            for med_data in medications_data:
                medication = self._create_medication(med_data)

                # Enrich from catalog if enabled
                if enrich_from_catalog:
                    medication = self._enrich_from_catalog(medication)

                medications.append(medication)

            logger.info(
                "MEDICATION_EXTRACTION_SUCCESS",
                count=len(medications),
                medications=[m.name for m in medications],
            )

            return medications

        except MedicationExtractionError:
            raise
        except Exception as e:
            logger.error(
                "MEDICATION_EXTRACTION_FAILED",
                error=str(e),
                exc_info=True,
            )
            # Fallback to simple parsing
            return self._fallback_parse(treatment_text)

    def _parse_llm_response(self, response_text: str) -> list[dict[str, Any]]:
        """Parse LLM response to extract JSON array.

        Args:
            response_text: Raw LLM response

        Returns:
            List of medication dictionaries

        Raises:
            MedicationExtractionError: If JSON parsing fails
        """
        # Try to find JSON array in response
        # Handle cases where LLM adds extra text
        json_match = re.search(r"\[[\s\S]*\]", response_text)

        if not json_match:
            # Maybe it's a single object
            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                try:
                    single_med = json.loads(json_match.group())
                    return [single_med]
                except json.JSONDecodeError:
                    pass

            logger.warning(
                "NO_JSON_FOUND",
                response_preview=response_text[:200],
            )
            return []

        try:
            medications = json.loads(json_match.group())
            if isinstance(medications, dict):
                medications = [medications]
            return medications
        except json.JSONDecodeError as e:
            logger.warning(
                "JSON_PARSE_ERROR",
                error=str(e),
                response_preview=response_text[:200],
            )
            return []

    def _create_medication(self, data: dict[str, Any]) -> Medication:
        """Create Medication object from parsed data.

        Args:
            data: Dictionary with medication info

        Returns:
            Medication object
        """
        # Parse frequency
        frequency_text = (data.get("frequency") or "").lower().strip()
        frequency = self._parse_frequency(frequency_text)

        # Parse route
        route_text = (data.get("route") or "oral").lower().strip()
        route = self._parse_route(route_text)

        # Parse duration
        duration_days = data.get("duration_days")
        if duration_days is not None:
            try:
                duration_days = int(duration_days)
            except (ValueError, TypeError):
                duration_days = None

        return Medication(
            name=data.get("name", "").strip(),
            dosage=data.get("dosage", "según indicación").strip(),
            dosage_form=data.get("form", "tableta"),
            frequency=frequency,
            frequency_custom=frequency_text if frequency == "custom" else None,
            duration_days=duration_days,
            route=route,
            instructions=data.get("instructions"),
        )

    def _parse_frequency(self, text: str) -> MedicationFrequency:
        """Parse frequency text to enum value.

        Args:
            text: Spanish frequency text

        Returns:
            MedicationFrequency enum value
        """
        text = text.lower().strip()

        # Direct match
        if text in FREQUENCY_MAP:
            return FREQUENCY_MAP[text]

        # Partial match
        for spanish, enum_val in FREQUENCY_MAP.items():
            if spanish in text or text in spanish:
                return enum_val

        # Pattern matching for "cada X horas"
        hours_match = re.search(r"cada\s*(\d+)\s*h", text)
        if hours_match:
            hours = int(hours_match.group(1))
            hours_map = {
                4: "every_4_hours",
                6: "every_6_hours",
                8: "every_8_hours",
                12: "every_12_hours",
                24: "every_24_hours",
            }
            return hours_map.get(hours, "custom")

        # Default to custom if unrecognized
        return "custom" if text else "every_8_hours"

    def _parse_route(self, text: str) -> MedicationRoute:
        """Parse route text to enum value.

        Args:
            text: Spanish route text

        Returns:
            MedicationRoute enum value
        """
        text = text.lower().strip()

        # Direct match
        if text in ROUTE_MAP:
            return ROUTE_MAP[text]

        # Partial match
        for spanish, enum_val in ROUTE_MAP.items():
            if spanish in text:
                return enum_val

        # Default to oral
        return "oral"

    def _enrich_from_catalog(self, medication: Medication) -> Medication:
        """Enrich medication with data from catalog.

        Searches catalog by medication name and adds:
        - Generic name (if commercial name was used)
        - Active ingredient
        - Standard warnings
        - Dosing info validation

        Args:
            medication: Medication to enrich

        Returns:
            Enriched Medication (or original if not found)
        """
        # Search catalog for this medication (using injected service)
        search_results = self._catalog_service.autocomplete(
            prefix=medication.name[:3].lower()
            if len(medication.name) >= 3
            else medication.name.lower(),
            limit=5,
        )

        # Try to find exact or close match
        catalog_entry = None
        med_name_lower = medication.name.lower()

        for suggestion in search_results:
            entry = self._catalog_service.get_by_id(
                suggestion.lower().replace(" ", "_").replace("/", "_")
            )
            if entry:
                if entry.generic_name.lower() == med_name_lower or med_name_lower in [
                    n.lower() for n in entry.commercial_names
                ]:
                    catalog_entry = entry
                    break

        # Also try direct search
        if not catalog_entry:
            from backend.domain.prescription.services.catalog_service import CatalogSearchRequest

            search_req = CatalogSearchRequest(query=medication.name, limit=1)
            search_resp = self._catalog_service.search(search_req)
            if search_resp.results and search_resp.results[0].score >= 50:
                catalog_entry = search_resp.results[0].medication

        if not catalog_entry:
            logger.debug(
                "CATALOG_MATCH_NOT_FOUND",
                medication_name=medication.name,
            )
            return medication

        logger.debug(
            "CATALOG_MATCH_FOUND",
            medication_name=medication.name,
            catalog_id=catalog_entry.id,
            catalog_name=catalog_entry.generic_name,
        )

        # Enrich medication with catalog data
        # Use generic name if a commercial name was provided
        if medication.name.lower() != catalog_entry.generic_name.lower():
            medication.active_ingredient = catalog_entry.generic_name

        # Add warnings from catalog
        if catalog_entry.warnings and not medication.warnings:
            medication.warnings = "; ".join(catalog_entry.warnings[:2])

        # Validate dosage against max daily dose
        if catalog_entry.standard_dosing and catalog_entry.standard_dosing.max_daily_dose:
            # Add note about max dose if not already mentioned
            if medication.instructions:
                if "máxim" not in medication.instructions.lower():
                    medication.instructions += (
                        f" (Dosis máx: {catalog_entry.standard_dosing.max_daily_dose})"
                    )
            else:
                medication.instructions = (
                    f"Dosis máxima: {catalog_entry.standard_dosing.max_daily_dose}"
                )

        return medication

    def _fallback_parse(self, text: str) -> list[Medication]:
        """Simple fallback parser when LLM fails.

        Uses basic text patterns to extract medications.

        Args:
            text: Treatment text

        Returns:
            List of Medications (may be incomplete)
        """
        logger.info("FALLBACK_PARSE_ACTIVATED")

        medications: list[Medication] = []
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove common prefixes
            for prefix in ["- ", "• ", "* ", "Rx: ", "Rx ", "1. ", "2. ", "3. "]:
                if line.startswith(prefix):
                    line = line[len(prefix) :]
                    break

            # Skip non-medication lines
            skip_keywords = [
                "seguimiento",
                "cita",
                "indicaciones generales",
                "reposo",
                "dieta",
                "laboratorios",
            ]
            if any(kw in line.lower() for kw in skip_keywords):
                continue

            # Try to extract medication name (first capitalized word or phrase)
            parts = line.split()
            if not parts:
                continue

            med_name = parts[0]

            # Look for dosage (number + unit)
            dosage = "según indicación"
            dosage_pattern = re.search(r"\d+\s*(?:mg|g|ml|mcg|ui)", line, re.IGNORECASE)
            if dosage_pattern:
                dosage = dosage_pattern.group()

            medication = Medication(
                name=med_name,
                dosage=dosage,
                instructions=line,
            )

            # Try to enrich from catalog
            medication = self._enrich_from_catalog(medication)
            medications.append(medication)

        return medications


def get_medication_extractor(
    catalog_service: "ICatalogService | None" = None,
    provider: str = "ollama",
) -> MedicationExtractor:
    """Create MedicationExtractor instance with proper DI.

    Args:
        catalog_service: ICatalogService instance. If None, creates default.
        provider: LLM provider to use

    Returns:
        MedicationExtractor instance

    Note:
        Phase 2.3 Critical Fix: No more module-level singleton.
        Each call creates a new instance for proper DI compliance.
        For best practice, pass catalog_service from get_catalog_service_dep().
    """
    if catalog_service is None:
        # Backwards compatibility: create default catalog service
        from backend.services.workflow.dependencies import get_catalog_service_dep

        catalog_service = get_catalog_service_dep()

    return MedicationExtractor(
        catalog_service=catalog_service,
        provider=provider,
    )
