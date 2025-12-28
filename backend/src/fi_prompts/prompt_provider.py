"""Prompt Provider - Centralized prompt management system.

Provides a standardized way to retrieve, customize, and manage prompts
across the Free Intelligence application.

Features:
- Template-based prompts with placeholders
- Standardized prompt types
- Dynamic parameter injection
- Prompt versioning and history
"""

from __future__ import annotations

import re
from datetime import datetime
from string import Template
from typing import Any

import os
from backend.src.fi_common.logging.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)


class PromptType:
    """Standardized prompt types for consistency."""

    # Medical consultation prompts
    MEDICAL_CONSULTATION = "medical_consultation"
    PATIENT_INTAKE = "patient_intake"
    DIAGNOSIS_ASSISTANCE = "diagnosis_assistance"
    TREATMENT_RECOMMENDATION = "treatment_recommendation"
    MEDICAL_SUMMARY = "medical_summary"

    # Documentation prompts
    SOAP_NOTE = "soap_note"
    CLINICAL_NOTE = "clinical_note"
    PROGRESS_NOTE = "progress_note"

    # Analysis prompts
    DATA_ANALYSIS = "data_analysis"
    TRENDS_IDENTIFICATION = "trends_identification"
    PREDICTIVE_ANALYSIS = "predictive_analysis"

    # Communication prompts
    PATIENT_COMMUNICATION = "patient_communication"
    DOCTOR_COMMUNICATION = "doctor_communication"
    DISCHARGE_INSTRUCTIONS = "discharge_instructions"


