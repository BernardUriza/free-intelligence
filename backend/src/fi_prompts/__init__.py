"""FI Prompts - Centralized Prompt Library.

This package provides a standardized way to manage and retrieve
prompts across the Free Intelligence application.

Features:
- Template-based prompts with parameter injection
- Standardized prompt types
- YAML preset integration
- CLI access to prompts
- Extensible architecture for new prompt types

Usage:
    from backend.src.fi_prompts import get_prompt

    # Get a medical consultation prompt with parameters
    prompt = get_prompt(
        "medical_consultation",
        demographics="65-year-old male",
        chief_complaint="Chest pain for 2 hours",
        medications="Aspirin, Metformin, Lisinopril",
        allergies="Penicillin (rash)",
    )
"""

from backend.src.fi_prompts.prompt_provider import (
    PromptProvider,
    PromptType,
    get_available_prompts,
    get_prompt,
    get_prompt_provider,
)
from backend.src.fi_prompts.yaml_provider import (
    YAMLPromptProvider,
    get_enhanced_prompt,
)

__all__ = [
    "PromptProvider",
    "PromptType",
    "YAMLPromptProvider",
    "get_available_prompts",
    "get_enhanced_prompt",
    "get_prompt",
    "get_prompt_provider",
]