class PromptProvider:
    """Central provider for all prompts in the Free Intelligence system.

    This class serves as the single source of truth for all prompts,
    providing template-based prompts that can be customized with
    dynamic parameters based on the context.
    """

    def __init__(self, templates_dir: str | None = None):
        """Initialize the prompt provider."""
        self.templates_dir = Path(
            templates_dir or os.getenv("PROMPT_TEMPLATES_DIR", "backend/src/fi_prompts/templates")
        )
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Load all prompt templates
        self._templates = self._load_all_templates()

        logger.info(
            f"PromptProvider initialized with {len(self._templates)} templates from {self.templates_dir}"
        )

    def _load_all_templates(self) -> dict[str, str]:
        """Load all prompt templates from the templates directory."""
        templates = {}

        for template_file in self.templates_dir.glob("*.txt"):
            try:
                template_name = template_file.stem
                templates[template_name] = template_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")

        # Add some default templates if not already present
        self._add_default_templates(templates)

        return templates

    def _add_default_templates(self, templates: dict[str, str]) -> None:
        """Add default templates if not already present."""
        default_templates = {
            "medical_consultation": """You are an expert medical assistant. Your role is to analyze patient information and provide insights to healthcare professionals.

Current Context:
- Patient demographics: $demographics
- Chief complaint: $chief_complaint
- Current medications: $medications
- Allergies: $allergies

Analysis Required:
1. Identify relevant medical conditions
2. Consider drug interactions
3. Provide differential diagnoses
4. Suggest diagnostic tests
5. Recommend treatment options

IMPORTANT: Provide only medical insights. Do not make final decisions - these are for healthcare professionals to review.""",
            "patient_intake": """You are a patient intake assistant. Collect the following information in a structured format:

1. Demographics
   - Name: $name
   - Age: $age
   - Gender: $gender
   - Contact: $contact

2. Chief Complaint
   - Primary concern: $chief_complaint
   - Duration: $duration

3. History
   - Current medications: $medications
   - Known allergies: $allergies
   - Relevant medical history: $history

4. Additional Details
   - Symptoms: $symptoms
   - Severity: $severity

Please format the response as a structured medical intake form.""",
            "soap_note": """Create a SOAP note based on the following consultation:

SUBJECTIVE:
- Chief complaint: $chief_complaint
- History of present illness: $history
- Review of systems: $ros

OBJECTIVE:
- Vital signs: $vitals
- Physical examination: $examination
- Diagnostic results: $results

ASSESSMENT:
- Primary diagnosis: $primary_diagnosis
- Differential diagnoses: $differential_diagnoses
- Severity: $severity

PLAN:
- Treatments: $treatments
- Medications: $medications
- Follow-up: $follow_up
- Patient education: $education

Format as a professional medical SOAP note.""",
            "discharge_instructions": """Generate patient discharge instructions based on:

Condition: $condition
Treatments received: $treatments
Medications prescribed: $medications
Follow-up requirements: $follow_up

Include:
1. Care instructions
2. Medication schedule
3. Warning signs to monitor
4. When to seek immediate care
5. Follow-up appointments

Format as patient-friendly instructions with clear, simple language.""",
        }

        for name, content in default_templates.items():
            if name not in templates:
                templates[name] = content
                # Save to file as well
                template_file = self.templates_dir / f"{name}.txt"
                template_file.write_text(content, encoding="utf-8")

    def get_prompt(self, prompt_type: str, **kwargs: Any) -> str:
        """Retrieve a prompt of the specified type with filled parameters.

        Args:
            prompt_type: The type of prompt to retrieve
            **kwargs: Parameters to fill into the prompt template

        Returns:
            Formatted prompt string with all placeholders filled

        Raises:
            ValueError: If the prompt type is not found
        """
        if prompt_type not in self._templates:
            available = list(self._templates.keys())
            raise ValueError(f"Unknown prompt type: {prompt_type}. Available: {available}")

        template = self._templates[prompt_type]

        # Fill template with provided parameters
        try:
            # Use safe_substitute to handle missing keys gracefully
            template_obj = Template(template)
            filled_prompt = template_obj.safe_substitute(**kwargs)

            logger.info(f"Retrieved prompt: {prompt_type}", extra={"params": list(kwargs.keys())})
            return filled_prompt
        except Exception as e:
            logger.error(f"Failed to fill prompt template {prompt_type}: {e}")
            raise

    def get_prompt_metadata(self, prompt_type: str) -> dict[str, Any]:
        """Get metadata about a specific prompt type.

        Args:
            prompt_type: The type of prompt to get metadata for

        Returns:
            Dictionary containing prompt metadata
        """
        if prompt_type not in self._templates:
            available = list(self._templates.keys())
            raise ValueError(f"Unknown prompt type: {prompt_type}. Available: {available}")

        template = self._templates[prompt_type]

        # Extract placeholders from the template
        placeholders = re.findall(r"\$(\w+)", template)

        return {
            "type": prompt_type,
            "template_length": len(template),
            "required_parameters": placeholders,
            "created_at": datetime.now().isoformat(),
        }

    def register_new_template(self, prompt_type: str, template: str) -> None:
        """Register a new prompt template.

        Args:
            prompt_type: The type/name of the prompt
            template: The template string with placeholders
        """
        # Validate template has placeholders
        placeholders = re.findall(r"\$(\w+)", template)
        if not placeholders:
            logger.warning(f"Template for {prompt_type} has no placeholders")

        self._templates[prompt_type] = template

        # Save to file
        template_file = self.templates_dir / f"{prompt_type}.txt"
        template_file.write_text(template, encoding="utf-8")

        logger.info(
            f"Registered new prompt template: {prompt_type} with {len(placeholders)} placeholders"
        )

    def list_available_prompts(self) -> list[str]:
        """List all available prompt types.

        Returns:
            List of available prompt type names
        """
        return list(self._templates.keys())


# Global instance for convenience
_prompt_provider = None


def get_prompt_provider() -> PromptProvider:
    """Get the global prompt provider instance."""
    global _prompt_provider
    if _prompt_provider is None:
        _prompt_provider = PromptProvider()
    return _prompt_provider


def get_prompt(prompt_type: str, **kwargs: Any) -> str:
    """Convenience function to get a prompt with filled parameters.

    Args:
        prompt_type: The type of prompt to retrieve
        **kwargs: Parameters to fill into the prompt template

    Returns:
        Formatted prompt string with all placeholders filled
    """
    provider = get_prompt_provider()
    return provider.get_prompt(prompt_type, **kwargs)


def get_available_prompts() -> list[str]:
    """Get a list of all available prompt types.

    Returns:
        List of available prompt type names
    """
    provider = get_prompt_provider()
    return provider.list_available_prompts()
